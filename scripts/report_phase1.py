"""Phase 1 block of FINDINGS.md, generated from results/phase1/<run_id>/ artifacts (used by report.py)."""
from __future__ import annotations

import csv
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from report import md_table, rel


def pct(x) -> str:
    return f"{100 * float(x):.1f}%"


def phase1_block(run: Path) -> tuple[str, list[list]]:
    idx: list[list] = []
    L = [f"Run `{run.name}` - manifest: `{rel(run / 'run_manifest.json')}`; config: seeds 42, eval n=300, "
         "ladder 1k/2k/5k/10k/all, ground-truth k=50.", ""]

    cs = run / "corpus_stats.json"
    if cs.exists():
        c = json.loads(cs.read_text(encoding="utf-8"))
        w = c["words_per_paragraph"]
        L += [f"**T1a corpus / eval set** (`{rel(cs)}`)", "", md_table(["Quantity", "Value"], [
            ["Raw paragraphs train / dev", f"{c['raw']['train']} / {c['raw']['dev']}"],
            ["Exact duplicates dropped", c["duplicates_dropped"]],
            ["Unique paragraphs", c["unique_paragraphs"]],
            ["Dev questions with gold paragraph in corpus", c["candidate_questions"]],
            ["Eval questions (seed 42)", c["n_eval"]],
            ["Distinct gold paragraphs among eval questions", c["distinct_gold_paragraphs"]],
            ["Words per paragraph mean / median / p95 / max", f"{w['mean']:.1f} / {w['median']:.0f} / {w['p95']:.0f} / {w['max']}"],
            ["Ladder nested", c["ladder_nested"]],
            ["Gold in every rung", c["gold_in_every_rung"]],
        ]), "", "**T1b corpus ladder** (`data/ladder_N.json`)", "",
            md_table(["Rung", "Paragraphs", "Gold included", "Distractors"],
                     [[k, v, c["n_gold"], v - c["n_gold"]] for k, v in c["ladder_sizes"].items()]), ""]
        idx.append(["P1-1", 1, f"{c['unique_paragraphs']} unique paragraphs; {c['n_eval']} eval questions on "
                    f"{c['distinct_gold_paragraphs']} gold paragraphs; ladder nested, gold in every rung", rel(cs)])

    ei = run / "embed_info.json"
    if ei.exists():
        e = json.loads(ei.read_text(encoding="utf-8"))
        t = e["paragraph_tokens"]
        L += [f"**Embedding** (`{rel(ei)}`)", "", md_table(["Item", "Value"], [
            ["Model / revision", f"`{e['model']}` @ `{e['revision']}`"],
            ["Device / torch threads / batch", f"{e['device']} / {e['torch_threads']} / {e['batch_size']}"],
            ["Dim / padded dim", f"{e['dim']} / {e['padded_dim']}"],
            ["Paragraph embedding time", f"{e['paragraph_embed_s']:.1f} s ({e['paragraphs_per_s']:.1f} paragraphs/s)"],
            ["Query embedding time", f"{e['query_embed_s']:.2f} s ({e['queries_per_s']:.1f} queries/s)"],
            ["Process RSS after embedding", f"{e['process_rss_gb_after_embed']:.2f} GB"],
            ["max_seq_length (tokens)", e["max_seq_length"]],
            ["Paragraph tokens mean / median / max", f"{t['mean']:.1f} / {t['median']:.0f} / {t['max']}"],
            ["Paragraphs truncated by max_seq_length", f"{e['paragraphs_truncated']} ({pct(e['paragraphs_truncated_frac'])})"],
        ]), ""]
        idx.append(["P1-2", 1, f"Embedded {e['n_paragraphs']} paragraphs in {e['paragraph_embed_s']:.0f} s "
                    f"({e['paragraphs_per_s']:.1f}/s)", rel(ei)])

    ce = run / "ceiling_by_N.csv"
    if ce.exists():
        rows = list(csv.DictReader(ce.open(encoding="utf-8")))
        cols = ("Hit@1", "Hit@3", "Hit@5", "Hit@10", "P@1", "P@3", "P@5", "P@10", "MRR@10", "nDCG@10")
        L += [f"**Classical ceiling: exact cosine vs gold paragraph, 300 queries** (`{rel(ce)}`; top-50 ground truth in "
              f"`{rel(run)}/ground_truth_N*.npz`)", "",
              md_table(["N", "Corpus size", *cols, "Median gold rank", "Brute-force s (300 q)"],
                       [[r["N"], r["corpus_size"], *(f"{float(r[k]):.3f}" for k in cols), r["median_gold_rank"], r["brute_force_s"]]
                        for r in rows]), "",
              "Note: P@k is upper-bounded by 1/k with a single gold paragraph (A.4).", ""]
        lo, hi = rows[-1], rows[0]
        idx.append(["P1-3", 1, f"Exact-cosine ceiling Hit@1 = {pct(hi['Hit@1'])} (N={hi['N']}) to {pct(lo['Hit@1'])} (N={lo['N']})", rel(ce)])

    sa = run / "sanity.json"
    if sa.exists():
        s = json.loads(sa.read_text(encoding="utf-8"))
        g = s["gold_cosine"]
        L += [f"**Data sanity** (`{rel(sa)}`, `{rel(run / 'gold_cosine.csv')}`)", "", md_table(["Check", "Result"], [
            ["NaNs in embeddings", s["has_nan"]],
            ["Paragraph norm min / max", f"{s['paragraph_norm']['min']:.6f} / {s['paragraph_norm']['max']:.6f}"],
            ["Query norm min / max", f"{s['query_norm']['min']:.6f} / {s['query_norm']['max']:.6f}"],
            ["512-d padded norm max abs deviation from 1", f"{s['padded_norm_max_abs_dev']:.2e}"],
            ["Gold cosine change from padding (max abs)", f"{s['padding_cosine_max_abs_diff']:.2e}"],
            ["Padding columns all zero", s["padding_columns_all_zero"]],
            ["Question-gold cosine min / p5 / median / p95 / max", " / ".join(f"{g[k]:.3f}" for k in ("min", "p5", "median", "p95", "max"))],
            ["Negative cosines in exact top-10 (per rung)", ", ".join(f"{n}: {v['negative_cosine_in_top10']}" for n, v in s["top10_negative_cosine"].items())],
            ["Min top-10 cosine (per rung)", ", ".join(f"{n}: {v['min_top10_score']:.3f}" for n, v in s["top10_negative_cosine"].items())],
        ]), ""]
        idx.append(["P1-4", 1, f"Sanity: norms in [{s['paragraph_norm']['min']:.4f}, {s['paragraph_norm']['max']:.4f}], "
                    f"NaN={s['has_nan']}, gold-cosine median {g['median']:.3f}", rel(sa)])

    cc = run / "contamination_check.json"
    if cc.exists():
        k = json.loads(cc.read_text(encoding="utf-8"))
        L += [f"**Embedder contamination check (D7)** - model card saved at `{rel(run / 'model_card.md')}` "
              f"(revision `{k['revision']}`, {k['card_lines']} lines). Card mentions SQuAD: **{k['mentions_squad']}**. "
              "Lines mentioning squad/wikipedia/wiki:", ""]
        L += [f"- line {h['line']}: `{h['text'][:200]}`" for h in k["squad_or_wiki_lines"]] or ["- (none)"]
        L += ["", "Interpretation: see Section 5. A model card cannot prove absence of overlap.", ""]
        idx.append(["P1-5", 1, f"Model card mentions SQuAD: {k['mentions_squad']} ({len(k['squad_or_wiki_lines'])} squad/wiki lines)", rel(cc)])

    xml = run / "pytest_junit.xml"
    if xml.exists():
        r = ET.parse(xml).getroot()
        ts = r if r.tag == "testsuite" else r.find("testsuite")
        tot, fail, err, skip = (int(ts.get(x, 0)) for x in ("tests", "failures", "errors", "skipped"))
        L += [f"**pytest** (whole suite at Phase 1 exit): {tot} tests, {fail} failures, {err} errors, {skip} skipped (`{rel(xml)}`).", ""]
        idx.append(["P1-6", 1, f"pytest: {tot - fail - err - skip}/{tot} passed", rel(xml)])

    L += ["**Manuscript hook**: Section 5 (corpus, ladder, embeddings), Table T1; contamination discussion in Section 11.", ""]
    return "\n".join(L), idx
