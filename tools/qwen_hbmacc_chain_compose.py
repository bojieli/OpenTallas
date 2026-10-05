#!/usr/bin/env python3
"""Qwen3-8B HBM accelerator at 8K (P8191): compose the per-user AR and DSpark rates from MEASURED stages.

Owner rules: one token at the target position, one RTL job per layer type (+ head), composed analytically;
every term is a measured stage result (token_result.json of tools/qwen_hbmacc_rt_token_w12.py or
tools/qwen_hbmacc_rt_verify_w12.py); terms that are not measured on this vehicle are listed under
"unvalidated" with their source.  Stage time composition as HA8: 7 + sum(stage cycles) + (stages - 1).

    --terms terms.json   {"name": {"cycles": int, "source": str, "exact": bool, "measured": bool}, ...}
    --out compose.json

AR:      a/b baseline (HA8 SRAM placement: lm_head, then the leading layers) and the SRAM SPREAD (the same
         SRAM budget split over the 36 layers, each layer's share its leading code words).
DSpark:  step = verify + draft + commit; verify = 36 x verify layer (p = 4, each HBM code word reused by the 4
         positions from the prefetch window) + verify head (p = 4); draft = 5 x drafter layer (S = 3) + drafter
         head over 3 slots (linear in the measured p = 1 / p = 4 heads, as tools/qwen_dspark_step_collect.py) +
         ingest + Markov (priced on the ROM, unvalidated); rate = tau x f / step.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

F = 1.2e9
TAU = 3.0375          # owner 6-class equal blend of tau_w8_S3_B4 (results/rtl/qwen_dspark_system_20261004)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--terms", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    T = json.loads(a.terms.read_text())
    c = lambda k: T[k]["cycles"]  # noqa: E731

    def stages(parts):
        n = sum(k for k, _ in parts)
        return 7 + sum(k * c(name) for k, name in parts) + (n - 1)

    rows = {}

    def ar(label, parts):
        cyc = stages(parts)
        rows[label] = {"composition": [[k, n, c(n)] for k, n in parts], "cycles": cyc, "us": round(cyc / F * 1e6, 2),
                       "tok_s": round(F / cyc, 1), "terms_measured": all(T[n]["measured"] for _, n in parts),
                       "terms_exact": all(T[n]["exact"] for _, n in parts)}
        return cyc

    a_base = ar("a_AR_baseline", [(1, "a_L0_sram"), (1, "a_L1_partial"), (34, "a_L_hbm"), (1, "a_head_p1")])
    a_spr = ar("a_AR_spread", [(36, "a_L_spread"), (1, "a_head_p1")])
    b_base = ar("b_AR_baseline", [(5, "b_L0_sram"), (1, "b_L5_partial"), (1, "b_L6_first_hbm"), (29, "b_L_hbm"),
                                  (1, "b_head_p1")])
    b_spr = ar("b_AR_spread", [(36, "b_L_spread"), (1, "b_head_p1")])
    for lab, base, new in (("a", a_base, a_spr), ("b", b_base, b_spr)):
        rows[f"{lab}_spread_gain_pct"] = round((base / new - 1) * 100, 3)

    def dspark(lab, ar_cyc):
        v, vh, d = f"{lab}_verify_layer", f"{lab}_verify_head_p4", f"{lab}_drafter_layer"
        h1 = c(f"{lab}_head_p1")
        verify = stages([(36, v), (1, vh)])
        draft_head = h1 + 2 * (c(vh) - h1) / 3
        draft = 5 * c(d) + draft_head + c(f"{lab}_ingest_markov")
        commit = c("commit")
        step = verify + draft + commit
        unval = [n for n in (v, vh, d, f"{lab}_ingest_markov", "commit") if not T[n]["measured"]]
        rows[f"{lab}_DSpark"] = {"verify": verify, "draft": round(draft), "draft_head_3slots": round(draft_head),
                                 "commit": commit, "step": round(step), "tau": TAU,
                                 "tok_s": round(TAU * F / step, 1), "vs_AR": round(TAU * ar_cyc / step, 3),
                                 "unvalidated_terms": unval}

    dspark("a", a_spr)
    dspark("b", b_spr)
    rec = {"schema": "opentallas.hbm-accel-qwen-p8191-chain-composition.v1", "clock_hz": F, "terms": T, "rows": rows}
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
