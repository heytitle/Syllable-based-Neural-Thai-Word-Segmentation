#!/usr/bin/env python

import glob
import os
import shutil
import sys
import time

sys.path.insert(0, os.getcwd())

import numpy as np

import fire
import torch
import torch.optim as optim
from torch.utils import data

from attacut import dataloaders as dl, output_tags
from attacut import evaluation, models, utils, loss

def _create_metrics(metrics=["true_pos", "false_pos", "false_neg"]):
    return dict(zip(metrics, [0]*len(metrics)))


def copy_files(path, dest):
    utils.maybe_create_dir(dest)

    for f in glob.glob(path):
        filename = f.split("/")[-1]
        shutil.copy(f, "%s/%s" % (dest, filename), follow_symlinks=True)


def do_iterate(model, generator, device,
    optimizer=None, criterion=None, prefix="", step=0):

    total_loss, total_preds = 0, 0

    for _, batch in enumerate(generator):
        (x, seq), labels, perm_ix = batch

        xd, yd, total_batch_preds = generator.dataset.prepare_model_inputs(
            ((x, seq), labels), device
        )

        if optimizer:
            model.zero_grad()

        logits = model(xd)

        loss = criterion(model, logits, yd, seq.to(device))

        if optimizer:
            loss.backward()
            optimizer.step()

        total_preds += total_batch_preds
        total_loss += loss.item() * total_batch_preds

    avg_loss = total_loss / total_preds if total_preds > 0 else 0
    print(f"[{prefix}] loss {avg_loss:.4f}")

    return avg_loss


# taken from https://stackoverflow.com/questions/52660985/pytorch-how-to-get-learning-rate-during-training
def get_lr(optimizer):
    for param_group in optimizer.param_groups:
        return param_group['lr']


def main(
        model_name, data_dir, 
        epoch=10,
        lr=0.001,
        batch_size=64,
        weight_decay=0.0,
        checkpoint=0,
        model_params="",
        output_dir="",
        no_workers=4,
        prev_model="",
    ):

    model_cls = models.get_model(model_name)

    output_scheme = output_tags.get_scheme(
        utils.parse_model_params(model_params)["oc"]
    )

    dataset_cls = model_cls.dataset

    training_set: dl.SequenceDataset = dataset_cls.load_preprocessed_file_with_suffix(
        data_dir,
        "training.txt",
        output_scheme
    )

    validation_set: dl.SequenceDataset = dataset_cls.load_preprocessed_file_with_suffix(
        data_dir,
        "val.txt",
        output_scheme
    )

    # only required
    data_config = training_set.setup_featurizer()

    device = models.get_device()
    print("Using device: %s" % device)

    params = {}

    if model_params:
        params['model_config'] = model_params
        print(">> model configuration: %s" % model_params)

    if prev_model:
        print("Initiate model from %s" % prev_model)
        model = models.get_model(model_name).load(
            prev_model,
            data_config,
            **params
        )
    else:
        model = models.get_model(model_name)(
            data_config,
            **params
        )

    model = model.to(device)

    if hasattr(model, "crf"):
        criterion = loss.crf
    else:
        criterion = loss.cross_ent

    optimizer = optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)

    if prev_model:
        print("Loading prev optmizer's state")
        optimizer.load_state_dict(torch.load("%s/optimizer.pth" % prev_model))
        print("Previous learning rate", get_lr(optimizer))

        # force torch to use the given lr, not previous one
        for param_group in optimizer.param_groups:
            param_group['lr'] = lr
            param_group['initial_lr'] = lr

        print("Current learning rate", get_lr(optimizer))

    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        "min",
        patience=0,
        verbose=True
    )

    dataloader_params = dict(
        batch_size=batch_size,
        num_workers=no_workers,
        collate_fn=dataset_cls.collate_fn
    )

    print("Using dataset: %s" % type(dataset_cls).__name__)

    training_generator = data.DataLoader(
        training_set,
        shuffle=True,
        **dataloader_params
    )
    validation_generator = data.DataLoader(
        validation_set,
        shuffle=False,
        **dataloader_params
    )

    total_train_size = len(training_set) 
    total_test_size = len(validation_set)

    print("We have %d train samples and %d test samples" %
        (total_train_size, total_test_size)
    )

    # for FloydHub
    print(
        '{"metric": "%s:%s", "value": %s}' %
        ("model", model_name, model.total_trainable_params())
    )

    os.makedirs(output_dir, exist_ok=True)

    copy_files(
        "%s/dictionary/*.json" % data_dir,
        output_dir
    )

    start_training_time = time.time()
    best_val_loss = np.inf
    for e in range(1, epoch+1):
        print("===EPOCH %d ===" % (e))
        st_time = time.time()

        curr_lr = get_lr(optimizer)
        print(f"lr={curr_lr}")

        with utils.Timer("epoch-training") as timer:
            model.train()
            _ = do_iterate(model, training_generator,
                prefix="training",
                step=e,
                device=device,
                optimizer=optimizer,
                criterion=criterion,
            )

        with utils.Timer("epoch-validation") as timer, \
            torch.no_grad():
            model.eval()
            val_loss = do_iterate(model, validation_generator,
                prefix="validation",
                step=e,
                device=device,
                criterion=criterion,
            )

        elapsed_time = (time.time() - st_time) / 60.
        print(f"Time took: {elapsed_time:.4f} mins")

        scheduler.step(val_loss)

        if val_loss < best_val_loss:
            model_path = "%s/model.pth" % output_dir
            opt_path = "%s/optimizer.pth" % output_dir

            print("Saving model to %s" % model_path)
            torch.save(model.state_dict(), model_path)
            torch.save(optimizer.state_dict(), opt_path)

            best_val_loss = val_loss

    training_took = time.time() - start_training_time

    print(f"[training] total time: {training_took}")


    config = utils.parse_model_params(model_params)

    if "embs" in config and type(config["embs"]) == str:
        emb = config["embs"]
        copy_files(
            f"{data_dir}/dictionary/sy-emb-{emb}.npy",
            output_dir
        )

    utils.save_training_params(
        output_dir,
        utils.ModelParams(
            name=model_name,
            params=model.model_params,
            training_took=training_took,
            num_trainable_params=model.total_trainable_params(),
            lr=lr,
            weight_decay=weight_decay,
            epoch=epoch
        )
    )

if __name__ == "__main__":
    fire.Fire(main)
