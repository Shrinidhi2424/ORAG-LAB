"""Figures (PNG, 300 dpi) + backing CSVs in results/figures/ (plan D16, Section 8).

Usage: python scripts/make_figures.py [F2 ...]
Palette: validated categorical slots 1-2 (blue, orange); theory/reference lines in neutral ink.
"""
from __future__ import annotations

import csv
import json
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


OUTCOME_COLORS = {"correct_grounded": BLUE, "correct_ungrounded": ORANGE, "misread": AQUA, "hallucinated": "#eda100", "abstained": "#e87ba4"}
OUTCOME_LABELS = {"correct_grounded": "Correct-grounded", "correct_ungrounded": "Correct-ungrounded", "misread": "Misread (gold in context)",
                  "hallucinated": "Hallucinated (gold not in context)", "abstained": "Abstained"}


def arm_label(r: dict) -> str:
    k = r["kind"]
    if k == "quantum":
        return f"Quantum-sim N={NLAB.get(r['N'], r['N'])} S={r['S']}" + (f" (seed {r['seed']})" if r["seed"] != "0" else "")
    if k == "classical":
        return f"Classical N={NLAB.get(r['N'], r['N'])}"
    return {"closed_book": "Closed-book*", "oracle": "Oracle (gold only)", "random": "Random context"}[k]


def p5_rows() -> list[dict]:
    return rows_of(current("phase5") / "outcomes_by_arm.csv")


def fig_f8() -> Path:
    rows = p5_rows()
    fig, ax = plt.subplots(figsize=(9, 0.42 * len(rows) + 1.8), dpi=300)
    fig.patch.set_facecolor(SURFACE)
    style(ax)
    ax.grid(False, axis="y")
    data = []
    for i, r in enumerate(rows):
        n = int(r["n"])
        counts = {o: int(r[f"n_{o}"]) for o in OUTCOME_COLORS}
        if r["kind"] == "closed_book":  # no context: correct answers are ungrounded by definition, wrong ones are hallucinations
            counts["correct_ungrounded"] += int(r["n_correct_closed_book"])
            counts["hallucinated"] += int(r["n_wrong_closed_book"])
        left = 0.0
        for o, c in counts.items():
            w = c / n
            ax.barh(i, w, left=left, color=OUTCOME_COLORS[o], edgecolor=SURFACE, linewidth=1.5, height=0.72)
            if w >= 0.07:
                ax.text(left + w / 2, i, f"{100 * w:.0f}", ha="center", va="center", fontsize=7, color=SURFACE if o in ("correct_grounded",) else INK)
            left += w
            data.append({"arm": r["arm"], "label": arm_label(r), "outcome": o, "count": c, "share": w})
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([arm_label(r) for r in rows], fontsize=8, color=INK)
    ax.invert_yaxis()
    ax.set_xlim(0, 1)
    ax.set_xlabel("Share of 200 questions (labels in %)", color=INK, fontsize=9)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in OUTCOME_COLORS.values()]
    ax.legend(handles, list(OUTCOME_LABELS.values()), ncol=3, frameon=False, fontsize=7.5, labelcolor=INK2, loc="upper center", bbox_to_anchor=(0.45, -0.12))
    ax.set_title("F8. Five-way outcome taxonomy per arm (HHEM threshold 0.5)", color=INK, fontsize=11, loc="left")
    fig.text(0.01, 0.005, "* Closed-book has no context: correct answers count as correct-ungrounded, wrong answers as hallucinated.", color=INK2, fontsize=7)
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    return save(fig, "F8_outcome_taxonomy", data)


