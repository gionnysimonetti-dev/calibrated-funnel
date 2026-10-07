"""Combining correlated measurements and turning the result into a verified confidence."""
from __future__ import annotations

import math

import numpy as np
from scipy.stats import chi2


def measurement_covariance(reliability, error_correlation, noise_var):
    """Covariance matrix of the measurements of one candidate with true value ~ N(0, 1).

    Measurement f = r_f * mu + sqrt(1 - r_f^2) * e_f + noise_f, where the systematic errors
    e_f have unit variance and pairwise correlation `error_correlation`.
    Returns (total covariance, covariance of the error part only).
    """
    r = np.asarray(reliability, float)
    resid = np.sqrt(1 - r ** 2)
    corr = np.full((len(r), len(r)), float(error_correlation))
    np.fill_diagonal(corr, 1.0)
    error_cov = np.outer(resid, resid) * corr + np.diag(np.asarray(noise_var, float))
    return np.outer(r, r) + error_cov, error_cov


def inverse_covariance_weights(reliability, error_correlation, noise_var):
    """Weights of the best linear estimate of the true value, and its posterior variance."""
    r = np.asarray(reliability, float)
    total, _ = measurement_covariance(reliability, error_correlation, noise_var)
    w = np.linalg.solve(total, r)
    return w, float(1 - r @ w)


def gap_chi2(gap, weights, error_cov):
    """Chi-square statistic (1 d.o.f.) of the gap between the two leading candidates."""
    return np.asarray(gap, float) ** 2 / (2.0 * float(weights @ error_cov @ weights))


def chi2_confidence(statistic, dof=1):
    """Chi-square CDF: orders cases by confidence. It is a ranking, not a probability."""
    return chi2.cdf(statistic, dof)


def calibration_chi2(confidence, outcome, n_bins=10, min_count=30):
    """Does a declared confidence match the observed frequency of correct outcomes?

    statistic = sum over bins of n * (observed - declared)^2 / (declared * (1 - declared)).
    Returns dict with statistic, dof, p_value and the per-bin table.
    """
    confidence = np.asarray(confidence, float)
    outcome = np.asarray(outcome, float)
    idx = np.clip((confidence * n_bins).astype(int), 0, n_bins - 1)
    stat, rows = 0.0, []
    for b in range(n_bins):
        mask = idx == b
        n = int(mask.sum())
        if n < min_count:
            continue
        p = float(np.clip(confidence[mask].mean(), 1e-6, 1 - 1e-6))
        o = float(outcome[mask].mean())
        stat += n * (o - p) ** 2 / (p * (1 - p))
        rows.append({"declared": p, "observed": o, "n": n})
    dof = len(rows)
    return {"statistic": stat, "dof": dof, "p_value": float(chi2.sf(stat, dof)), "bins": rows}


def drift_chi2(observed, expected):
    """Pearson chi-square between observed and expected counts per category.

    Returns dict with statistic, dof, p_value, critical value at 5% and each category's
    share of the statistic, which tells where to look.
    """
    observed = np.asarray(observed, float)
    expected = np.asarray(expected, float)
    parts = (observed - expected) ** 2 / expected
    stat = float(parts.sum())
    dof = len(observed) - 1
    return {
        "statistic": stat,
        "dof": dof,
        "p_value": float(chi2.sf(stat, dof)),
        "critical_5pct": float(chi2.ppf(0.95, dof)),
        "shares": (parts / stat if stat > 0 else parts).tolist(),
    }
