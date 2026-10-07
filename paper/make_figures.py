"""Figures for the technical report, drawn from the CSV files in results/.

Writes an English and an Italian version of each figure.

Usage:  python paper/make_figures.py
"""
import csv
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
RESULTS = HERE.parent / "results"
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e3e2dd"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
SIGNALS = ("good", "medium", "weak")
RATIOS = (2, 3, 4, 5, 6, 8, 10)
TEXT = {
    "en": {"suffix": "", "good": "Good signal", "medium": "Medium signal", "weak": "Weak signal",
           "y": "points of saving gained or lost", "x": "cost ratio between neighbouring models",
           "middle": "middle model", "rules10": "rules, 10% coverage", "rules30": "rules, 30% coverage"},
    "it": {"suffix": "_it", "good": "Segnale buono", "medium": "Segnale medio", "weak": "Segnale debole",
           "y": "punti di risparmio guadagnati o persi", "x": "rapporto di costo fra modelli vicini",
           "middle": "modello intermedio", "rules10": "regole, copertura 10%", "rules30": "regole, copertura 30%"},
}

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 8.5, "axes.edgecolor": MUTED, "axes.labelcolor": MUTED,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
    "axes.titlesize": 9.5, "axes.titleweight": "bold", "axes.titlecolor": INK, "axes.titlelocation": "left",
    "savefig.bbox": "tight", "savefig.pad_inches": 0.05,
})


def read(name):
    with open(RESULTS / name, newline="") as fh:
        return list(csv.DictReader(fh))


def frame(ax, lo, hi):
    ax.axhline(0, color=INK, linewidth=0.9, zorder=2)
    ax.axvline(5, color=MUTED, linewidth=0.8, linestyle=(0, (3, 3)), zorder=1)
    ax.set_xscale("log")
    ax.set_xticks(RATIOS)
    ax.set_xticklabels([f"{r}x" if r != 6 else "" for r in RATIOS])
    ax.minorticks_off()
    ax.set_ylim(lo, hi)
    ax.grid(axis="y", color=GRID, linewidth=0.6, zorder=0)
    ax.tick_params(length=0)


def band(ax, cells, color, label, marker="o", linestyle="-"):
    """Mean across easy-query shares as a line, minimum to maximum as a band."""
    lo = [100 * min(cells[r]) for r in RATIOS]
    hi = [100 * max(cells[r]) for r in RATIOS]
    mean = [100 * sum(cells[r]) / len(cells[r]) for r in RATIOS]
    ax.fill_between(RATIOS, lo, hi, color=color, alpha=0.16, linewidth=0, zorder=3)
    ax.plot(RATIOS, mean, color=color, linewidth=2, marker=marker, markersize=4.5, linestyle=linestyle,
            markeredgecolor="white", markeredgewidth=0.8, label=label, zorder=4)


def figure_middle_model(t):
    rows = read("exp8a_middle_model_by_ratio.csv")
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.6), sharey=True)
    for ax, signal in zip(axes, SIGNALS):
        cells = {r: [float(x["gain_middle_model"]) for x in rows
                     if x["signal"] == signal and int(x["ratio_between_neighbours"]) == r] for r in RATIOS}
        frame(ax, -26, 17)
        band(ax, cells, BLUE, t["middle"])
        ax.set_title(t[signal])
    axes[0].set_ylabel(t["y"])
    fig.supxlabel(t["x"], color=MUTED, fontsize=8.5, y=-0.04)
    fig.savefig(HERE / f"fig1_middle_model{t['suffix']}.pdf")
    plt.close(fig)


def figure_rules_vs_middle(t):
    rows = read("exp8b_rules_vs_middle_model.csv")
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.9), sharey=True)
    for ax, signal in zip(axes, SIGNALS):
        def cells(column, coverage):
            return {r: [float(x[column]) for x in rows if x["signal"] == signal
                        and x["rule_coverage"] == coverage and int(x["ratio_between_neighbours"]) == r] for r in RATIOS}
        frame(ax, -26, 20)
        band(ax, cells("gain_middle_model", "0.3"), ORANGE, t["middle"], marker="s")
        band(ax, cells("gain_rule_stage", "0.1"), AQUA, t["rules10"], marker="^", linestyle=(0, (4, 2)))
        band(ax, cells("gain_rule_stage", "0.3"), BLUE, t["rules30"])
        ax.set_title(t[signal])
    axes[0].set_ylabel(t["y"])
    fig.supxlabel(t["x"], color=MUTED, fontsize=8.5, y=-0.04)
    handles, labels = axes[0].get_legend_handles_labels()
    order = [2, 1, 0]
    fig.legend([handles[i] for i in order], [labels[i] for i in order], loc="upper center", ncol=3, frameon=False,
               bbox_to_anchor=(0.5, 1.06), labelcolor=INK, handlelength=2.6)
    fig.savefig(HERE / f"fig2_rules_vs_middle{t['suffix']}.pdf")
    plt.close(fig)


if __name__ == "__main__":
    for language in TEXT.values():
        figure_middle_model(language)
        figure_rules_vs_middle(language)
    print("figures written to", HERE)
