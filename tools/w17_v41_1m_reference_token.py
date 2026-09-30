#!/usr/bin/env python3
"""W17 1M-context reference token: pick a seed whose top-1 logit margin is robust, pin it and its replication.

    python3 tools/w17_v41_1m_reference_token.py --seed S --primary DIR --replica DIR \
        --search DIR [DIR ...] [--output results/rtl/w17_v41_1m_reference_token.json]

The full-shape DeepSeek-V4.1-Flash headline token is at 1M context (position 1,048,575).  The token is computed by
the golden (tools/rtl_v41_fullshape_layer_campaign.py --steps golden --seed S, HDC_V41_ARITH=chunk8) on a
synthetic, golden-consistent KV/index state and token history, both drawn from the seed.  Only the seed varies
between candidates; the context construction is the tool's.

ROBUSTNESS.  A reference token is useful only when its top-1 logit margin (top1 - top2) is far above any
arithmetic perturbation, so that an implementation differing in one rounding could not flip it.  Threshold:
margin >= 1.0 logit.  The record also states the margin in units of the largest single BF16 rounding effect at
the final head: the golden rounds the final hidden vector (the input of the vocabulary head) to BF16 and
accumulates the logits in FP32, so (a) half a BF16 ulp of the top logit (the effect of one BF16 rounding of a
logit of that size), (b) the measured largest effect on the margin of one final-hidden BF16 rounding,
max_k |w_top1[k] - w_top2[k]| * ulp_bf16(xf[k]) / 2, and (c) half an FP32 ulp of the top logit (the precision
the logits are actually held in).

Every seed tried is listed with its margin; a candidate below threshold is kept, never overwritten.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from v41_fullshape_golden_collect import DEFAULT_SNAPSHOT, collect, sha256  # noqa: E402

CONTEXT = 1048576
THRESHOLD = 1.0
DEFAULT_SEED = 20260928
EXISTING = ROOT / "results/rtl/hdc_v41x_fullshape_golden.json"
OUT = ROOT / "results/rtl/w17_v41_1m_reference_token.json"
SOURCES = ["tools/rtl_v41_fullshape_layer_campaign.py", "tools/w17_v41_1m_reference_token.py",
           "tools/v41_fullshape_golden_collect.py", "tools/v41_fullshape_shard_compare.py",
           "tools/hdc_golden_v41.py", "tools/hdc_golden.py",
           "compiler/models/deepseek-v4.1-flash/inference_config.json"]


def half_ulp(x: float, mant_bits: int) -> float:
    """Half an ulp of |x| in a binary format with `mant_bits` stored mantissa bits (normal range)."""
    e = math.floor(math.log2(abs(x)))
    return 2.0 ** (e - mant_bits) / 2


def bf16_half_ulp_vec(x: np.ndarray) -> np.ndarray:
    a = np.abs(np.asarray(x, dtype=np.float64))
    e = np.floor(np.log2(np.where(a > 0, a, 2.0 ** -126)))
    return np.where(a > 0, 2.0 ** (e - 7) / 2, 2.0 ** -133)


def summary(d: Path) -> dict:
    return json.loads((d / f"golden_ctx{CONTEXT}_0-39.json").read_text())


def usage(d: Path) -> dict:
    """Wall and peak RSS of the run from /usr/bin/time -v (time.log) and the tool's own summary."""
    s = summary(d)
    out = {"model_build_s": s["model_build_s"], "state_build_s": s["state_build_s"],
           "layers_s": round(sum(r["golden_wall_s"] for r in s["layers"]), 1),
           "head_s": s["head"]["wall_s"], "tool_peak_rss_gb": s["peak_rss_gb"]}
    t = d / "time.log"
    if t.exists():
        txt = t.read_text()
        m = re.search(r"Elapsed \(wall clock\) time.*: (?:(\d+):)?(\d+):([\d.]+)", txt)
        if m:
            out["wall_s"] = round(int(m.group(1) or 0) * 3600 + int(m.group(2)) * 60 + float(m.group(3)), 1)
        m = re.search(r"Maximum resident set size \(kbytes\): (\d+)", txt)
        if m:
            out["peak_rss_gb"] = round(int(m.group(1)) / 1048576, 2)
    return out


