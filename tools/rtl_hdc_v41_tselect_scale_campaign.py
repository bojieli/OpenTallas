#!/usr/bin/env python3
"""Shipped-scale campaign for the V4.1 index top-512 on ot_hdc_tselect.

The indexer at shipped scale scores context/ratio compressed keys per token
(32 heads x 128, ReLU, head weights, head sum -> one BF16 score per key) and
keeps the top 512 in position order (tools/hdc_golden_v41.py `indexer`:
`sorted(topk_lowest_index(s, min(512, n)))`).  This campaign re-parameterises
the existing unit (rtl/hdc/v41/ot_hdc_tselect.sv, unchanged) for the full
1,048,576-token context -- W = 64 lanes, 20-bit positions, 2^14 lines -- and
checks it bit-exactly against the golden:

* random segments (many ties, +/-0, +/-inf, subnormals, raw BF16) at the
  shipped width;
* the real reduced DeepSeek-V4.1 index scores (every indexer, candidate-masked
  -inf included) and the same scores scaled up to shipped context lengths;
* single segments at 8K, 200K and 1M context for a ratio-1 layer (n = context)
  and a ratio-2 layer (n = context / 2), and a reuse layer whose scores are
  -inf outside 2,048 candidate blocks;
* the two-level form (G contiguous ranges, local top-512 each, RTL merge of the
  concatenation) the multi-die critical path uses.

Latency is measured in the RTL (clock edges from the last accepted beat to the
out_last beat) and recorded per context; tools/decode_critical_path.py prices
the index top-k from these rows.  Writes
results/rtl/hdc_v41_tselect_scale_campaign.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pickle
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_hdc_v41_select_campaign as SC  # noqa: E402
import rtl_hdc_v41_tselect_campaign as TC  # noqa: E402

OUT = ROOT / "results/rtl/hdc_v41_tselect_scale_campaign.json"
SHIPPED = json.loads((ROOT / "configs/models/candidates/deepseek-v4.1-flash.json").read_text())
OPC = SHIPPED["metadata"]["operator_config"]
MAX_CONTEXT = SHIPPED["max_context_tokens"]
TOPK = OPC["index_topk"]
W, IW, AW = 64, 20, 14                       # 2^14 lines x 64 lanes = 1,048,576 positions
CONTEXTS = (8192, 200000, MAX_CONTEXT)
CAND_POSITIONS = OPC["candidate_topk_blocks"] * OPC["candidate_block_size"]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scaled(rng, arrays, n):
    out, have = [], 0
    while have < n:
        a = arrays[int(rng.integers(len(arrays)))]
        out.append(a)
        have += len(a)
    return np.concatenate(out)[:n]


def candidate_masked(rng, arrays, n):
    """A reuse layer: scores outside 2,048 candidate blocks of 8 are -inf (the newest block always kept)."""
    s = scaled(rng, arrays, n)
    nb = -(-n // 8)
    keep = np.zeros(nb, bool)
    keep[rng.choice(nb, min(nb, OPC["candidate_topk_blocks"]) , replace=False)] = True
    keep[nb - 1] = True
    return np.where(np.repeat(keep, 8)[:n], s, -np.inf)


def run(quick=False, cache=None, nrand=80, htrials=6) -> dict:
    if cache and Path(cache).exists():
        sets, checks, meta = pickle.loads(Path(cache).read_bytes())
    else:
        sets, checks, meta = SC.real_sets(SC.REAL_POSITIONS)
    arrays = [np.asarray(v, np.float64) for v, _, _ in sets["index"]]
    finite = [a[np.isfinite(a)] for a in arrays if np.isfinite(a).any()]
    rng = np.random.default_rng(12345)
    lint = __import__("subprocess").run(
        ["verilator", "--lint-only", *TC.LINT_FLAGS, f"-GW={W}", f"-GIW={IW}", f"-GK={TOPK}", f"-GAW={AW}",
         "--top-module", "ot_hdc_tselect", str(TC.RTL)], capture_output=True, text=True)
    ok = lint.returncode == 0
    long_rows = []
    with tempfile.TemporaryDirectory() as scratch:
        s = Path(scratch)
        binary = TC.build(s / "obj", TC.RTL, W, IW, TOPK, AW)
        # -- functional: random + real + scaled-real segments -----------------------------------------
        segs = [] if quick else [TC.seg_record(rng, *TC.random_segment(rng, W, IW, TOPK, AW), TOPK, W)
                                 for _ in range(nrand)]
        for vals, labels, _ in sets["index"]:
            segs.append(TC.seg_record(rng, vals, np.asarray(labels), TOPK, TOPK, W, dense=True))
        for _ in range(4 if quick else 24):
            n = int(rng.integers(TOPK, 1 << 17))
            segs.append(TC.seg_record(rng, scaled(rng, finite, n), np.arange(n), TOPK, TOPK, W, dense=True))
        fin, fexp, st = TC.write_vectors(segs, W, TOPK, s, "func")
        func = {}
        for mode, bub, gap, seed in (("back_to_back", 0, 0, 1), ("bubbles_and_gaps", 30, 20, 7)):
            rec = TC.simulate(binary, fin, fexp, bub, gap, seed)
            rec["pass"] = bool(rec["pass"] and rec.get("segments") == len(segs) and
                               rec.get("outputs") == st["expected_outputs"] and
                               rec.get("lat0_min") >= TC.lat0(W) and rec.get("lat0_max") <= TC.lat0(W) + 1)
            func[mode] = dict(rec, bubble_percent=bub, gap_percent=gap, seed=seed)
            ok &= rec["pass"]
        print("functional", {m: (r.get("errors"), r.get("segments")) for m, r in func.items()}, flush=True)
        # -- shipped contexts: one segment per run so the latency is the unit's alone ----------------------
        cases = []
        for ctx in CONTEXTS:
            cases.append(("ratio1_source", ctx, ctx, "scaled"))
            cases.append(("ratio2_source", ctx, ctx // 2, "scaled"))
            cases.append(("ratio1_reuse_candidate_masked", ctx, ctx, "masked"))
            cases.append(("ratio1_reuse_candidate_stream", ctx, min(ctx, CAND_POSITIONS), "scaled"))
        for kind, ctx, n, how in cases:
            vals = scaled(rng, finite, n) if how == "scaled" else candidate_masked(rng, finite, n)
            seg = TC.seg_record(rng, vals, np.arange(n), TOPK, TOPK, W, dense=True)
            fi, fe, st1 = TC.write_vectors([seg], W, TOPK, s, f"{kind}_{ctx}")
            rec = TC.simulate(binary, fi, fe)
            beats = st1["beats"]
            lat = [2 * beats + rec.get("lat0_min", -10**9), 2 * beats + rec.get("lat0_max", -10**9)]
            row = {"layer_kind": kind, "context": ctx, "scores": n, "beats": beats,
                   "cycles_after_last_beat": lat[1], "cycles_from_first_beat": lat[1] + beats - 1,
                   "formula_after_last_beat": 2 * beats + TC.lat0(W), "errors": rec.get("errors"),
                   "outputs": rec.get("outputs"), "pass": bool(rec.get("pass") and
                                                              lat[0] >= 2 * beats + TC.lat0(W) and
                                                              lat[1] <= 2 * beats + TC.lat0(W) + 1)}
            ok &= row["pass"]
            long_rows.append(row)
            print(kind, ctx, n, row["cycles_after_last_beat"], row["pass"], flush=True)
        hier = None if quick else TC.hierarchy(np.random.default_rng(777), binary, W, IW, TOPK, htrials, s, "two_level")
        if hier:
            ok &= hier["pass"]
            print("two-level", hier["pass"], flush=True)
    return {
        "schema": "opentallas.hdc-v41-tselect-scale-campaign.v1",
        "status": "pass" if ok else "fail",
        "claim_boundary": "functional cycle-level RTL simulation of ot_hdc_tselect at the shipped index top-k "
                          "parameters (behavioural line memory in the bench) against tools/hdc_golden_v41.py "
                          "topk_lowest_index; latencies are clock edges, converted to time only with a routed fmax",
        "parameters": {"W": W, "VW": 16, "IW": IW, "K": TOPK, "AW": AW, "max_positions": (1 << AW) * W,
                       "lat0": TC.lat0(W), "line_memory_bits": (1 << AW) * W * (1 + 16 + IW)},
        "shipped_shape": {"index_heads": OPC["index_heads"], "index_head_dim": OPC["index_head_dim"],
                          "index_topk": TOPK, "max_context_tokens": MAX_CONTEXT,
                          "candidate_positions_on_reuse_layers": CAND_POSITIONS},
        "latency_definition": "clock edges from the edge that accepts a segment's last beat to the edge that "
                              "registers its out_last beat = 2 x beats + LAT0 (+1); beats = ceil(scores / 64), "
                              "one beat per cycle while the scores stream in",
        "real_data": dict(meta, golden_selection_checks=checks),
        "functional": dict(st, runs=func, real_index_segments=len(sets["index"])),
        "shipped_context_rows": long_rows,
        "two_level": hier,
        "verilator_lint": {"returncode": lint.returncode, "messages": lint.stderr.strip().splitlines()[:10]},
        "input_sha256": {str(p.relative_to(ROOT)): sha(p) for p in (TC.RTL, TC.TB, TC.HARNESS, *TC.TOOLS,
                                                                       Path(__file__))},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--output", type=Path, default=OUT)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--real-cache")
    a = ap.parse_args()
    r = run(a.quick, a.real_cache)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(r, indent=2, sort_keys=True) + "\n")
    print(r["status"])
    return 0 if r["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
