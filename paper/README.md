# Technical report

*The 5x Rule: Choosing the Third Stage of a Confidence-Gated Model Cascade.* Draft 0.1, simulation only.

- English: [paper.pdf](paper.pdf), source [paper.md](paper.md)
- Italiano: [paper.it.pdf](paper.it.pdf), sorgente [paper.it.md](paper.it.md)

## Rebuild

The figures are drawn from the CSV files in `results/`. Needs matplotlib, pandoc and a LaTeX engine.

```bash
python paper/make_figures.py
cd paper
pandoc paper.md -o paper.pdf --pdf-engine=xelatex
pandoc paper.it.md -o paper.it.pdf --pdf-engine=xelatex
```
