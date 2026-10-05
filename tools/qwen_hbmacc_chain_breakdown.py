#!/usr/bin/env python3
"""Qwen3-8B HBM accelerator: per-chain cycle breakdown of one measured layer stage (RT_ITRACE run of
tools/qwen_hbmacc_rt_token_w12.py) against its bandwidth floor.

Inputs: the stage's token.log (RT_ITRACE die-0 instruction fetches, ME-clock and collective edges, the HBMSTAT
attribution) and the die-0 program.hex / segments.hex of that stage.

Method (measured issue timeline, no model):
  * issue cycle of each instruction from the fetch trace (tools/qwen_body_wire_latency.trace_issue_times: in
    steady state the fetch of word f follows the issue of word f - 5 by one cycle), per program segment;
  * every instruction is labelled with the layer chain it belongs to, from its decoded fields in program order
    (norm, QKV matvec, q/k-norm + RoPE + KV write, attention QK / softmax / PV, o, all-reduce, residual, post-attn
    norm, gate/up, SiLU-mul, down, all-reduce, residual + next norm);
  * the layer's in-order issue timeline is partitioned: the cycles from an instruction's issue to the next
    instruction's issue are charged to its chain (the last one to the stage end).  Overlap is therefore folded
    into the chain that holds the issue slot -- which is exactly the critical-path share of each chain;
  * floor: stream words x 98,304 B over the die's stacks at peak (1.0 TB/s a stack) and at the measured stream
    rate of the record; SRAM-resident code words: one word an engine edge.

  python3 tools/qwen_hbmacc_chain_breakdown.py --log RUN/token.log --program P.hex --segments S.hex
          --stage L2 --tp 2 --stacks 4 [--words N --sram-words M] --out out.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

WORD = 98304
CORE_HZ = 1.2e9


def labels(fields):
    """chain label of every instruction (program order of the norm-folded TP layer)."""
    out, att_seen = [], False
    dense = 0
    for f in fields:
        u = f["unit"]
        if u == 1 and f.get("me_wsrc"):
            att_seen = True
            out.append("attn_QK" if f.get("me_rmax") else "attn_PV")
            continue
        if u == 1:
            dense += 1
            out.append({1: "qkv_matvec", 2: "o_matvec", 3: "gu_matvec", 4: "down_matvec"}.get(dense, f"matvec{dense}"))
            continue
        if u == 0:
            out.append("allreduce1" if dense <= 2 else "allreduce2")
            continue
        # stream unit
        if dense == 0:
            out.append("norm1_sumsq")
        elif dense == 1 and not att_seen:
            if f.get("sfu") == 3 and f.get("su_nin", 0) <= 1:
                out.append("norm1_rsqrt_scale")
            elif f.get("b_src") == 1:
                out.append("rope_kvwrite")
            else:
                out.append("qk_norm_vwrite")
        elif dense == 1 and att_seen:
            out.append("softmax")
        elif dense == 2:
            # after o: the collective's residual / sumsq, or the softmax tail when o is not yet issued
            out.append("residual1_norm2_sumsq" if f.get("c_src") or f.get("red_sq") else "softmax")
        elif dense == 3:
            out.append("silu_mul" if f.get("sfu") == 4 else "norm2_rsqrt_scale")
        else:
            out.append("residual2_next_norm_sumsq")
    if fields and fields[-1]["unit"] == 0:
        out[-1] = "end_barrier"
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--log", type=Path, required=True)
    ap.add_argument("--program", type=Path, required=True)
    ap.add_argument("--segments", type=Path, required=True)
    ap.add_argument("--stage", required=True)
    ap.add_argument("--tp", type=int, required=True)
    ap.add_argument("--stacks", type=int, default=4)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    os.environ.setdefault("QWEN_O4_TP", str(a.tp))
    os.environ.setdefault("QWEN_O4_GROUPS", "6144")
    os.environ.setdefault("HDC_SU_WIDTH", "64")
    import qwen_body_wire_latency as B      # noqa: E402
    import hdc_qwen_fullshape_isa_w12 as QI  # noqa: E402
    fields = [QI.decode_instruction(int(x, 16)) for x in a.program.read_text().split()]
    lab = labels(fields)
    text = a.log.read_text()
    st = re.search(rf"STAGE {a.stage} done cycles=(\d+) start_cyc=(\d+) end_cyc=(\d+)", text)
    cycles, start, end = int(st.group(1)), int(st.group(2)), int(st.group(3))
    hs = re.search(rf"HBMSTAT {a.stage} die0 (.*)", text)
    hb = {k: int(v) for k, v in (x.split("=") for x in hs.group(1).split())}
    ev = B.parse_trace(a.log)
    bases = B.seg_bases(a.segments)
    win = B.trace_windows(ev, bases, end)
    issue = B.trace_issue_times(ev, win, len(fields))
    order = sorted(issue)
    chains = {}
    for k, pc in enumerate(order):
        nxt = issue[order[k + 1]] if k + 1 < len(order) else end
        chains[lab[pc]] = chains.get(lab[pc], 0) + (nxt - issue[pc])
    first = issue[order[0]] - start
    chains["start_to_first_issue"] = first
    words = hb.get("words_done", 0)
    floor_peak = words * WORD / (a.stacks * 1.0e12) * CORE_HZ
    span = hb["ctl_cycles"]
    rec = {"schema": "opentallas.hbm-accel-qwen-chain-breakdown.v1", "stage": a.stage, "tp": a.tp,
           "cycles": cycles, "chains_critical_path_cycles": chains, "sum_check": sum(chains.values()),
           "hbmstat_die0": hb, "stream_words": words,
           "floor_cycles_at_peak": round(floor_peak), "measured_over_peak_floor": round(cycles / floor_peak, 4) if words else None,
           "issue": {str(pc): [lab[pc], issue[pc] - start] for pc in order},
           "inputs": {"log": str(a.log), "program": str(a.program), "segments": str(a.segments)}}
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: rec[k] for k in ("stage", "cycles", "chains_critical_path_cycles", "sum_check",
                                          "floor_cycles_at_peak", "measured_over_peak_floor")}, indent=1))


if __name__ == "__main__":
    main()
