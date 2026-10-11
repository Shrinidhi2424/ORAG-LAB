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


BLUE, ORANGE, AQUA, VIOLET = "#2a78d6", "#eb6834", "#1baf7a", "#6250d6"
ORANGE_RAMP = ["#f4b394", "#eb6834", "#bd4a1f", "#7d3014"]  # S = 256 ... 16384, light -> dark
BLUE_RAMP = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281"]  # N = 1k ... all, light -> dark
NLAB = {"1000": "1k", "2000": "2k", "5000": "5k", "10000": "10k", "all": "21k"}
NORDER = ["1000", "2000", "5000", "10000", "all"]
NX = {"1000": 1000, "2000": 2000, "5000": 5000, "10000": 10000, "all": 20958}


def rows_of(path: Path) -> list[dict]:
    return list(csv.DictReader(path.open(encoding="utf-8")))


def save(fig, name: str, rows: list[dict]) -> Path:
    FIG.mkdir(parents=True, exist_ok=True)
    out = FIG / f"{name}.png"
    fig.savefig(out, dpi=300, facecolor=SURFACE)
    plt.close(fig)
    with (FIG / f"{name}.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
        w.writeheader()
        w.writerows(rows)
    return out


def fig_f3() -> Path:
    p3 = rows_of(current("phase3") / "retrieval_metrics.csv")
    main = rows_of(current("phase4") / "main_table.csv")
    fig, axes = plt.subplots(2, 5, figsize=(13, 5.6), dpi=300, sharex=True)
    fig.patch.set_facecolor(SURFACE)
    data = []
    for j, n in enumerate(NORDER):
        cl = next(r for r in p3 if (r["N"], r["M"], r["tie"], r["shots"]) == (n, "50", "classical", "classical"))
        ivf = next(r for r in main if r["N"] == n and r["arm"].startswith("IVF"))
        qs = sorted((r for r in p3 if (r["N"], r["M"], r["tie"]) == (n, "50", "classical") and r["shots"] not in ("classical", "inf")),
                    key=lambda r: int(r["shots"]))
        x = [int(r["shots"]) for r in qs]
        for i, m in enumerate(("Hit@3", "MRR@10")):
            ax = axes[i, j]
            style(ax)
            ax.axhspan(float(cl[m + "_lo"]), float(cl[m + "_hi"]), color=BLUE, alpha=0.12, linewidth=0)
            ax.axhline(float(cl[m]), color=BLUE, linewidth=1.8)
            ax.axhline(float(ivf[m]), color=AQUA, linewidth=1.8, linestyle=(0, (5, 2)))
            y = [float(r[m]) for r in qs]
            ax.fill_between(x, [float(r[m + "_lo"]) for r in qs], [float(r[m + "_hi"]) for r in qs], color=ORANGE, alpha=0.18, linewidth=0)
            ax.plot(x, y, color=ORANGE, linewidth=2, marker="o", markersize=5, markeredgecolor=SURFACE, markeredgewidth=1)
            ax.set_xscale("log", base=2)
            ax.set_xticks([64, 256, 1024, 4096, 16384])
            ax.set_xticklabels(["64", "256", "1k", "4k", "16k"])
            if i == 0:
                ax.set_title(f"N = {NLAB[n]}", color=INK, fontsize=10, loc="left")
            if j == 0:
                ax.set_ylabel(m, color=INK, fontsize=10)
            if i == 1:
                ax.set_xlabel("Shots S", color=INK, fontsize=9)
            for s_, v_ in zip(x, y):
                data.append({"N": n, "metric": m, "S": s_, "quantum_sim": v_, "classical": float(cl[m]), "ivf": float(ivf[m])})
    for i in range(2):
        lo = min(a.get_ylim()[0] for a in axes[i])
        hi = max(a.get_ylim()[1] for a in axes[i])
        for a in axes[i]:
            a.set_ylim(lo, hi)
    handles = [plt.Line2D([], [], color=BLUE, lw=1.8), plt.Line2D([], [], color=AQUA, lw=1.8, ls=(0, (5, 2))),
               plt.Line2D([], [], color=ORANGE, lw=2, marker="o", markersize=5)]
    fig.legend(handles, ["Classical Flat (exact), 95% CI band", "IVF (best nprobe)", "Quantum-sim (M=50), mean of 5 seeds, 95% CI band"],
               loc="lower center", ncol=3, frameon=False, fontsize=9, labelcolor=INK2)
    fig.suptitle("F3. Hit@3 and MRR@10 vs shots, per corpus size", color=INK, fontsize=12, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0.05, 1, 0.96))
    return save(fig, "F3_quality_vs_shots", data)


