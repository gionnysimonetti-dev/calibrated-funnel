# Real-model protocol (planned, not yet run)

The simulations make assumptions that only real models can confirm or refute. This is the experiment that would do it. It is a draft: criticism is welcome before it is run.

## Setup

- **Models.** Three open-weight models of clearly different size, served locally behind the same API.
- **Data.** A public benchmark with known answers, a few thousand items at least, scored automatically. Items are split once, with a fixed seed, into a calibration half and a test half.
- **Confidence signal.** The probability the model assigns to its answer (or the margin between its two most likely answers). Agreement across repeated samples is a second candidate.
- **Cost.** Measured, not assumed: GPU seconds and tokens per query for each model.

## Procedure

1. Run all three models on every item once. Store the answer, whether it is correct, the confidence signal and the measured cost.
2. Fit the calibration of each model's signal on the calibration half.
3. Choose the threshold on the calibration half: the cheapest one whose accuracy stays within the tolerance of the largest model alone.
4. Evaluate every design offline on the test half. Because step 1 stores everything, no model needs to be run again.

## Comparisons

- Largest model alone.
- Two-stage cascade (small, large) against three-stage (small, medium, large).
- Calibrated confidence against the raw signal with a hand-tuned threshold.
- A deterministic rule stage in front of the models, where the task allows one.
- The same designs on model sets with close and with far-apart costs.
- Published methods where their code is available.

## What to report

- Compute saved at equal accuracy, with bootstrap confidence intervals.
- Calibration error and the chi-square calibration test, before and after calibration.
- Share of queries answered at each stage.
- Correlation between the models' errors: do they fail on the same items?

## What would count against the method

- A third stage, middle model or rule stage, never beating two stages at equal accuracy.
- The predicted boundaries (cost spread, signal quality) not matching what is measured.
- Confidence signals too weak for any threshold to hold accuracy.
- Savings that vanish once the measured cost of running the smaller models first is included.

Negative results will be published here as they are.
