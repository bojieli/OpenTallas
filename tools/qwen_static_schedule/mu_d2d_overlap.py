#!/usr/bin/env python3
"""MU-DQ-TOK (2026-10-19): can the as-built compute <-> KV D2D link play the 4-user calendar of record (record_op)?

ot_qwen_d2d_cal (rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_static.sv) has ONE playhead per calendar: a layer exchange
is segment 0, started once a layer, and `start while running` is a sticky fault.  A layer's segment spans the whole
attention op (CMD + 32 Q out, KV service, 32 RESULT + STATUS back; tb_xdie_qwen_exchange: CMD issue -> R31 land 1,844).
mu_opcal.compile_frame reserves only d2d_q / kvs / d2d_o windows, so the NEXT user's CMD/Q may leave while the previous
user's segment is still running.  This tool counts those overlaps on the frame of record and recompiles the frame with
the attention span made exclusive (seg_windows hook, resource 'd2dcal') = what the as-built link can play.

    python3 -m qwen_static_schedule.mu_d2d_overlap [--out JSON]      (from tools/)
"""
from __future__ import annotations

import argparse
import json

from . import mu_calendar as M
from . import mu_opcal as O


def exchanges(cal):
    ev = []
    for u, seq in cal["schedule"].items():
        for n, t0, b in seq:
            w = b["windows"]
            if "d2d_q" in w:
                ev.append(dict(user=u, unit=n, q=min(a for a, _ in w["d2d_q"]) + t0, o=max(e for _, e in w["d2d_o"]) + t0))
    ev.sort(key=lambda e: e["q"])
    return ev


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--frame", type=int, default=16)
    a = ap.parse_args()
    rec = cal = O.compile_frame(a.frame)
    ev = exchanges(cal)
    ov = [(x, y) for x, y in zip(ev, ev[1:]) if y["q"] < x["o"]]
    p = M._need(dict(M.SOURCED, users=O.NU, occupancy="measured", head_chunks=8))
    att = M.layer_block(p)["ops"]["attention"]
    excl = O.compile_frame(a.frame, p={"seg_windows": {"layer": {"d2dcal": [tuple(att)]}}})
    res = dict(
        schema="opentallas.qwen.mu_d2d_overlap.v1", frame_tokens=a.frame,
        record_op=dict(aggregate_tok_s=round(rec["aggregate_tok_s"], 1), per_user=[round(u["tok_s"], 1) for u in rec["users"]]),
        exchanges=len(ev), exchange_span=att[1] - att[0], adjacent_overlaps=len(ov),
        first_overlaps=[dict(prev=x, next=y) for x, y in ov[:3]],
        single_playhead=dict(attention_window_exclusive=list(att), aggregate_tok_s=round(excl["aggregate_tok_s"], 1),
                             per_user=[round(u["tok_s"], 1) for u in excl["users"]]),
        verdict=("AS-BUILT D2D CANNOT PLAY record_op" if ov else "record_op playable by one playhead"),
        fix=("ot_qwen_d2d_cal: separate C->K request and K->C response segments (or 2 playheads) so a user's request "
             "segment may start while another user's response segment runs; compiler emits per-user segment starts "
             "from record_op; KV programme must accept the next CMD while its RESULT tail runs"))
    s = json.dumps(res, indent=1)
    if a.out:
        open(a.out, "w").write(s + "\n")
    print(s)


if __name__ == "__main__":
    main()