def fig_f4() -> Path:
    main = rows_of(current("phase4") / "main_table.csv")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), dpi=300)
    fig.patch.set_facecolor(SURFACE)
    data = []
    series = [("Flat", lambda r: r["arm"] == "Flat", BLUE, "s", "Flat (exact)")]
    series += [("IVF", lambda r: r["arm"].startswith("IVF"), AQUA, "^", "IVF (nprobe 16)")]
    series += [(f"S{s}", (lambda s_: lambda r: r["arm"] == "Quantum-sim" and r["S"] == str(s_))(s), c, "o", f"Quantum-sim S={s}")
               for s, c in zip((256, 1024, 4096, 16384), ORANGE_RAMP)]
    for ax, m in zip(axes, ("Hit@3", "MRR@10")):
        style(ax)
        for key, sel, color, mk, label in series:
            pts = [(NX[n], next(r for r in main if r["N"] == n and sel(r))) for n in NORDER]
            ax.plot([p[0] for p in pts], [float(p[1][m]) for p in pts], color=color, linewidth=2, marker=mk, markersize=6,
                    markeredgecolor=SURFACE, markeredgewidth=1)
            if key in ("S256", "S1024"):
                ax.annotate(label, (pts[-1][0], float(pts[-1][1][m])), xytext=(6, 0), textcoords="offset points", color=INK2, fontsize=7.5, va="center")
            for n_, r in pts:
                data.append({"series": label, "N": n_, "metric": m, "value": float(r[m]), "lo": float(r[m + "_lo"]), "hi": float(r[m + "_hi"])})
        ax.set_xscale("log")
        ax.set_xlim(900, 70000)
        ax.set_xticks([1000, 2000, 5000, 10000, 20958])
        ax.set_xticklabels(["1k", "2k", "5k", "10k", "21k"])
        ax.set_xlabel("Corpus size N (log scale)", color=INK, fontsize=10)
        ax.set_ylabel(m, color=INK, fontsize=10)
    handles = [plt.Line2D([], [], color=c, lw=2, marker=mk, markersize=6) for _, _, c, mk, _ in series]
    axes[1].legend(handles, [x[4] for x in series], frameon=False, fontsize=8, labelcolor=INK2, loc="upper right")
    fig.suptitle("F4. Retrieval quality vs corpus size (quantum-sim: M=50, mean of 5 seeds; 95% CIs in Table T3)", color=INK, fontsize=11, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    return save(fig, "F4_quality_vs_N", data)


def fig_f5() -> Path:
    lat = rows_of(current("phase4") / "latency_summary.csv")
    slopes = {r["series"]: r for r in rows_of(current("phase4") / "latency_slopes.csv")}
    fig, ax = plt.subplots(figsize=(7.4, 4.8), dpi=300)
    fig.patch.set_facecolor(SURFACE)
    style(ax)
    spec = [("Flat (exact), k=10", ("flat", "", ""), BLUE, "s", "Flat (exact)"),
            ("IVF best nprobe, k=10", ("ivf", "", ""), AQUA, "^", "IVF (nprobe 16)"),
            ("Quantum-sim shortlist M=50, S=1024", ("qsim", "50", "1024"), ORANGE, "o", "Quantum-sim shortlist (M=50, S=1024)"),
            ("Quantum-sim full scan, S=1024", ("qsim", "full", "1024"), VIOLET, "D", "Quantum-sim full scan (S=1024)")]
    data = []
    yoff = {"Flat (exact), k=10": -28, "Quantum-sim shortlist M=50, S=1024": 4, "Quantum-sim full scan, S=1024": 12}
    for key, (arm, m, s), color, mk, label in spec:
        rs = [next(r for r in lat if (r["arm"], r["N"], r["M"], r["S"]) == (arm, n, m, s)) for n in NORDER]
        x = [NX[n] for n in NORDER]
        ax.fill_between(x, [float(r["repeat_median_min_ms"]) for r in rs], [float(r["repeat_median_max_ms"]) for r in rs], color=color, alpha=0.15, linewidth=0)
        ax.plot(x, [float(r["median_ms"]) for r in rs], color=color, linewidth=2, marker=mk, markersize=6, markeredgecolor=SURFACE, markeredgewidth=1)
        sl = slopes[key]
        ax.annotate(f"{label}\nslope {float(sl['slope_b']):.2f} [{float(sl['slope_lo']):.2f}, {float(sl['slope_hi']):.2f}]", (x[-1], float(rs[-1]["median_ms"])),
                    xytext=(6, yoff.get(key, 0)), textcoords="offset points", color=INK2, fontsize=7.5, va="center")
        for n, r in zip(NORDER, rs):
            data.append({"series": label, "N": NX[n], "median_ms": float(r["median_ms"]), "p95_ms": float(r["p95_ms"]),
                         "repeat_median_min_ms": float(r["repeat_median_min_ms"]), "repeat_median_max_ms": float(r["repeat_median_max_ms"]),
                         "slope": float(sl["slope_b"]), "slope_lo": float(sl["slope_lo"]), "slope_hi": float(sl["slope_hi"])})
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(900, 400000)
    ax.set_xticks([1000, 2000, 5000, 10000, 20958])
    ax.set_xticklabels(["1k", "2k", "5k", "10k", "21k"])
    ax.set_xlabel("Corpus size N (log scale)", color=INK, fontsize=10)
    ax.set_ylabel("Retrieval latency per query, ms (log scale)", color=INK, fontsize=10)
    ax.set_title("F5. In-process retrieval latency vs N", color=INK, fontsize=11, loc="left", pad=22)
    ax.text(0, 1.02, "median; band = range of 5 repeat medians; slope = log-log exponent with 95% CI", transform=ax.transAxes, color=INK2, fontsize=8)
    fig.text(0.01, 0.01, "Emulated-estimator latency, 1 thread, embedding time excluded. HTTP latency (second layer) is added in Phase 6.",
             color=INK2, fontsize=7.5)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    return save(fig, "F5_latency_vs_N", data)


def fig_f6() -> Path:
    p3 = rows_of(current("phase3") / "retrieval_metrics.csv")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), dpi=300, sharex=True)
    fig.patch.set_facecolor(SURFACE)
    data = []
    for ax, m in zip(axes, ("Overlap@10", "RBO")):
        style(ax)
        for n, color in zip(NORDER, BLUE_RAMP):
            qs = sorted((r for r in p3 if (r["N"], r["M"], r["tie"]) == (n, "50", "classical") and r["shots"] not in ("classical", "inf")), key=lambda r: int(r["shots"]))
            x, y = [int(r["shots"]) for r in qs], [float(r[m]) for r in qs]
            ax.plot(x, y, color=color, linewidth=2, marker="o", markersize=5, markeredgecolor=SURFACE, markeredgewidth=1)
            ax.plot([], [], color=color, linewidth=2, marker="o", markersize=5, label=f"N = {NLAB[n]}")
            data += [{"N": n, "metric": m, "S": a, "value": b} for a, b in zip(x, y)]
        ax.set_xscale("log", base=2)
        ax.set_xticks([64, 256, 1024, 4096, 16384])
        ax.set_xticklabels(["64", "256", "1k", "4k", "16k"])
        ax.set_xlim(55, 40000)
        ax.set_xlabel("Shots S (log scale)", color=INK, fontsize=10)
        ax.set_ylabel(f"{m} vs classical exact top-10", color=INK, fontsize=10)
        ax.set_ylim(0.3, 1.0)
    axes[1].legend(frameon=False, fontsize=8, labelcolor=INK2, loc="lower right", title="Corpus size", title_fontsize=8)
    fig.suptitle("F6. Agreement with the classical ranking vs shots (M=50, mean of 5 seeds)", color=INK, fontsize=11, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    return save(fig, "F6_overlap_rbo_vs_shots", data)


FIGS = {"F2": fig_f2, "F3": fig_f3, "F4": fig_f4, "F5": fig_f5, "F6": fig_f6}

if __name__ == "__main__":
    for name in sys.argv[1:] or list(FIGS):
        print("wrote", FIGS[name]())
