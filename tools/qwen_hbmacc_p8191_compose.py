#!/usr/bin/env python3
"""Qwen3-8B HBM accelerator at the 8K target (position 8,191): compose the per-user token from measured stages.

Owner rules: one token at P8191 with 8,192 positions of KV, one RTL job per layer TYPE (+ head), each entered from
the GPU golden exit of the previous layer (tools/qwen_hbmacc_layer_parallel.py); token = 7 + sum(stage cycles) +
(stages - 1), as the HA8 P1023 record composes it.  Every term is a measured token_result.json; nothing modelled.

    --stage NAME=COUNT=PATH/token_result.json  (repeatable, in token order)
    --out FILE

Stream metrics per stage (die 0; the dies are identical):
  * bytes        = stream words x 98,304 B (weights + this layer's KV of positions < P, FP8 K and V)
  * layer TB/s   = bytes / stage time at 1.2 GHz              (achieved, over the whole layer)
  * stream TB/s  = bytes / (controller cycles - preroll) x 1.024 ns   (the controller's span for this layer)
  * blocked      = room_block / (32 PCs x stacks): controller cycles a landed sector waited for window room
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

CORE_HZ = 1.2e9
CTL_NS = 1.024
WORD = 98304
PEAK_STACK = 1.0e12


def stage_row(name, count, path):
    r = json.loads(Path(path).read_text())
    st = r["stages"][name]
    d0 = st["die0"]
    ms = r["memory_system"]
    words = d0["words_done"]
    stacks = ms["stacks_per_die"]
    cyc = st["cycles"]
    ctl_span = d0["ctl_cycles"] - ms["preroll_ctl_cycles"]
    plan = r["plan"][0]
    hbm_words = plan["hbm_words"]
    row = {"stage": name, "count": count, "status": r["status"], "cycles": cyc,
           "x_mismatches": sum(c["mismatches"] for c in r["layer_x_checks"].values()),
           "rtl_token": r.get("rtl_token"), "rtl_logit_bits": r.get("rtl_logit_bits"),
           "oracle_token": r.get("oracle_token"), "oracle_logit_bits": r.get("oracle_logit_bits"),
           "window_words": ms["window_words"], "kv_words": ms["kv_words_per_layer"], "stream_words": words,
           "hbm_words": hbm_words, "sram_words": plan["sram_words"], "preroll_ctl_cycles": ms["preroll_ctl_cycles"],
           "attribution_die0": {k: d0[k] for k in ("hbm_wait", "kv_wait", "matmul", "attention", "collective",
                                                   "stream_unit", "other")},
           "tail_after_last_wread": st["end_cyc"] - d0["last_wread_cyc"] if d0.get("last_wread_cyc") else None,
           "source": str(path)}
    if words and hbm_words:
        b = words * WORD
        blocked = d0["room_block"] / (32 * stacks)
        row.update(bytes_per_die=b,
                   layer_TBps_die=round(b / (cyc / CORE_HZ) / 1e12, 4),
                   layer_frac_of_die_peak=round(b / (cyc / CORE_HZ) / (stacks * PEAK_STACK), 4),
                   stream_span_ctl=ctl_span,
                   stream_TBps_stack=round(b / (ctl_span * CTL_NS * 1e-9) / stacks / 1e12, 4),
                   blocked_ctl_cycles=round(blocked, 1),
                   stream_TBps_stack_unblocked=round(b / ((ctl_span - blocked) * CTL_NS * 1e-9) / stacks / 1e12, 4))
    return row


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stage", action="append", required=True)
    ap.add_argument("--label", default="")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    rows = []
    for s in a.stage:
        name, count, path = s.split("=", 2)
        rows.append(stage_row(name, int(count), path))
    n = sum(r["count"] for r in rows)
    total = 7 + sum(r["cycles"] * r["count"] for r in rows) + (n - 1)
    hbm_bytes = sum(r.get("bytes_per_die", 0) * r["count"] for r in rows)
    exact = all(r["status"] == "pass" and r["x_mismatches"] == 0 for r in rows)
    out = {"schema": "opentallas.hbm-accel-qwen-p8191-composition.v1", "label": a.label,
           "stages_in_token": n, "composed_cycles": total, "us": round(total / CORE_HZ * 1e6, 2),
           "ar_tok_s": round(CORE_HZ / total, 1), "all_stages_exact": exact,
           "token_stream_bytes_per_die": hbm_bytes,
           "token_TBps_die_over_token": round(hbm_bytes / (total / CORE_HZ) / 1e12, 4), "stages": rows}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("label", "composed_cycles", "us", "ar_tok_s", "all_stages_exact",
                                          "token_TBps_die_over_token")}))
    for r in rows:
        print(r["stage"], r["count"], r["cycles"], r.get("layer_TBps_die"), r.get("layer_frac_of_die_peak"),
              r.get("stream_TBps_stack"), r.get("stream_TBps_stack_unblocked"), r["attribution_die0"])


if __name__ == "__main__":
    main()
