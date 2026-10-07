# Method and assumptions

This page states precisely what the simulations assume and compute. Everything here is standard statistics; the references are in the README.

## 1. Confidence-gated cascade (`funnel/routing.py`)

**Workload.** Each query has a latent difficulty `d`. A share `easy_fraction` of queries is easy, `d ~ N(-2.5, 0.5)`; the rest is hard, `d ~ N(1.0, 1.0)`.

**Models.** Model `f` has ability `a_f` (1.0, 1.8, 2.4) and relative cost `c_f` (1, 8, 70). It answers correctly when `a_f - d + eps > 0`, with `eps ~ N(0, 1)`.

**Confidence signal.** Each model emits a raw signal `q_f = (a_f - d) + s * z`, `z ~ N(0, 1)`. The noise `s` sets the quality of the signal: 0.5 is "good", 1.5 is "weak".

**Calibration.** The raw signal is split into 200 quantile bins on a calibration sample. The calibrated confidence of a bin is the observed frequency of correct answers in it.

**Routing rule.** Stages run in order. A stage's answer is accepted when its calibrated confidence reaches the threshold `theta`; otherwise the query moves to the next stage. The last stage always answers.

**Rule stage (optional).** A deterministic step runs before the models: exact lookups, business rules. It answers a share `coverage` of all queries, always easy ones, with accuracy 0.995, at a fixed cost of 0.01 paid by every query. Its answers are always accepted; everything else moves on to the models.

**Choosing the threshold.** `theta` is the value, from a fixed grid, with the lowest mean cost on the calibration sample among those whose accuracy stays within a tolerance (0.5 points) of the largest model alone. The grid includes "never accept early", so a feasible value always exists.

**Reporting.** Accuracy, cost and saving are measured on an independent test sample. Saving is `1 - cost / c_largest`.

## 2. Staged elimination (`funnel/selection.py`)

**Problem.** `N` candidates have true values `mu_i ~ N(0, 1)`. One evaluation returns `mu_i + N(0, sigma^2)`. With a total budget of `B` evaluations, pick the candidate with the largest `mu`.

**Procedure.** The budget is divided among `S` elimination stages and a final choice. In each stage every surviving candidate gets the same number of evaluations; evaluations accumulate across stages; the top `ceil(k / eta_s)` candidates survive. The final choice uses fresh evaluations only.

**Schedules.** `geometric_schedule(N, finalists, S, g)` returns coefficients `a, a*g, a*g^2, ...` whose product is `N / finalists`. `g = 1` means equal coefficients; `g > 1` cuts lightly first.

## 3. Cascade of evaluators (`funnel/selection.py`)

Evaluator `f` has reliability `r_f` and cost `c_f`. Its noiseless score for a candidate is

```
proxy_f = r_f * mu + sqrt(1 - r_f^2) * e_f
```

where `e_f` is a systematic error with unit variance, fixed for that candidate and evaluator. Repeating the evaluation averages out the measurement noise but not `e_f`. The errors of different evaluators have pairwise correlation `error_correlation`.

When a stage's budget cannot cover every surviving candidate once, a random subset is evaluated and the rest are dropped. The budget is never exceeded.

## 4. Combining measurements (`funnel/confidence.py`)

For one candidate, the vector of measurements `x` has covariance

```
Sigma = r r' + E,     E_fg = sqrt(1 - r_f^2) * sqrt(1 - r_g^2) * corr_fg + delta_fg * noise_var_f
```

The best linear estimate of the true value is `m = w' x` with `w = Sigma^-1 r`, and posterior variance `1 - r' w`. When errors are strongly correlated the cheap evaluator gets a negative weight: it is used to subtract the shared error.

## 5. Confidence in the final choice

**Ranking statistic.** With `m_1` and `m_2` the two highest estimates,

```
chi2 = (m_1 - m_2)^2 / (2 * w' E w)
```

follows a chi-square distribution with one degree of freedom when the two candidates are truly equal. Its CDF ranks cases by confidence. It is not the probability that the choice is correct.

**Probability.** The probability that the leader is the best finalist is estimated by sampling each finalist's value from `N(m_i, 1 - r' w)`.

## 6. Verifying calibration and detecting drift

**Calibration test.** Group cases into bins of declared confidence. With `p_b` the mean declared confidence, `o_b` the observed frequency of correct outcomes and `n_b` the number of cases in bin `b`:

```
chi2 = sum over b of n_b * (o_b - p_b)^2 / (p_b * (1 - p_b))
```

compared with a chi-square distribution with as many degrees of freedom as bins. A large value means the declared confidence no longer matches reality and must be recalibrated.

**Drift test.** With observed and expected counts per category:

```
chi2 = sum over categories of (observed - expected)^2 / expected
```

with `categories - 1` degrees of freedom. Each category's share of the statistic shows where the change is.

Worked example: expected 160 / 100 / 100 / 40, observed 130 / 110 / 120 / 40 gives 5.63 + 1.00 + 4.00 + 0 = 10.63, above the 5% critical value of 7.81 for three degrees of freedom.
