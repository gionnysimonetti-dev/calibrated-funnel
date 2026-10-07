# Use cases

A cascade is worth building only where the workload suits it. This page goes through the workloads where it tends to fit, what the stages are in practice, where the outcome data for calibration comes from, and when to leave it alone.

The figures quoted are simulated on illustrative profiles (experiment 7 in [results/RESULTS.md](../results/RESULTS.md)). They show which designs are worth measuring, not what a real system will save. Use `python -m funnel.planner` with your own figures.

## Before anything else: four numbers to measure

1. **Share of easy queries.** Run the smallest model on a sample with known answers. The share it gets right with high confidence is the ceiling of what a cascade can save.
2. **Rule coverage.** The share of queries a deterministic step can answer outright: an exact code, a lookup, a fixed business rule.
3. **Cost ladder.** Measured compute per query for each model you can run. What matters is the ratio between neighbours.
4. **Quality of the confidence signal.** How well the model's confidence separates right answers from wrong ones on that sample.

## Choosing the third stage

In these simulations the right third stage depends on the workload:

| Situation | Third stage | Why |
| --- | --- | --- |
| Models far apart in cost (5x or more between neighbours), weak confidence signal, mostly easy queries | A middle model | It catches what the small model cannot decide, at a fraction of the large model's cost: 7 to 12 points more saving |
| Models close in cost (about 3x between neighbours) | A deterministic rule stage, not a middle model | A rule stage adds 2 to 6 points; a middle model loses 4 to 10 |
| Models far apart in cost, good confidence signal | None | Two stages already capture the saving; a third adds 2 points at most |
| Few easy queries | No cascade | The large model alone is as cheap or cheaper |

The general form is the 5x rule in the [README](../README.md): under a 5x cost ratio between neighbouring models the third stage is rules, not a model.

## Ticket triage into a fixed taxonomy

Classifying or reclassifying service-desk tickets into a closed set of categories.

- **Why it fits.** Closed list of answers, high volumes, many unambiguous tickets, no user waiting on each one.
- **Stages.** Rules on source, sender and fixed keywords; a small model that classifies and reports its confidence; a large model for what remains uncertain.
- **Outcomes for calibration.** Operator corrections and approvals are a continuous stream of labelled outcomes, so confidence can be recalibrated as the ticket mix changes.
- **Cost of an error.** Uneven: mistaking an incident for a request can hide a missed service-level target. Use a stricter threshold for the category pairs that matter.
- **Simulated indication.** 80% easy, 30% rule coverage, good signal: two models are enough with far-apart costs (81%); with close costs a rule stage in front is the best design (74% against 72%).
- **Monitor.** A chi-square test on the weekly distribution of categories flags a new kind of fault or a change upstream.

## Catalogue and spare-part matching

Finding the right item in a large catalogue from a free-text request.

- **Why it fits.** The answer must come from the catalogue, never from the model. Deterministic filters do most of the work.
- **Stages.** Exact matches on codes and compatibility rules; a small model to map the customer's words to catalogue attributes and rank the survivors; a large model only to separate close candidates.
- **Outcomes for calibration.** Confirmed orders, returns for wrong part, operator overrides.
- **Cost of an error.** High: a wrong part means a return and often downtime. Below the confidence threshold, ask one more question or hand over to a person.
- **Simulated indication.** 70% easy, 50% rule coverage, good signal: two models are enough with far-apart costs (72%); with close costs the rule stage adds 5 points (67% against 62%).
- **Requirement.** Compatibility data must exist in structured form. Without it the first stage has nothing to filter on.

## Sales and support assistant turns

Routing each turn of a conversation to the cheapest model that can handle it.

- **Why it fits.** Many turns are simple (greetings, clarifications, catalogue facts); a few need real reasoning.
- **Stages.** Fixed handling for the simplest turns; a small model for routine ones; a large model for the rest.
- **Outcomes for calibration.** Harder to obtain: there is no single correct answer. Guardrail interventions, hand-overs to a person and conversions are the usable signals.
- **Cost of an error.** Depends on the turn: a wrong price is serious, an awkward greeting is not. Keep anything involving numbers out of the model altogether.
- **Simulated indication.** 60% easy, 10% rule coverage, weak signal: with far-apart costs the middle model is worth it (46% against 37% with two models); with close costs prefer rules plus two models (33%).
- **Caveat.** Latency and prompt caching work per model. On low traffic, running several models can cost more than it saves.

## Document field extraction

Pulling structured fields out of documents in batch.

- **Why it fits.** Batch work, no latency constraint, a mix of clean and messy documents.
- **Stages.** Pattern rules for fields with fixed formats; a small model for standard layouts; a large model for unusual ones.
- **Outcomes for calibration.** Validation rules (totals that add up, valid codes) and sampled human review.
- **Simulated indication.** 50% easy, 20% rule coverage, weak signal: with far-apart costs three models reach 39% against 33% with two; with close costs rules plus two models reach 29%.

## When not to use a cascade

- **Open-ended analysis and generation.** Few queries are easy and there is no clear notion of a correct answer to calibrate on. Simulated saving with 10% easy queries: 5% at best, negative with close costs.
- **Low volumes.** The engineering and the memory for several models are not repaid.
- **No outcome data.** Without outcomes there is no calibration, and an uncalibrated threshold is a guess.
- **A single GPU with no memory headroom.** Every extra model takes memory from the large one.
