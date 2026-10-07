"""Experiment 5. Do "special" number sequences make better reduction coefficients?

Question: do primes, Fibonacci numbers or other named sequences beat a generic schedule
with the same overall reduction? Each sequence is tested on the problem size it fits
(candidates = 2 x product of the three coefficients), on noisy data.
"""
import math

from funnel.selection import geometric_schedule, staged_elimination

from .common import md_table, pct, rng_for, write_csv

SIGMA = 3.0
BUDGET = 16
TRIALS = 6000
SEQUENCES = (
    ("Fibonacci 3, 5, 8", (3, 5, 8)),
    ("Fibonacci 5, 8, 13", (5, 8, 13)),
    ("Primes 3, 5, 7", (3, 5, 7)),
    ("Primes 5, 7, 11", (5, 7, 11)),
    ("Powers of two 2, 4, 8", (2, 4, 8)),
    ("Squares 4, 9, 16", (4, 9, 16)),
    ("Factorials 2, 6, 24", (2, 6, 24)),
)


def run() -> str:
    rows = []
    for name, seq in SEQUENCES:
        n = 2 * math.prod(seq)
        named = staged_elimination(n, SIGMA, BUDGET, list(seq), n_trials=TRIALS, rng=rng_for("exp5", name, "named"))
        equal = staged_elimination(n, SIGMA, BUDGET, geometric_schedule(n, 2, 3, 1.0), n_trials=TRIALS,
                                   rng=rng_for("exp5", name, "equal"))
        generic = staged_elimination(n, SIGMA, BUDGET, geometric_schedule(n, 2, 3, 1.4), n_trials=TRIALS,
                                     rng=rng_for("exp5", name, "generic"))
        rows.append([name, n, round(named, 4), round(equal, 4), round(generic, 4)])
    write_csv("exp5_named_sequences.csv",
              ["sequence", "candidates", "named_sequence", "equal_coefficients", "generic_growth_1.4"], rows)
    return "\n".join([
        "## Experiment 5. Named number sequences as reduction coefficients\n",
        f"Noisy data, {BUDGET} evaluations per candidate, 2 finalists, {TRIALS} trials "
        "(standard error about 0.6 points). Probability of picking the truly best candidate.\n",
        md_table(["Sequence", "Candidates", "Named sequence", "Equal coefficients", "Generic growth 1.4"],
                 [[r[0], r[1], pct(r[2]), pct(r[3]), pct(r[4])] for r in rows]) + "\n"])


if __name__ == "__main__":
    print(run())
