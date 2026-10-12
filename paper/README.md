# Technical reports

**History Before Models.** Labelled history, small language models and cascades for request classification on local hardware. Draft 0.2, measured.

- English: [paper.pdf](paper.pdf), source [paper.md](paper.md). Italian version in preparation.

**The 5x Rule.** Choosing the third stage of a confidence-gated model cascade. Draft 0.1, simulation only, kept for reference.

- English: [five-x-rule.pdf](five-x-rule.pdf), source [five-x-rule.md](five-x-rule.md)
- Italiano: [five-x-rule.it.pdf](five-x-rule.it.pdf), sorgente [five-x-rule.it.md](five-x-rule.it.md)

## Rebuild

Figures are drawn from the CSV files in `results/`. Needs matplotlib, pandoc and a LaTeX engine.

```bash
python -m realtest.baselines --task departments    # data of figure 1
python paper/make_figure_history.py
python paper/make_figures.py                       # figures of the 5x rule report
cd paper
pandoc paper.md -o paper.pdf --pdf-engine=xelatex
pandoc five-x-rule.md -o five-x-rule.pdf --pdf-engine=xelatex
pandoc five-x-rule.it.md -o five-x-rule.it.pdf --pdf-engine=xelatex
```
