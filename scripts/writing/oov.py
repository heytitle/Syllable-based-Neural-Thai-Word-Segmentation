import sys
import re
import numpy as np
from pythainlp import util

from attacut import benchmark

TRAINING_SET = "./data/best-raw/training.txt"

TEST_SET = {
    "best-test": "./data/best-test/label.txt",
    "wisesight-1000": "../docker-thai-tokenizers/data/wisesight-1000/label.txt",
    "tnhc": "../docker-thai-tokenizers/data/tnhc/tnhc.label",
}

FILES = {
    "best-test": {
        "PyThaiNLP": "../docker-thai-tokenizers/data/best-test/input_tokenised-pythainlp-newmm.txt",
        "DeepCut": "../docker-thai-tokenizers/data/best-test/input_tokenised-deepcut-deepcut.txt",
        "BiLSTM-CRF(SY)-BI": "./best-models/seq_sy_lstm_bi_crf.yaml-2020-06-03--18-10.20-run-9/best-test.txt",
        "ID-CNN-CRF(SY)-SchemeA": "./best-models/seq_sy_conv_3lv_crf_scheme_a.yaml-2020-06-01--11-39.20-run-1/best-test.txt",
        "BiLSTM(CH)-BI": "./best-models/seq_ch_lstm_bi.yaml-2020-06-04--09-17.20-run-13/best-test.txt",
        "ID-CHH(CH)-BI": "./best-models/seq_ch_conv_3lv.yaml-2020-06-03--12-11.20-run-8/best-test.txt",
        "BiLSTM(CH+SY)-BI": "./best-models/seq_sy_ch_lstm_bi.yaml-2020-06-03--20-26.20-run-12/best-test.txt",
        "ID-CNN(CH+SY)-BI": "./best-models/seq_sy_ch_conv_3lv.yaml-2020-06-02--23-23.20-run-18/best-test.txt",
    },
    "wisesight-1000": {
        "PyThaiNLP": "../docker-thai-tokenizers/data/wisesight-1000/input_tokenised-pythainlp-newmm.txt",
        "DeepCut": "../docker-thai-tokenizers/data/wisesight-1000/input_tokenised-deepcut-deepcut.txt",
        "BiLSTM-CRF(SY)-BI": "../docker-thai-tokenizers/data/wisesight-1000/input-tokenized-by-seq_sy_lstm_bi_crf.yaml-2020-06-03--18-10.20-run-9.txt",
        "ID-CNN-CRF(SY)-SchemeA": "../docker-thai-tokenizers/data/wisesight-1000/input-tokenized-by-seq_sy_conv_3lv_crf_scheme_a.yaml-2020-06-01--11-39.20-run-1.txt",
        "BiLSTM(CH)-BI": "../docker-thai-tokenizers/data/wisesight-1000/input-tokenized-by-seq_ch_lstm_bi.yaml-2020-06-04--09-17.20-run-13.txt",
        "ID-CHH(CH)-BI": "../docker-thai-tokenizers/data/wisesight-1000/input-tokenized-by-seq_ch_conv_3lv.yaml-2020-06-03--12-11.20-run-8.txt",
        "BiLSTM(CH+SY)-BI": "../docker-thai-tokenizers/data/wisesight-1000/input-tokenized-by-seq_sy_ch_lstm_bi.yaml-2020-06-03--20-26.20-run-12.txt",
        "ID-CNN(CH+SY)-BI": "../docker-thai-tokenizers/data/wisesight-1000/input-tokenized-by-seq_sy_ch_conv_3lv.yaml-2020-06-02--23-23.20-run-18.txt",
    },
    "tnhc": {
        "PyThaiNLP": "../docker-thai-tokenizers/data/tnhc/input_tokenised-pythainlp-newmm.txt",
        "DeepCut": "../docker-thai-tokenizers/data/tnhc/input_tokenised-deepcut-deepcut.txt",
        "BiLSTM-CRF(SY)-BI": "../docker-thai-tokenizers/data/tnhc/input-tokenized-by-seq_sy_lstm_bi_crf.yaml-2020-06-03--18-10.20-run-9.txt",
        "ID-CNN-CRF(SY)-SchemeA": "../docker-thai-tokenizers/data/tnhc/input-tokenized-by-seq_sy_conv_3lv_crf_scheme_a.yaml-2020-06-01--11-39.20-run-1.txt",
        "BiLSTM(CH)-BI": "../docker-thai-tokenizers/data/tnhc/input-tokenized-by-seq_ch_lstm_bi.yaml-2020-06-04--09-17.20-run-13.txt",
        "ID-CHH(CH)-BI": "../docker-thai-tokenizers/data/tnhc/input-tokenized-by-seq_ch_conv_3lv.yaml-2020-06-03--12-11.20-run-8.txt",
        "BiLSTM(CH+SY)-BI": "../docker-thai-tokenizers/data/tnhc/input-tokenized-by-seq_sy_ch_lstm_bi.yaml-2020-06-03--20-26.20-run-12.txt",
        "ID-CNN(CH+SY)-BI": "../docker-thai-tokenizers/data/tnhc/input-tokenized-by-seq_sy_ch_conv_3lv.yaml-2020-06-02--23-23.20-run-18.txt",
    }
}

