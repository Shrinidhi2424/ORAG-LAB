"""Phase 5 block of FINDINGS.md, generated from results/phase5/<run_id>/ artifacts (used by report.py)."""
from __future__ import annotations

import csv
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from report import md_table, rel


def rd(p: Path) -> list[dict]:
    return list(csv.DictReader(p.open(encoding="utf-8")))


def ci(r: dict, m: str, lo: str, hi: str) -> str:
    return "-" if r.get(m) in ("", None) else f"{float(r[m]):.3f} [{float(r[lo]):.3f}, {float(r[hi]):.3f}]"


def label(r: dict) -> str:
    k = r["kind"]
    if k == "quantum":
        return f"Quantum-sim N={r['N']} S={r['S']} seed {r['seed']}"
    if k == "classical":
        return f"Classical Flat N={r['N']}"
    return {"closed_book": "Control: closed-book", "oracle": "Control: oracle (gold only)", "random": "Control: random context"}[k]


def phase5_block(run: Path) -> tuple[str, list[list]]:
    idx: list[list] = []
    bi = json.loads((run / "build_info.json").read_text(encoding="utf-8"))
    L = [f"Run `{run.name}` (manifests in `{rel(run / 'manifests')}`). Generator `{bi['model']}` digest `{bi['digest'][:12]}`, options `{json.dumps(bi['options'])}`; "
         f"{bi['questions']} questions (first 200 of the fixed 300, H4); k=3 contexts; prompt Appendix A.5 (closed-book prompt: see Deviations). "
         f"Run matrix: {bi['records']} records, {bi['unique_prompts_P0']} unique P0 prompts + {bi['unique_prompts_P1_extra']} extra for P1 "
         f"(`{rel(run / 'build_info.json')}`, all prompts in `{rel(run / 'prompts.jsonl')}`). Answers: `{rel(run / 'generations.jsonl')}`; judged: `{rel(run / 'judged.csv')}`.", ""]
    oc = run / "outcomes_by_arm.csv"
    if oc.exists():
        s = rd(oc)
        body = [[label(r), r["priority"], f"{float(r['gold_in_context_rate']):.3f}" if r["kind"] not in ("closed_book",) else "-",
                 ci(r, "correct_rate", "correct_rate_lo", "correct_rate_hi"), ci(r, "hallucination_rate", "hall_lo", "hall_hi"),
                 ci(r, "abstention_rate", "abstention_rate_lo", "abstention_rate_hi"), ci(r, "ungrounded_answer_rate", "ungr_lo", "ungr_hi"),
                 f"{float(r['median_gen_wall_s']):.2f}"] for r in s]
        L += [f"**T5b Outcome rates by arm (HHEM threshold 0.5)** (`{rel(oc)}`). Hallucination rate = (hallucinated + misread) / all questions; "
              "for closed-book = wrong non-abstained answers / all. Ungrounded-answer rate = non-abstained answers with HHEM < 0.5. 95% bootstrap CIs over questions; "
              "generation time is the median wall time of the original (uncached) call, CPU-only.", "",
              md_table(["Arm", "Pri.", "Gold in context", "Correct", "Hallucination rate", "Abstention", "Ungrounded-answer rate", "Gen. s (median)"], body), ""]
        tax = [[label(r), *(r[f"n_{o}"] for o in ("correct_grounded", "correct_ungrounded", "misread", "hallucinated", "abstained", "correct_closed_book", "wrong_closed_book"))] for r in s]
        L += ["**F8 data: five-way outcome taxonomy counts (threshold 0.5)**", "",
              md_table(["Arm", "Correct-grounded", "Correct-ungrounded", "Misread", "Hallucinated", "Abstained", "Closed-book correct", "Closed-book wrong"], tax), ""]
        cl = next((r for r in s if r["arm"] == "classical_Nall_k3"), None)
        if cl:
            idx.append(["P5-1", 5, f"Classical N=all: correct {float(cl['correct_rate']):.3f}, hallucination rate {float(cl['hallucination_rate']):.3f}", rel(oc)])
    jd = run / "judged.csv"
    if jd.exists():
        j = rd(jd)
        trunc = sum(r["done_reason"] == "length" for r in j)
        L += [f"Answers stopped by the 48-token limit (done_reason=length): {trunc} of {len(j)} (`{rel(jd)}`).", ""]
    rg = run / "regeneration_check.json"
    if rg.exists():
        g = json.loads(rg.read_text(encoding="utf-8"))
        n = g["n_sampled"]
        L += [f"**Integrity / reproducibility check** (`{rel(rg)}`, rows `{rel(run / 'regeneration_check.csv')}`; `scripts/check_regeneration.py`): {n} prompts sampled with seed {g['seed']} were re-generated "
              f"without the cache. Identical text: {g['identical_text']}/{n}; same correctness label: {g['same_correct_label']}/{n}; same abstention label: {g['same_abstain_label']}/{n}; "
              f"an immediate second call of the same request matched the first in {g['immediate_repeat_identical']}/{n} cases. Stored answers are therefore a faithful, "
              "internally consistent record (see also the audit of cache keys, completeness and context provenance below), but CPU generation is not bit-reproducible, so exact reruns rely on the cache.", ""]
        idx.append(["P5-6", 5, f"Regeneration check: text identical {g['identical_text']}/{n}, correctness label unchanged {g['same_correct_label']}/{n}", rel(rg)])
    cc = run / "controls_check.json"
    if cc.exists():
        c = json.loads(cc.read_text(encoding="utf-8"))
        L += [f"**Controls sanity (exit gate)** (`{rel(cc)}`): oracle correct {c['oracle_correct']:.3f}, closed-book {c['closed_book_correct']:.3f}, random {c['random_correct']:.3f}. "
              f"Oracle above closed-book (CI-separated): **{c['oracle_correct_gt_closed_book']}**; random not above closed-book: **{c['random_correct_le_closed_book']}** ({c['rule']}).", ""]
        idx.append(["P5-2", 5, f"Controls: oracle {c['oracle_correct']:.3f} vs closed-book {c['closed_book_correct']:.3f} vs random {c['random_correct']:.3f} correct", rel(cc)])
    pt = run / "paired_tests.csv"
    if pt.exists():
        t = rd(pt)
        body = [[r["family"], r["metric"], r["N"], r["S"], r["seed"], f"{float(r['classical_rate']):.3f}", f"{float(r['quantum_rate']):.3f}",
                 f"{float(r['diff']):+.3f} [{float(r['diff_lo']):+.3f}, {float(r['diff_hi']):+.3f}]", f"{r['quantum_only']}/{r['classical_only']}",
                 f"{float(r['p_mcnemar']):.4f}", f"{float(r['p_holm_T-c']):.4f}" if r.get("p_holm_T-c") else "-"] for r in t]
        L += [f"**T5c Paired comparisons vs classical at the same N (exact McNemar)** (`{rel(pt)}`). Pre-registered family T-c = hallucination indicator at N=all, "
              "S in {64, 256, 1024}, seed 0, Holm-corrected; all other rows are exploratory (uncorrected).", "",
              md_table(["Family", "Metric", "N", "S", "Seed", "Classical", "Quantum", "Diff [95% CI]", "Quantum-only / classical-only", "p McNemar", "p Holm (T-c)"], body), ""]
        tc = [r for r in t if r["family"] == "T-c"]
        idx.append(["P5-3", 5, "T-c hallucination McNemar (Holm) at N=all: " + ", ".join(f"S={r['S']} p={float(r['p_holm_T-c']):.3f}" for r in tc), rel(pt)])
    md = run / "mediation_by_gold_in_context.csv"
    if md.exists():
        m = rd(md)
        L += [f"**Mediation view (5.5): outcomes split by whether the gold paragraph reached the context** (`{rel(md)}`)", "",
              md_table(["Arm", "Gold in context", "n", "Correct", "Hallucinated/misread", "Abstained"],
                       [[r["arm"], r["gold_in_context"], r["n"], f"{float(r['correct_rate']):.3f}", f"{float(r['hallucinated_or_misread_rate']):.3f}", f"{float(r['abstention_rate']):.3f}"] for r in m]), ""]
    ts = run / "threshold_sweep.csv"
    if ts.exists():
        t = rd(ts)
        arms = list(dict.fromkeys(r["arm"] for r in t))
        body = []
        for a in arms:
            rs = {r["threshold"]: r for r in t if r["arm"] == a}
            if rs["0.5"]["kind"] == "closed_book":
                continue
            body.append([label(rs["0.5"]), *(f"{float(rs[x]['ungrounded_answer_rate']):.3f}" if rs[x].get("ungrounded_answer_rate") else "-" for x in ("0.3", "0.5", "0.7")),
                         *(f"{rs[x]['n_correct_grounded']}/{rs[x]['n_correct_ungrounded']}" for x in ("0.3", "0.5", "0.7"))])
        L += [f"**HHEM threshold sensitivity (D10b)** (`{rel(ts)}`): ungrounded-answer rate and correct-grounded / correct-ungrounded counts at thresholds 0.3 / 0.5 / 0.7. "
              "Hallucinated and misread counts do not depend on the threshold (they use correctness and gold-in-context only).", "",
              md_table(["Arm", "Ungrounded @0.3", "@0.5", "@0.7", "C-grounded/C-ungrounded @0.3", "@0.5", "@0.7"], body), ""]
    ji = run / "judge_info.json"
    if ji.exists():
        j = json.loads(ji.read_text(encoding="utf-8"))
        L += [f"Judge (`{rel(ji)}`): `{j['model']}` @ `{j['revision']}`; hypothesis template `{j['hypothesis_template']}`; premise: {j['premise']}; not scored: {j['not_scored']}; "
              f"peak RSS of the judging process {j['peak_rss_gb']:.2f} GB.", ""]
    au = run / "audit_template.csv"
    if au.exists():
        L += [f"**Audit sheet (5.6) [P1]**: 50 random P0 RAG answers with automatic labels for human labelling: `results/audit_template.csv` (copy: `{rel(au)}`). "
              "Agreement (Cohen's kappa) is computed in Phase 8 once labels are returned.", ""]
        idx.append(["P5-4", 5, "Audit sheet (50 rows) ready for human labels", "results/audit_template.csv"])
    gs = sorted(run.glob("generate_session_*.json"))
    if gs:
        g = [json.loads(p.read_text(encoding="utf-8")) for p in gs]
        L += [f"Generation sessions (`{rel(run)}/generate_session_*.json`): " + "; ".join(
            f"{x['new_generations']} new answers in {x['seconds'] / 3600:.2f} h, min free RAM {x['min_system_available_gb']:.2f} GB" for x in g) + ".", ""]
    xml = run / "pytest_junit.xml"
    if xml.exists():
        r = ET.parse(xml).getroot()
        ts_ = r if r.tag == "testsuite" else r.find("testsuite")
        tot, fail, err, skip = (int(ts_.get(x, 0)) for x in ("tests", "failures", "errors", "skipped"))
        L += [f"**pytest** (whole suite at Phase 5 exit): {tot} tests, {fail} failures, {err} errors, {skip} skipped (`{rel(xml)}`).", ""]
        idx.append(["P5-5", 5, f"pytest: {tot - fail - err - skip}/{tot} passed", rel(xml)])
    L += ["**Manuscript hook**: Section 8 (hallucination analysis), Table T5, figures F8-F9.", ""]
    return "\n".join(L), idx
