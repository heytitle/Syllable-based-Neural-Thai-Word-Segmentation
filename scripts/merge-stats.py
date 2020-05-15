#!/usr/bin/env python

"""eval.py

Usage:
  merge-stats.py --model-group=<model-group>

"""

from docopt import docopt
import json


from glob import glob
import pandas as pd
import yaml

if __name__ == "__main__":
    arguments = docopt(__doc__)

    model_group = arguments["--model-group"]

    data = []

    for sf in glob(model_group):
        # read params
        with open(f"{sf}/params.yml") as fh:
            dd = yaml.full_load(fh)

        # check if it exits
        with open(f"{sf}/best-test.json") as fh:
            st = json.load(fh)
            dd = dict(**dd, **st)

        data.append(dd)

    df = pd.DataFrame(data)
    dest = "/".join(model_group.split("/")[:-1]) + "/stats.csv"
    print(f"saving file to {dest}")
    df.to_csv(dest, index=False)