def head_analysis(d: Path, top: list[int]) -> dict:
    sys.path.insert(0, str(ROOT / "tools"))
    import rtl_v41_fullshape_layer_campaign as C  # noqa: E402
    with np.load(d / f"ctx{CONTEXT}_head.npz", allow_pickle=True) as z:
        logits = np.asarray(z["logits"], dtype=np.float32)
        xf = z["xf"]
    if xf.dtype == object:
        raise ValueError("final hidden is Folded (nfold); this analysis assumes the unfused BF16 hidden")
    ck = C.Checkpoint()
    w = np.asarray(ck.rows("head.weight", top[:2]), dtype=np.float64)
    dw = np.abs(w[0] - w[1])
    eff = dw * bf16_half_ulp_vec(xf)
    k = int(np.argmax(eff))
    t1 = float(logits[top[0]])
    margin = float(logits[top[0]] - logits[top[1]])
    a, c = half_ulp(t1, 7), half_ulp(t1, 23)
    return {"head_weight_dtype": ck.meta("head.weight")[0]["dtype"], "final_hidden_precision": "BF16",
            "logit_precision": "FP32 (chunk8 csum of exact BF16 x BF16 products)",
            "top_logit": t1,
            "bf16_half_ulp_of_top_logit": a, "margin_over_bf16_half_ulp_of_top_logit": margin / a,
            "largest_single_final_hidden_bf16_rounding_effect_on_margin": float(eff[k]),
            "at_hidden_index": k, "margin_over_largest_single_hidden_rounding": margin / float(eff[k]),
            "fp32_half_ulp_of_top_logit": c, "margin_over_fp32_half_ulp_of_top_logit": margin / c}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--primary", type=Path, required=True, help="golden run dir of the chosen seed")
    ap.add_argument("--replica", type=Path, required=True, help="second, independent run dir of the chosen seed")
    ap.add_argument("--search", type=Path, nargs="*", default=[], help="every other seed run dir tried")
    ap.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    ap.add_argument("--output", type=Path, default=OUT)
    a = ap.parse_args()

    tried = []
    ex = json.loads(EXISTING.read_text())["contexts"][str(CONTEXT)]
    tried.append({"seed": DEFAULT_SEED, "next_token": ex["next_token"], "margin": ex["terminal_margin"],
                  "logits_sha256": ex["logits_sha256"], "token_history": ex["token_history"],
                  "evidence": str(EXISTING.relative_to(ROOT)), "meets_threshold": ex["terminal_margin"] >= THRESHOLD})
    for d in sorted(set(a.search) | {a.primary}):
        s = summary(d)
        tried.append({"seed": s["seed"], "next_token": s["head"]["next_token"], "margin": s["head"]["margin"],
                      "logits_sha256": s["head"]["logits_sha256"], "token_history": s["history"],
                      "top5": s["head"].get("top5"), "meets_threshold": s["head"]["margin"] >= THRESHOLD,
                      "usage": usage(d)})
    tried.sort(key=lambda r: r["seed"])

    p, r = summary(a.primary), summary(a.replica)
    if p["seed"] != a.seed or r["seed"] != a.seed:
        raise ValueError("run dirs are not of the chosen seed")
    base = collect(a.primary, [CONTEXT], a.snapshot, replica_dir=a.replica)
    c = base["contexts"][str(CONTEXT)]
    rep = c.get("independent_replication", {"status": "missing"})
    margin = p["head"]["margin"]
    top5 = p["head"]["top5"]
    hr = head_analysis(a.primary, [t for t, _ in top5])
    rec = {
        "schema": "opentallas.rtl.w17_v41_1m_reference_token.v1",
        "status": "reference_token_bit_exact_replicated" if rep["status"] == "bit_exact" and margin >= THRESHOLD
        else "reference_token_not_qualified",
        "claim_boundary": base["claim_boundary"] + " Selection by seed of the synthetic state/token history only.",
        "context": CONTEXT, "position": CONTEXT - 1, "arith": p["arith"], "fuse": p["fuse"],
        "seed": a.seed, "token_history": p["history"], "input_token": p["token"],
        "next_token": p["head"]["next_token"], "top5_logits": top5, "margin": margin,
        "threshold": {"margin_logits": THRESHOLD,
                      "rationale": "user decision 2026-09-30: the 1M headline reference token must be robust to any "
                                   "arithmetic perturbation. At this token a 1.0-logit margin is "
                                   f"{THRESHOLD / hr['bf16_half_ulp_of_top_logit']:.0f}x half a BF16 ulp of the top "
                                   f"logit and {THRESHOLD / hr['largest_single_final_hidden_bf16_rounding_effect_on_margin']:.0f}x "
                                   "the largest effect of one final-hidden BF16 rounding (head_robustness), so no "
                                   "single rounding difference in an implementation can flip the argmax. The earlier "
                                   "1M token (seed 20260928, margin 0.8699) and 200K token (margin 0.00998) are below it.",
                      "met": margin >= THRESHOLD},
        "head_robustness": hr,
        "logits_sha256": p["head"]["logits_sha256"],
        "state": {k: p["state"][k] for k in ("seed", "rows", "state_sha256", "window_rows_per_layer", "streams")},
        "layers": [{"layer": x["layer"], "input_sha256": x["input_sha256"], "output_sha256": x["output_sha256"],
                    "kind": y["kind"], "experts": y["experts"]}
                   for x, y in zip(c["layers"], p["layers"])],
        "replication": {**rep, "primary_dir": str(a.primary), "replica_dir": str(a.replica),
                        "checked": "every layer's input/output sha256, trace sha256s, experts, appended rows, "
                                   "carried context, next token and logits sha256 equal"},
        "usage": {"primary": usage(a.primary), "replica": usage(a.replica),
                  "note": "local host, 32 cores shared with other streams (load ~60); one token is one process"},
        "seeds_tried": tried,
        "shards": {"dir": str(a.replica), "schema": "ctx1048576_L{layer:02d}.json/.npz, ctx1048576_head.npz"},
        "checkpoint": base["checkpoint"],
        "source_commit": base["source_commit"],
        "source_sha256": {f: sha256(ROOT / f) for f in SOURCES},
        "command": f"HDC_V41_ARITH=chunk8 python3 tools/rtl_v41_fullshape_layer_campaign.py --steps golden "
                   f"--contexts {CONTEXT} --layers 0-39 --seed {a.seed} --scratch DIR",
    }
    a.output.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: rec[k] for k in ("status", "seed", "next_token", "margin")}))


if __name__ == "__main__":
    main()