KEYS = {
    "best-test": [
        "PyThaiNLP",
        "DeepCut",
        "BiLSTM(CH)-BI",
        "BiLSTM(CH+SY)-BI",
        "BiLSTM-CRF(SY)-BI",
        "ID-CHH(CH)-BI",
        "ID-CNN(CH+SY)-BI",
        "ID-CNN-CRF(SY)-SchemeA",
    ],
    "wisesight-1000": [
        "PyThaiNLP",
        "DeepCut",
        "BiLSTM(CH)-BI",
        "BiLSTM(CH+SY)-BI",
        "BiLSTM-CRF(SY)-BI",
        "ID-CHH(CH)-BI",
        "ID-CNN(CH+SY)-BI",
        "ID-CNN-CRF(SY)-SchemeA",
    ],
    "tnhc": [
        "PyThaiNLP",
        "DeepCut",
        "BiLSTM(CH)-BI",
        "BiLSTM(CH+SY)-BI",
        "BiLSTM-CRF(SY)-BI",
        "ID-CHH(CH)-BI",
        "ID-CNN(CH+SY)-BI",
        "ID-CNN-CRF(SY)-SchemeA",
    ],
}

def extract_vocabs(file):
    words = dict()
    with open(file, "r") as fh:
        for l in fh:
            l = re.sub(benchmark.TAG_RX, "", l.strip())
            for w in l.split("|"):

                if not util.isthai(w):
                    continue

                if w in words:
                    words[w] += 1
                else:
                    words[w] = 1

    print(f"File: {file}")
    print(f" no. vocabs: {len(words)}")
    return words

if __name__ == "__main__":

    dataset = sys.argv[1]
    print(f"OOV for {dataset}")

    train_vocabs = extract_vocabs(TRAINING_SET)


    test_set = TEST_SET[dataset]
    test_vocabs = extract_vocabs(test_set)

    oov = set(test_vocabs.keys()).difference(train_vocabs.keys())

    total_oov_freq = 0

    for ov in oov:
        total_oov_freq += test_vocabs[ov]

    count_oov = len(oov)

    print(f"Test \ Train: {count_oov} oovs (freq: {total_oov_freq}).")     

    for k in KEYS[dataset]:
        print(f"-- {k} --")
        v = FILES[dataset][k]
        print(k, v)
        local_oov = dict()
        with open(test_set, "r") as ft, open(v, "r") as ff:

            for label, res in zip(ft, ff):
                label = benchmark.preprocessing(label.strip())
                res = benchmark.preprocessing(res.strip())


                bin_label = benchmark._binary_representation(label)
                bin_res = benchmark._binary_representation(res)

                wb_label = benchmark._find_word_boudaries(bin_label)
                wb_res = benchmark._find_word_boudaries(bin_res)

                # we switch reference here because we want to see whether words in label are tokenized correctly.
                indicators = benchmark._find_words_correctly_tokenised(wb_res, wb_label)

                assert len(indicators) == len(wb_label)

                label_raw = label.replace("|", "")

                for (st, end), ind in zip(wb_label, indicators):
                    word = label_raw[st:end]
                    if word in oov and ind:
                        if word in local_oov:
                            local_oov[word] += 1
                        else:
                            local_oov[word] = 1

        freq = np.sum(list(local_oov.values()))
        recall_freq = freq / total_oov_freq * 100
        count = len(local_oov)
        recall_count = count / count_oov * 100
        print(f"Correctly segmented OOV: {count} (freq: {freq})")
        print(f" recall count: {recall_count:2.2f} | recall freq: {recall_freq:2.2f}")
        print(f" {count:,d} ({freq:,d}) & {recall_count:2.2f}\% ({recall_freq:2.2f}\%)")
