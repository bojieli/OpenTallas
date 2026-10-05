#!/usr/bin/env python3
"""Measure one expert's bit-copy activation gather on the 64-byte PX stage.

The seven expert gathers are identical in size (38 VM words per die). This
bench measures the repeated operation's startup/tail; it does not assume that
the blocked COLL-v1 core can overlap its ME with the gather.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import rtl_v41_stage_collective_campaign as B
import rtl_v41_collective_levers_campaign as L
from rtl_v41_tp_rowsplit_collectives import patterns_from_design_point

ROOT = Path(__file__).resolve().parents[1]
TB = ROOT / "rtl/test/tb_v41_tp_rowsplit_px.sv"
B.LANES = 16
B.WORD_B = 64


def build(scratch: Path) -> dict:
    base = patterns_from_design_point()["act"]
    B.PATTERNS["expert_act"] = dict(base, words=38,
                                    node="L0.ffn.expert_act_allgather",
                                    consumer="one complete expert activation")
    lp = B.link_params()
    old_params, old_tb = L.top_params, L.TB
    L.TB = TB

    def top_params(case, link):
        top, params = old_params(case, link)
        params["PUSHW"] = 1
        params["PAIRWISE"] = 1
        return top, params

    L.top_params = top_params
    try:
        cases = [L.run_case(scratch, dict(name=f"expert_act_d{depth}_q{qtx}_blocked",
                                              pattern="expert_act", lever="relay_add3",
                                              depth=depth, qtx=qtx, lanes=16, order="blocked"), lp)
                 for depth, qtx in ((16, 2), (128, 64))]
    finally:
        L.top_params, L.TB = old_params, old_tb
    for c in cases:
        assert c["passed"] and c["mismatches"] == c["out_err"] == c["timeout"] == 0
        assert all(f == 0 for f in c["faults"])
    fused_path = ROOT / "results/rtl/v41_tp_rowsplit_die_collectives.json"
    fused = json.loads(fused_path.read_text())
    fused_tail = next(c["exposed_tail_cycles"] for c in fused["cases"]
                      if c["case"] == "die_act_d16_q2_blocked")
    sources = ("tools/rtl_v41_w2_expert_stream_stage.py", "tools/rtl_v41_tp_rowsplit_collectives.py",
               "tools/rtl_v41_stage_collective_campaign.py", "tools/rtl_v41_collective_levers_campaign.py",
               "rtl/test/tb_v41_tp_rowsplit_px.sv", "rtl/rom/ot_rom_oneshot_px.sv",
               "rtl/proto/ot_fp32_add_rne_pipe.sv", "results/arch/v41_lanes.json",
               "results/rtl/v41_tp_rowsplit_die_collectives.json")
    return dict(schema="v41_w2_expert_stream_stage_v1", scope="one expert's 38-word gather on stage RTL; "
                "producer timing stub and behavioural T1; no nonblocking COLL or ME overlap implemented",
                source_sha256={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sources},
                expert_count=7, per_expert_words_per_die=38, fused_words_per_die=266,
                serial_v1_projection=dict(depth16_qtx2_seven_isolated_tail_cycles=
                                          7 * cases[0]["exposed_tail_cycles"],
                                          same_contract_fused_tail_cycles=fused_tail,
                                          extra_cycles_before_me_drains=
                                          7 * cases[0]["exposed_tail_cycles"] - fused_tail,
                                          caveat="seven isolated one-shot operations multiplied; "
                                          "seven-op full core program not run"),
                cases=cases, summary={c["case"]: dict(tail_cycles=c["exposed_tail_cycles"],
                producer_stall_cycles=c["producer_stall_cycles"],
                consumer_last_word_cycle=c["consumer_last_word_cycle"]) for c in cases})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratch", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=ROOT / "results/rtl/v41_w2_expert_stream_stage.json")
    a = ap.parse_args()
    a.scratch.mkdir(parents=True, exist_ok=True)
    rec = build(a.scratch)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
    print(json.dumps(rec["summary"], indent=2))


if __name__ == "__main__":
    main()