def fig_f9() -> Path:
    med = rows_of(current("phase5") / "mediation_by_gold_in_context.csv")
    lab = {r["arm"]: arm_label(r) for r in p5_rows()}
    arms = [a for a in dict.fromkeys(r["arm"] for r in med) if a in lab and a not in ("oracle",)]
    fig, ax = plt.subplots(figsize=(9.5, 4.6), dpi=300)
    fig.patch.set_facecolor(SURFACE)
    style(ax)
    ax.grid(False, axis="x")
    data, w = [], 0.38
    for j, g in enumerate(("True", "False")):
        xs, ys = [], []
        for i, a in enumerate(arms):
            r = next((x for x in med if x["arm"] == a and x["gold_in_context"] == g), None)
            if r:
                xs.append(i + (j - 0.5) * w)
                ys.append(float(r["hallucinated_or_misread_rate"]))
                data.append({"arm": a, "label": lab[a], "gold_in_context": g, "n": int(r["n"]), "hallucinated_or_misread_rate": ys[-1]})
        ax.bar(xs, ys, width=w - 0.04, color=BLUE if g == "True" else ORANGE, label="Gold paragraph in context" if g == "True" else "Gold paragraph NOT in context")
    ax.set_xticks(range(len(arms)))
    ax.set_xticklabels([lab[a] for a in arms], rotation=35, ha="right", fontsize=7.5, color=INK)
    ax.set_ylabel("Hallucinated or misread (share)", color=INK, fontsize=9)
    ax.set_ylim(0, 1)
    ax.legend(frameon=False, fontsize=8, labelcolor=INK2, loc="lower right", bbox_to_anchor=(1.0, 1.0), ncol=2)
    ax.set_title("F9. Confident wrong answers, split by whether retrieval\ndelivered the gold paragraph", color=INK, fontsize=10.5, loc="left")
    fig.tight_layout()
    return save(fig, "F9_hallucination_by_gold_in_context", data)


PROFILE_COLORS = {"small": BLUE, "medium": ORANGE, "large": AQUA}
PROFILE_LABELS = {"small": "small (1 CPU, 1.5 GB)", "medium": "medium (2 CPU, 2 GB)", "large": "large (4 CPU, 3 GB)"}


def fig_f5b() -> Path:
    p6 = current("phase6")
    lat = rows_of(p6 / "latency_summary.csv")
    p2, p4 = current("phase2"), current("phase4")
    embed = float(json.loads((p2 / "query_embed_summary.json").read_text(encoding="utf-8"))["median_ms"])
    l4 = rows_of(p4 / "latency_summary.csv")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), dpi=300, sharey=True)
    fig.patch.set_facecolor(SURFACE)
    data = []
    ns = ["1000", "5000", "all"]
    x = [NX[n] for n in ns]
    for ax, arm in zip(axes, ("classical", "quantum")):
        style(ax)
        base = []
        for n in ns:
            r = next(r for r in l4 if (r["arm"], r["N"]) == ("flat", n)) if arm == "classical" else next(r for r in l4 if (r["arm"], r["N"], r["M"], r["S"]) == ("qsim", n, "50", "1024"))
            base.append(embed + float(r["median_ms"]))
        ax.plot(x, base, color=INK, linewidth=1.8, linestyle=(0, (4, 3)), marker="o", markersize=5, markeredgecolor=SURFACE)
        ax.annotate("in-process (embed + retrieve)", (x[-1], base[-1]), xytext=(-6, -14), textcoords="offset points", ha="right", color=INK2, fontsize=7.5)
        for n, b in zip(ns, base):
            data.append({"arm": arm, "series": "in-process", "N": NX[n], "median_ms": b})
        for prof, color in PROFILE_COLORS.items():
            rs = [next((r for r in lat if (r["profile"], r["arm"], r["N"]) == (prof, arm, n)), None) for n in ns]
            if any(r is None for r in rs):
                continue
            ax.fill_between(x, [float(r["repeat_median_min_ms"]) for r in rs], [float(r["repeat_median_max_ms"]) for r in rs], color=color, alpha=0.12, linewidth=0)
            ax.plot(x, [float(r["e2e_median_ms"]) for r in rs], color=color, linewidth=2, marker="s", markersize=5, markeredgecolor=SURFACE, markeredgewidth=1)
            ax.annotate(prof, (x[-1], float(rs[-1]["e2e_median_ms"])), xytext=(6, 0), textcoords="offset points", color=INK2, fontsize=8, va="center")
            for n, r in zip(ns, rs):
                data.append({"arm": arm, "series": f"HTTP {prof}", "N": NX[n], "median_ms": float(r["e2e_median_ms"]), "p95_ms": float(r["e2e_p95_ms"]),
                             "repeat_median_min_ms": float(r["repeat_median_min_ms"]), "repeat_median_max_ms": float(r["repeat_median_max_ms"])})
        ax.set_xscale("log")
        ax.set_xlim(900, 45000)
        ax.set_xticks(x)
        ax.set_xticklabels(["1k", "5k", "21k"])
        ax.set_xlabel("Corpus size N (log scale)", color=INK, fontsize=10)
        ax.set_title("Classical Flat" if arm == "classical" else "Quantum-sim (M=50, S=1024, emulated)", color=INK, fontsize=10, loc="left")
    axes[0].set_ylabel("Median latency per request, ms", color=INK, fontsize=10)
    handles = [plt.Line2D([], [], color=c, lw=2, marker="s", markersize=5) for c in PROFILE_COLORS.values()] + [plt.Line2D([], [], color=INK, lw=1.8, ls=(0, (4, 3)), marker="o", markersize=5)]
    fig.legend(handles, [PROFILE_LABELS[p] for p in PROFILE_COLORS] + ["in-process (Phase 2 embed + Phase 4 retrieve)"], loc="lower center", ncol=4, frameon=False, fontsize=8, labelcolor=INK2)
    fig.suptitle("F5b. HTTP end-to-end latency (retrieval-only, through the services) vs in-process; band = range of 5 repeat medians", color=INK, fontsize=10.5, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0.07, 1, 0.95))
    return save(fig, "F5b_http_vs_inprocess", data)


