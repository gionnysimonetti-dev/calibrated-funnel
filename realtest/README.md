# Real-model test

A first, minimal run of the [real-model protocol](../docs/REAL_MODEL_PROTOCOL.md), sized for an office PC with no graphics card.

**Status: one full run, on the `departments` workload: [REPORT_departments.md](REPORT_departments.md).** The `banking77` workload has had only short trials.

## What it tests

The lower branch of the 5x rule: when neighbouring models are less than 5x apart in cost, a middle model should not pay and a deterministic stage should.

- **Models.** Four sizes of one open family, served locally by [Ollama](https://ollama.com): `qwen2.5` at 0.5b, 1.5b, 3b and 7b. They answer with the name of the category.
- **Confidence signal.** The probability the model gives to its whole answer: the product of the probabilities of its tokens.
- **Cost.** Compute seconds per request, as measured by the server.
- **Deterministic stage.** A lookup in the labelled history: it answers when the five closest past requests agree and the closest is similar enough. No model, about 0.3 ms per request.

## Two workloads

| Workload | What it is | Requests | History |
| --- | --- | --- | --- |
| `departments` | Requests to a virtual assistant, routed to one of 10 departments, each handling 15 topics. A triage workload. From [CLINC150](https://github.com/clinc/oos-eval), CC BY 3.0. | 4,500 | 15,000 |
| `banking77` | Customer requests to a bank, 77 fine-grained categories. A hard workload: many categories, close to each other. From [Banking77](https://github.com/PolyAI-LDN/task-specific-datasets), CC BY 4.0. | 3,080 | 10,003 |

## Run it

```bash
ollama pull qwen2.5:0.5b
ollama pull qwen2.5:1.5b
ollama pull qwen2.5:3b
ollama pull qwen2.5:7b

python -m realtest.run_models --task departments     # runs every model on every request
python -m realtest.analyze --task departments        # seconds; writes realtest/REPORT_departments.md
```

`run_models` can be stopped and restarted: stored requests are skipped. It prints the time left. For a short trial on a fixed subset, add `--limit 100`. `--shots N` shows the models N example requests per category, taken from the history.

Python needs only numpy and scipy. The datasets are downloaded on first use into `realtest/data/`.

## What is stored

`realtest/outputs/<workload>/<prompt variant>/<model>.jsonl`, one line per request: the answer, whether it is correct, the raw confidence, the log probability of each token of the answer, compute seconds. Every cascade design is then evaluated offline from these files, so no model has to run twice.

## How the result is read

The requests are split once, with a fixed seed, into a calibration half and a test half. Calibration, the confidence threshold and the similarity threshold of the lookup stage are all fitted on the calibration half, so that the whole cascade stays within half a point of the largest model alone. Every figure in the report comes from the test half, with 95% bootstrap intervals.

The report gives, for each small, middle, large triple of models: the measured cost step, what a middle model adds to the two-stage cascade, and what the lookup stage adds.

## The lookup stage alone

```bash
python -m realtest.lookup
```

Measured on the test half, with the similarity threshold set on the calibration half for 99% accuracy:

| Workload | Requests answered | Accuracy on what it answers |
| --- | --- | --- |
| `departments` | 62.5% | 98.7% |
| `banking77` | 28.6% | 99.5% |

The simulation assumed a rule stage 99.5% accurate, with a coverage chosen by hand.

## Trials so far

Short trials on 100 requests of `banking77`, on a PC with no graphics card. They are too small to conclude anything; they shaped the design.

| Prompt | 0.5b | 1.5b | 3b | 7b |
| --- | --- | --- | --- | --- |
| Category names only | 12% | 38% | 40% | 57% |
| Names with one example request each | 17% | 36% | 37% | 58% |

- A first version asked for the number of the category instead of its name: on 20 requests the largest model was right on 35% and the smallest on none. Models of this size cannot map a request to an index among 77.
- With names, the largest model is still right on fewer than 6 requests in 10. This workload is outside the zone where a cascade makes sense, which is why `departments` was added. `banking77` stays as the hard case.
- Measured compute per request: 0.13, 0.25, 0.42 and 0.80 seconds from the smallest to the largest model, a ladder of 1 : 1.9 : 3.2 : 6.2.

A trial on 100 requests of `departments`, names only: 39%, 53%, 65% and 80% from the smallest to the largest model, on a cost ladder of 1 : 1.7 : 3 : 6. Up to 20 answers in 100 were not recognised, because the model answered with the topic ("shopping list") instead of the department that handles it. A topic names its department without ambiguity, so such answers are now accepted; the analysis reads every answer again from the stored raw response.

## Limits

- Two tasks, one model family, one machine: a first measurement, not a validation.
- The four models span less than one order of magnitude in cost, so no triple reaches 5x. The upper branch of the rule needs a larger model.
- The lookup stage uses the whole labelled history; the models see the list of categories and, at most, a few examples. That is the situation of a team that has past tickets and no fine-tuned model.
- Costs are measured with the instructions cached between requests, as a server would run it.
