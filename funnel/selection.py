"""Staged elimination among many noisy candidates.

Problem: N candidates with unknown true values mu_i ~ N(0, 1). Each evaluation returns
mu_i plus noise. With a fixed evaluation budget, find the candidate with the largest mu.

`staged_elimination` spends the budget in rounds, discarding a fraction of the candidates
after each round. `multifidelity_cascade` does the same with evaluators of different cost
and accuracy (cheap and rough first, expensive and precise last).
"""
from __future__ import annotations

import math

import numpy as np


def geometric_schedule(n_candidates: int, n_finalists: int, n_stages: int, growth: float = 1.0):
    """Reduction coefficients for each stage: a, a*g, a*g^2, ... with product N / finalists.

    growth = 1 gives equal coefficients; growth > 1 cuts lightly first and harder later.
    """
    if n_stages == 0:
        return []
    product = n_candidates / n_finalists
    first = product ** (1 / n_stages) / growth ** ((n_stages - 1) / 2)
    if first <= 1.0:
        raise ValueError("schedule not feasible: the first coefficient would not reduce anything")
    return [first * growth ** i for i in range(n_stages)]


def _keep_top(score: np.ndarray, k: int) -> np.ndarray:
    n = score.shape[1]
    threshold = np.partition(score, n - k, axis=1)[:, n - k][:, None]
    return score >= threshold


def staged_elimination(n_candidates, sigma, budget_per_candidate, etas, shares=None,
                       n_trials=2000, rng=None) -> float:
    """Probability of picking the truly best candidate.

    etas    reduction coefficient of each elimination stage (keep ceil(k / eta)).
            An empty list means no elimination: the whole budget is spread uniformly.
    shares  fraction of the budget for each stage plus the final choice (default: equal).
    Evaluations accumulate across elimination stages; the final choice uses fresh data only.
    """
    rng = rng or np.random.default_rng()
    n, t, s = n_candidates, n_trials, len(etas)
    shares = shares or [1 / (s + 1)] * (s + 1)
    budget = budget_per_candidate * n
    mu = rng.standard_normal((t, n))
    best = mu.argmax(1)
    alive = np.ones((t, n), bool)
    k = n
    total = np.zeros((t, n))
    count = 0
    for i, eta in enumerate(etas):
        reps = max(1, int(shares[i] * budget // k))
        total += reps * (mu + sigma / math.sqrt(reps) * rng.standard_normal((t, n)))
        count += reps
        k = max(1, math.ceil(k / eta))
        alive = _keep_top(np.where(alive, total / count, -np.inf), k)
    reps = max(1, int(shares[s] * budget // k))
    final = mu + sigma / math.sqrt(reps) * rng.standard_normal((t, n))
    pick = np.where(alive, final, -np.inf).argmax(1)
    return float((pick == best).mean())


def multifidelity_cascade(n_candidates, reliability, costs, fidelities, etas, budget,
                          sigma=1.0, shares=None, error_correlation=0.0,
                          n_trials=2000, rng=None) -> float:
    """Staged elimination with evaluators of different cost and accuracy.

    reliability[f]  correlation between evaluator f's noiseless score and the true value.
    costs[f]        cost of one evaluation with evaluator f.
    fidelities      evaluator used at each elimination stage, then at the final choice.
    error_correlation  correlation between the systematic errors of different evaluators.
    When the stage budget cannot cover every surviving candidate once, a random subset is
    evaluated and the rest are dropped: the budget is never exceeded.
    """
    rng = rng or np.random.default_rng()
    n, t, s = n_candidates, n_trials, len(etas)
    shares = shares or [1 / (s + 1)] * (s + 1)
    mu = rng.standard_normal((t, n))
    best = mu.argmax(1)
    common = rng.standard_normal((t, n))
    c = error_correlation
    proxy = {}
    for f in set(fidelities):
        r = reliability[f]
        own = rng.standard_normal((t, n))
        proxy[f] = r * mu + math.sqrt(1 - r * r) * (math.sqrt(c) * common + math.sqrt(1 - c) * own)

    alive = np.ones((t, n), bool)
    k = n
    running = {}

    def measure(f, stage_budget):
        nonlocal alive, k
        reps = int(stage_budget // (costs[f] * k))
        if reps >= 1:
            x = proxy[f] + sigma / math.sqrt(reps) * rng.standard_normal((t, n))
            if running.get(f) is not None:
                tot, cnt = running[f]
                tot, cnt = tot + reps * x, cnt + reps
                running[f] = (tot, cnt)
                x = tot / cnt
            else:
                running[f] = (reps * x, reps)
            return np.where(alive, x, -np.inf), k
        affordable = int(stage_budget // costs[f])
        running[f] = None
        if affordable < 1:
            return None, k
        key = np.where(alive, rng.random((t, n)), -1.0)
        seen = alive & _keep_top(key, affordable)
        x = proxy[f] + sigma * rng.standard_normal((t, n))
        return np.where(seen, x, -np.inf), affordable

    for i, eta in enumerate(etas):
        score, evaluated = measure(fidelities[i], shares[i] * budget)
        if score is None:
            continue
        k = max(1, math.ceil(evaluated / eta))
        alive = _keep_top(score, k)
    score, _ = measure(fidelities[s], shares[s] * budget)
    if score is None:
        score = np.where(alive, rng.random((t, n)), -np.inf)
    return float((score.argmax(1) == best).mean())
