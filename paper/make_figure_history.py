"""Figure 1 of the report: how much labelled history the classifier needs, against a language model.

Reads results/realtest_departments_history_curve.csv (written by python -m realtest.baselines)
and writes an English and an Italian version.

Usage:  python paper/make_figure_history.py
"""
import csv
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
SOURCE = HERE.parent / "results" / "realtest_departments_history_curve.csv"
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e3e2dd"
BLUE, ORANGE = "#2a78d6", "#eb6834"
TEXT = {
    "en": {"suffix": "", "x": "labelled past requests per category (log scale)", "y": "right answers on the test half",
           "clf": "classifier on the history", "hyb": "classifier, then 7.6B model when unsure",
           "llm": "7.6B model alone, no examples", "all": "all"},
    "it": {"suffix": "_it", "x": "richieste passate etichettate per categoria (scala logaritmica)",
           "y": "risposte giuste sulla metà di test", "clf": "classificatore sullo storico",
           "hyb": "classificatore, poi modello da 7,6 mld se incerto", "llm": "modello da 7,6 mld da solo, senza esempi",
           "all": "tutte"},
}
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8.5, "axes.edgecolor": MUTED, "axes.labelcolor": MUTED,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
                     "savefig.bbox": "tight", "savefig.pad_inches": 0.05})

rows = list(csv.DictReader(open(SOURCE, newline="")))
full = 1500                                    # 15,000 labelled requests over 10 categories
x = [full if r["per_category"] == "all" else int(r["per_category"]) for r in rows]
for lang, t in TEXT.items():
    fig, ax = plt.subplots(figsize=(6.2, 3.3))
    ax.axhline(float(rows[0]["llm_alone"]) * 100, color=MUTED, lw=1.2, ls="--", label=t["llm"])
    ax.fill_between(x, [float(r["classifier_min"]) * 100 for r in rows], [float(r["classifier_max"]) * 100 for r in rows],
                    color=BLUE, alpha=0.15, lw=0)
    ax.plot(x, [float(r["classifier"]) * 100 for r in rows], color=BLUE, lw=2, marker="o", ms=3.5, label=t["clf"])
    ax.plot(x, [float(r["hybrid"]) * 100 for r in rows], color=ORANGE, lw=2, marker="o", ms=3.5, label=t["hyb"])
    ax.set_xscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{t['all']}\n(1,500)" if v == full else str(v) for v in x])
    ax.minorticks_off()
    ax.set_ylim(0, 100)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_xlabel(t["x"])
    ax.set_ylabel(t["y"])
    ax.legend(frameon=False, loc="lower right")
    fig.savefig(HERE / f"fig1_history_curve{t['suffix']}.pdf")
    fig.savefig(HERE / f"fig1_history_curve{t['suffix']}.png", dpi=160)
    plt.close(fig)
