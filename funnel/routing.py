"""Confidence-gated cascade of models of increasing size (synthetic world).

Each query has a latent difficulty d. Model f with ability a_f answers correctly when
a_f - d + eps > 0, eps ~ N(0, 1). Each model also emits a raw confidence signal
q_f = (a_f - d) + signal_noise * z, z ~ N(0, 1): the larger signal_noise, the weaker the signal.

The raw signal is never used directly. It is mapped to a calibrated probability of being
correct, estimated on a separate calibration sample, and the cascade stops at the first
stage whose calibrated confidence reaches a threshold.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

NEVER = 1.01  # threshold that no calibrated confidence can reach: always escalate
DEFAULT_THRESHOLDS = (0.80, 0.85, 0.90, 0.93, 0.95, 0.97, 0.98, 0.99, 0.995, NEVER)


@dataclass(frozen=True)
class RoutingWorld:
    """Parameters of the synthetic workload."""

    abilities: tuple = (1.0, 1.8, 2.4)   # small, medium, large model
    costs: tuple = (1.0, 8.0, 70.0)      # relative compute per query
    easy_fraction: float = 0.7           # share of easy queries
    signal_noise: float = 0.5            # 0.5 = good confidence signal, 1.5 = weak
    easy_mean: float = -2.5
    easy_sd: float = 0.5
    hard_mean: float = 1.0
    hard_sd: float = 1.0


def sample(world: RoutingWorld, n: int, rng: np.random.Generator, return_easy: bool = False):
    """Draw n queries. Returns (correct, signal), each of shape (n_models, n)."""
    easy = rng.random(n) < world.easy_fraction
    d = np.where(
        easy,
        rng.normal(world.easy_mean, world.easy_sd, n),
        rng.normal(world.hard_mean, world.hard_sd, n),
    )
    k = len(world.abilities)
    margin = np.asarray(world.abilities, float)[:, None] - d[None, :]
    correct = margin + rng.standard_normal((k, n)) > 0
    signal = margin + world.signal_noise * rng.standard_normal((k, n))
    if return_easy:
        return correct, signal, easy
    return correct, signal


class BinnedCalibrator:
    """Maps a raw signal to the observed frequency of correct answers, by quantile bins."""

    def __init__(self, n_bins: int = 200):
        self.n_bins = n_bins
        self.edges_ = None
        self.accuracy_ = None

    def fit(self, signal: np.ndarray, correct: np.ndarray) -> "BinnedCalibrator":
        qs = np.linspace(0, 1, self.n_bins + 1)[1:-1]
        self.edges_ = np.quantile(signal, qs)
        idx = np.searchsorted(self.edges_, signal)
        hits = np.bincount(idx, weights=correct.astype(float), minlength=self.n_bins)
        count = np.bincount(idx, minlength=self.n_bins)
        self.accuracy_ = hits / np.maximum(count, 1)
        return self

    def predict(self, signal: np.ndarray) -> np.ndarray:
        return self.accuracy_[np.searchsorted(self.edges_, signal)]


@dataclass(frozen=True)
class RuleStage:
    """A deterministic first stage: exact matches, lookups, business rules.

    It answers a share `coverage` of all queries (always easy ones) with accuracy
    `accuracy`, at a small fixed cost paid by every query, and passes the rest on.
    """

    coverage: float = 0.3
    accuracy: float = 0.995
    cost: float = 0.01


def sample_rules(rule: RuleStage, world: RoutingWorld, easy: np.ndarray, rng: np.random.Generator):
    """Which queries the rule stage answers, and whether those answers are correct."""
    rate = min(1.0, rule.coverage / world.easy_fraction) if world.easy_fraction > 0 else 0.0
    fired = easy & (rng.random(easy.size) < rate)
    return fired, rng.random(easy.size) < rule.accuracy


def run_cascade(correct, confidence, costs, stages, threshold, rule=None):
    """Run the cascade over the given stages (indices into the model list).

    rule: optional (cost, fired, rule_correct) for a deterministic stage that runs first.
    Returns (accuracy, mean cost per query, share of queries answered at each stage).
    """
    n = correct.shape[1]
    done = np.zeros(n, bool)
    ok = np.zeros(n, bool)
    spent = np.zeros(n)
    shares = []
    if rule is not None:
        rule_cost, fired, rule_correct = rule
        spent += rule_cost
        ok[fired] = rule_correct[fired]
        done |= fired
        shares.append(float(fired.mean()))
    for j, f in enumerate(stages):
        active = ~done
        spent += active * costs[f]
        last = j == len(stages) - 1
        stop = active & ((confidence[f] >= threshold) | last)
        ok[stop] = correct[f][stop]
        done |= stop
        shares.append(float(stop.mean()))
    return float(ok.mean()), float(spent.mean()), shares


def evaluate(world: RoutingWorld, stages=(0, 1, 2), n_calibration=300_000, n_test=300_000,
             tolerance=0.005, thresholds=DEFAULT_THRESHOLDS, seed=0, rule: RuleStage | None = None) -> dict:
    """Calibrate and choose the threshold on one sample, report on an independent one.

    The threshold is the cheapest one whose calibration-sample accuracy stays within
    `tolerance` of the largest model alone. All reported figures come from the test sample.
    With `rule`, a deterministic stage runs before the models.
    """
    rng = np.random.default_rng(seed)
    c_cal, s_cal, easy_cal = sample(world, n_calibration, rng, return_easy=True)
    c_test, s_test, easy_test = sample(world, n_test, rng, return_easy=True)
    costs = np.asarray(world.costs, float)
    big = stages[-1]
    rule_cal = rule_test = None
    if rule is not None:
        rule_rng = np.random.default_rng([seed, 1])
        rule_cal = (rule.cost,) + sample_rules(rule, world, easy_cal, rule_rng)
        rule_test = (rule.cost,) + sample_rules(rule, world, easy_test, rule_rng)

    calibrators = {f: BinnedCalibrator().fit(s_cal[f], c_cal[f]) for f in stages}
    conf_cal = {f: calibrators[f].predict(s_cal[f]) for f in stages}
    conf_test = {f: calibrators[f].predict(s_test[f]) for f in stages}

    target = c_cal[big].mean() - tolerance
    best = None
    for th in thresholds:
        acc, cost, _ = run_cascade(c_cal, conf_cal, costs, stages, th, rule_cal)
        if acc >= target and (best is None or cost < best[1]):
            best = (th, cost)
    threshold = best[0]

    acc, cost, shares = run_cascade(c_test, conf_test, costs, stages, threshold, rule_test)
    big_acc = float(c_test[big].mean())
    return {
        "threshold": threshold,
        "accuracy": acc,
        "big_accuracy": big_acc,
        "accuracy_delta": acc - big_acc,
        "cost": cost,
        "big_cost": float(costs[big]),
        "saving": 1.0 - cost / float(costs[big]),
        "stage_shares": shares,
    }