def fig_f10() -> Path:
    rows = rows_of(current("phase6") / "concurrency.csv")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), dpi=300)
    fig.patch.set_facecolor(SURFACE)
    data = []
    for ax, (metric, ylab) in zip(axes, (("throughput_rps", "Throughput, requests / s"), ("p95_ms", "p95 latency, ms"))):
        style(ax)
        for prof, color in PROFILE_COLORS.items():
            for arm, ls, mk in (("classical", "-", "o"), ("quantum", (0, (4, 2)), "^")):
                pts = []
                for cl in ("1", "4", "16"):
                    sel = sorted(float(r[metric]) for r in rows if (r["profile"], r["arm"], r["clients"]) == (prof, arm, cl))
                    if sel:
                        pts.append((int(cl), sel[len(sel) // 2]))
                if not pts:
                    continue
                ax.plot([p[0] for p in pts], [p[1] for p in pts], color=color, linestyle=ls, marker=mk, markersize=6, linewidth=2, markeredgecolor=SURFACE, markeredgewidth=1)
                data += [{"profile": prof, "arm": arm, "clients": c, metric: v} for c, v in pts]
        ax.set_xscale("log", base=2)
        ax.set_xticks([1, 4, 16])
        ax.set_xticklabels(["1", "4", "16"])
        ax.set_xlabel("Concurrent clients", color=INK, fontsize=10)
        ax.set_ylabel(ylab, color=INK, fontsize=10)
        if metric == "p95_ms":
            ax.set_yscale("log")
    handles = [plt.Line2D([], [], color=c, lw=2) for c in PROFILE_COLORS.values()] + [plt.Line2D([], [], color=INK2, lw=2, marker="o", markersize=6), plt.Line2D([], [], color=INK2, lw=2, ls=(0, (4, 2)), marker="^", markersize=6)]
    fig.legend(handles, [PROFILE_LABELS[p] for p in PROFILE_COLORS] + ["classical Flat", "quantum-sim (emulated)"], loc="lower center", ncol=5, frameon=False, fontsize=8, labelcolor=INK2)
    fig.suptitle("F10. Concurrency: throughput and p95 latency vs clients (N=all, retrieval-only; median of 3 runs)", color=INK, fontsize=10.5, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0.07, 1, 0.95))
    return save(fig, "F10_concurrency", data)


def fig_f1() -> Path:
    """System architecture: services, ports, resource profiles, volumes (static; edges also written to the CSV)."""
    from matplotlib.patches import FancyBboxPatch

    fig, ax = plt.subplots(figsize=(11.5, 6.2), dpi=300)
    fig.patch.set_facecolor(SURFACE)
    ax.set_xlim(0, 118)
    ax.set_ylim(0, 62)
    ax.axis("off")
    nodes = {}

    def box(key, x, y, w, h, title, sub, fill, edge, dashed=False):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3,rounding_size=1.0", linewidth=1.6, edgecolor=edge, facecolor=fill, linestyle="--" if dashed else "-"))
        ax.text(x + w / 2, y + h - 2.4, title, ha="center", va="center", fontsize=8.8, color=INK, fontweight="bold")
        ax.text(x + w / 2, y + (h - 4.0) / 2, sub, ha="center", va="center", fontsize=7.1, color=INK2, linespacing=1.35)
        nodes[key] = (x, y, w, h)

    def arrow(a, b, label="", lx=0.35, dy=0.5):
        xa, ya, wa, ha = nodes[a]
        xb, yb, wb, hb = nodes[b]
        p0, p1 = (xa + wa, ya + ha / 2), (xb, yb + hb / 2)
        ax.annotate("", xy=p1, xytext=p0, arrowprops=dict(arrowstyle="-|>", color=INK2, lw=1.4))
        if label:
            ax.text(p0[0] + (p1[0] - p0[0]) * lx, p0[1] + (p1[1] - p0[1]) * lx + dy, label, ha="center", va="bottom", fontsize=6.8, color=INK2, backgroundcolor=SURFACE)

    ax.add_patch(FancyBboxPatch((20, 1.5), 72, 52, boxstyle="round,pad=0.3,rounding_size=1.5", linewidth=1.4, edgecolor=GRID, facecolor="#f4f4f1", linestyle=":"))
    ax.text(21.5, 51.2, "Docker Desktop WSL2 VM (cap 3 GB, 4 CPUs, 2 GB swap), compose project qraglab", fontsize=7.5, color=INK2, va="center")
    box("client", 1, 24, 15, 13, "Client", "load generator\n(in-network\ncontainer or\nhost port)", SURFACE, INK2)
    box("orch", 24, 24, 21, 13, "orchestrator :8000", "POST /rag\nPOST /rag/retrieval-only\n0.5 CPU, 384 MB", "#e9eef7", BLUE)
    box("emb", 58, 40, 31, 9.5, "embedder :8001", "MiniLM-L6-v2 weights baked in\nprofile CPU / RAM", "#e9eef7", BLUE)
    box("rc", 58, 28, 31, 9.5, "retriever-classical :8002", "FAISS IndexFlatIP, 5 ladder rungs\nprofile CPU / RAM", "#e9eef7", BLUE)
    box("rq", 58, 16, 31, 9.5, "retriever-quantum-sim :8003", "shortlist M + SWAP-test emulator\n(emulated; profile CPU / RAM)", "#fbe9e1", ORANGE)
    box("gen", 58, 4, 31, 9.5, "generator-gateway :8004", "cache-first Ollama client\n0.5 CPU, 384 MB", "#e9eef7", BLUE)
    box("ollama", 97, 4, 20, 9.5, "Ollama (Windows host)", "qwen2.5:1.5b-instruct, CPU\nnot a container; idle\nduring latency tests", SURFACE, INK2, dashed=True)
    arrow("client", "orch", "HTTP/JSON", lx=0.5, dy=0.7)
    for k, lab in (("emb", "1 embed"), ("rc", "2a classical"), ("rq", "2b quantum-sim"), ("gen", "3 generate (full mode)")):
        arrow("orch", k, lab, lx=0.62, dy=0.4)
    arrow("gen", "ollama", "", lx=0.5, dy=0.7)
    ax.text(93.0, 5.2, "host.docker.\ninternal:11434", ha="center", va="top", fontsize=6.3, color=INK2, linespacing=1.2)
    ax.text(21.5, 2.6, "volumes: ./data read-only (embeddings, ladder, paragraphs);  ./cache for the gateway", fontsize=6.9, color=INK2, va="center")
    ax.text(0.5, 59.5, "F1. Cloud-native architecture, emulated on one laptop", fontsize=11, color=INK, va="center", fontweight="bold")
    ax.text(0.5, 56.8, "profiles for the three compute services: small 1 CPU / 1.5 GB, medium 2 CPU / 2 GB, large 4 CPU / 3 GB", fontsize=8, color=INK2, va="center")
    rows = [{"from": a, "to": b, "label": lab} for a, b, lab in (("client", "orchestrator", "HTTP/JSON"), ("orchestrator", "embedder", "embed"), ("orchestrator", "retriever-classical", "retrieve/classical"),
                                                          ("orchestrator", "retriever-quantum-sim", "retrieve/quantum"), ("orchestrator", "generator-gateway", "generate (full mode)"), ("generator-gateway", "ollama-host", "host.docker.internal:11434"))]
    return save(fig, "F1_architecture", rows)


FIGS = {"F1": fig_f1, "F2": fig_f2, "F3": fig_f3, "F4": fig_f4, "F5": fig_f5, "F5b": fig_f5b, "F6": fig_f6, "F8": fig_f8, "F9": fig_f9, "F10": fig_f10}

if __name__ == "__main__":
    for name in sys.argv[1:] or list(FIGS):
        print("wrote", FIGS[name]())
