"""The test workload: Banking77, public customer-service requests in 77 intent categories.

Source: PolyAI, https://github.com/PolyAI-LDN/task-specific-datasets (CC BY 4.0).
Casanueva et al., "Efficient Intent Detection with Dual Sentence Encoders", 2020.

The training split (10,003 labelled requests) plays the role of the ticket history that a
deterministic lookup stage can search. The test split (3,080 requests) is the workload.
"""
from __future__ import annotations

import csv
import json
import pathlib
import urllib.request

import numpy as np

URL = "https://raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets/master/banking_data/"
FILES = ("train.csv", "test.csv", "categories.json")
DATA = pathlib.Path(__file__).resolve().parent / "data"
SEED = 20261007


def fetch() -> None:
    """Download the three files once into realtest/data/."""
    DATA.mkdir(exist_ok=True)
    for name in FILES:
        target = DATA / name
        if not target.exists():
            print("downloading", name)
            urllib.request.urlretrieve(URL + name, target)


def load():
    """Returns (categories, train, test); train and test are lists of (text, category index)."""
    fetch()
    categories = json.loads((DATA / "categories.json").read_text(encoding="utf-8"))
    index = {name: i for i, name in enumerate(categories)}

    def read(name):
        with open(DATA / name, newline="", encoding="utf-8") as fh:
            return [(row["text"].strip(), index[row["category"]]) for row in csv.DictReader(fh)]

    return categories, read("train.csv"), read("test.csv")


def select(n_test: int, limit: int | None, seed: int = SEED) -> np.ndarray:
    """A fixed random subset of test items, in a fixed order. Same seed, same items."""
    order = np.random.default_rng(seed).permutation(n_test)
    return order if limit is None else order[:limit]


def split(n: int, seed: int = SEED) -> np.ndarray:
    """Boolean mask over n items: True = calibration half, False = test half."""
    mask = np.zeros(n, bool)
    mask[np.random.default_rng([seed, 1]).permutation(n)[: n // 2]] = True
    return mask
