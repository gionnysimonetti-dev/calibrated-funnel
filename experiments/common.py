"""Shared helpers: deterministic seeds, CSV output, Markdown tables."""
from __future__ import annotations

import csv
import pathlib
import zlib

import numpy as np

RESULTS = pathlib.Path(__file__).resolve().parent.parent / "results"
RESULTS.mkdir(exist_ok=True)
BASE_SEED = 20261007


def rng_for(*key) -> np.random.Generator:
    """Independent, reproducible generator for one experimental cell."""
    return np.random.default_rng([BASE_SEED, zlib.crc32(repr(key).encode())])


def seed_for(*key) -> int:
    return int(zlib.crc32(repr((BASE_SEED,) + key).encode()))


def write_csv(name: str, header, rows) -> None:
    with open(RESULTS / name, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)


def md_table(header, rows) -> str:
    lines = ["| " + " | ".join(str(h) for h in header) + " |",
             "| " + " | ".join("---" for _ in header) + " |"]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(lines)


def pct(x, digits=0) -> str:
    return f"{100 * x:.{digits}f}%"
