"""Figures (PNG, 300 dpi) + backing CSVs in results/figures/ (plan D16, Section 8).

Usage: python scripts/make_figures.py [F2 ...]
Palette: validated categorical slots 1-2 (blue, orange); theory/reference lines in neutral ink.
"""
from __future__ import annotations

import csv
import shutil
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FIG = ROOT / "results" / "figures"
SERIES = ["#2a78d6", "#eb6834"]
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"


def style(ax):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(INK2)
    ax.tick_params(colors=INK2, labelsize=9)
    ax.grid(True, which="major", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def current(phase: str) -> Path:
    return ROOT / "results" / phase / (ROOT / "results" / phase / ".current_run").read_text(encoding="utf-8").strip()


def fig_f2() -> Path:
    src = current("phase3") / "f2_error_vs_shots.csv"
    rows = list(csv.DictReader(src.open(encoding="utf-8")))
    FIG.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, FIG / "F2_error_vs_shots.csv")
    fig, ax = plt.subplots(figsize=(6.4, 4.2), dpi=300)
    fig.patch.set_facecolor(SURFACE)
    style(ax)
    tb = [r for r in rows if r["tier"] == "B"]
    ta = [r for r in rows if r["tier"] == "A"]
    s = [int(r["shots"]) for r in tb]
    ax.plot(s, [float(r["theory_rmse"]) for r in tb], color=INK, linewidth=1.2, linestyle=(0, (4, 3)),
            label="Theory  sqrt(mean(1 - c^4) / S)  (slope -1/2)", zorder=4)
    ax.plot(s, [float(r["rmse"]) for r in tb], color=SERIES[1], linewidth=2, marker="s", markersize=6,
            markeredgecolor=SURFACE, markeredgewidth=1.5, label=f"Tier B emulator ({tb[0]['n_pairs']} pairs x {tb[0]['repeats']} repeats)", zorder=2)
    ax.plot([int(r["shots"]) for r in ta], [float(r["rmse"]) for r in ta], color=SERIES[0], linewidth=0, marker="o", markersize=8,
            markeredgecolor=SURFACE, markeredgewidth=1.5, label=f"Tier A Aer circuit ({ta[0]['n_pairs']} pairs, 1 run each)", zorder=3)
    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.set_xlabel("Shots S (log scale)", color=INK, fontsize=10)
    ax.set_ylabel("RMSE of cos² estimate (log scale)", color=INK, fontsize=10)
    ax.set_title("F2. SWAP-test estimator error vs shots", color=INK, fontsize=11, loc="left")
    leg = ax.legend(frameon=False, fontsize=8, labelcolor=INK2, loc="upper right")
    del leg
    fig.tight_layout()
    out = FIG / "F2_error_vs_shots.png"
    fig.savefig(out, dpi=300, facecolor=SURFACE)
    plt.close(fig)
    return out


FIGS = {"F2": fig_f2}

if __name__ == "__main__":
    for name in sys.argv[1:] or list(FIGS):
        print("wrote", FIGS[name]())
