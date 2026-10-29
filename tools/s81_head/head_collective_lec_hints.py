#!/usr/bin/env python3
"""Untrusted LEC matches for a HEAD safe4 collective lane.

These names are the actual original synthesis aliases, not replacement flops.
lec.py proves every relation and the FSM constraint by ordinary induction.  A
changed synthesis mapping fails the proof rather than bypassing retention.
"""
import argparse
import json
from pathlib import Path


def collective_lec_hints(prefix="ff:u_dut.u_lane.u"):
    p = prefix.rstrip(".") + "."
    bits = [p + f"u_gb.hunt[{i}]" for i in range(2)]
    hints = [["gate", p + f"u_gb.hunt#t[{bit}]",
              ["cube", "gold", bits, [(code >> i) & 1 for i in range(2)]]]
             for code, bit in ((0, 0), (1, 2), (2, 1))]
    hints.append(["cons", "gold", bits, [[0, 0], [1, 0], [0, 1]]])
    # s2v was folded into ok_f; its other same-edge copy remains distinct.
    hints.append(["both", p + "u_ep.g_fcopy.u_k_ok_f3.q",
                  ["eq", "gold", p + "u_ep.ok_f", 0]])
    # Name each physical alias FF against the exact kept demand, rather than
    # an interchangeable replica.  The kept-register bipartite test still
    # requires one separate gate flop per demanded bit.
    for gate, gold in (("u_ep.in_ready", "u_ep.rdy_k[3]"),
                       ("u_gb.g_pc[0].g_b[0].a0", "u_gb.g_pc[0].ps[5]"),
                       ("u_gb.g_pc[11].g_b[280].a2", "u_gb.g_pc[11].ps[3]"),
                       ("u_gb.g_pc[5].g_b[140].a1", "u_gb.g_pc[5].ps[4]")):
        hints.append(["gate", p + gate, ["eq", "gold", p + gold, 0]])
    return hints


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lane-prefix", action="append", default=[])
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    hints = [h for p in (args.lane_prefix or ["ff:u_dut.u_lane.u"])
             for h in collective_lec_hints(p)]
    args.output.write_text(json.dumps(hints, indent=1) + "\n")


if __name__ == "__main__":
    main()
