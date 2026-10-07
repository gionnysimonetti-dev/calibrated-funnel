"""The test workloads: two public sets of real requests, each with a labelled history.

banking77    Customer requests to a bank, 77 fine-grained categories. A hard workload: the
             categories are many and close to each other.
             PolyAI, https://github.com/PolyAI-LDN/task-specific-datasets (CC BY 4.0).
             Casanueva et al., "Efficient Intent Detection with Dual Sentence Encoders", 2020.

departments  Requests to a virtual assistant, routed to one of 10 departments (the domains of
             CLINC150; each department handles 15 topics). A triage workload.
             https://github.com/clinc/oos-eval (CC BY 3.0).
             Larson et al., "An Evaluation Dataset for Intent Classification and
             Out-of-Scope Prediction", 2019.

In both, the training split plays the role of the ticket history that a deterministic
lookup stage can search, and the test split is the workload.
"""
from __future__ import annotations

import csv
import json
import pathlib
import re
import urllib.request
from dataclasses import dataclass

import numpy as np

DATA = pathlib.Path(__file__).resolve().parent / "data"
SEED = 20261007
SOURCES = {
    "banking77": ("https://raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets/master/banking_data/",
                  ("train.csv", "test.csv", "categories.json")),
    "departments": ("https://raw.githubusercontent.com/clinc/oos-eval/master/data/",
                    ("data_full.json", "domains.json")),
}


@dataclass(frozen=True)
class Task:
    name: str
    title: str             # one line for reports
    instruction: str       # first sentence of the prompt
    noun: str              # what a category is called in the prompt
    categories: tuple      # names as shown to the model and expected back
    descriptions: tuple    # one per category, or empty strings
    train: tuple           # (text, category index): the labelled history
    test: tuple            # (text, category index): the workload


def display(name: str) -> str:
    """'card_arrival' -> 'card arrival'."""
    return re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()


def fetch(task: str) -> pathlib.Path:
    """Download the files of a task once into realtest/data/<task>/."""
    url, files = SOURCES[task]
    folder = DATA / task
    folder.mkdir(parents=True, exist_ok=True)
    for name in files:
        if not (folder / name).exists():
            print("downloading", name)
            urllib.request.urlretrieve(url + name, folder / name)
    return folder


def load(task: str) -> Task:
    folder = fetch(task)
    if task == "banking77":
        names = json.loads((folder / "categories.json").read_text(encoding="utf-8"))
        index = {name: i for i, name in enumerate(names)}

        def read(name):
            with open(folder / name, newline="", encoding="utf-8") as fh:
                return tuple((row["text"].strip(), index[row["category"]]) for row in csv.DictReader(fh))

        return Task(task, "customer requests to a bank, 77 categories (Banking77)",
                    "You classify customer requests sent to a bank.", "category",
                    tuple(display(n) for n in names), ("",) * len(names), read("train.csv"), read("test.csv"))

    domains = json.loads((folder / "domains.json").read_text(encoding="utf-8"))
    full = json.loads((folder / "data_full.json").read_text(encoding="utf-8"))
    names = list(domains)
    department = {intent: i for i, name in enumerate(names) for intent in domains[name]}

    def read(split):
        return tuple((text.strip(), department[intent]) for text, intent in full[split])

    return Task(task, "requests to a virtual assistant, routed to 10 departments (CLINC150 domains)",
                "You route requests sent to a virtual assistant to the department that handles them.", "department",
                tuple(display(n) for n in names),
                tuple(", ".join(display(i) for i in domains[n]) for n in names), read("train"), read("test"))


def select(n_test: int, limit: int | None, seed: int = SEED) -> np.ndarray:
    """A fixed random subset of test items, in a fixed order. Same seed, same items."""
    order = np.random.default_rng(seed).permutation(n_test)
    return order if limit is None else order[:limit]


def split(n: int, seed: int = SEED) -> np.ndarray:
    """Boolean mask over n items: True = calibration half, False = test half."""
    mask = np.zeros(n, bool)
    mask[np.random.default_rng([seed, 1]).permutation(n)[: n // 2]] = True
    return mask
