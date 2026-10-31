#!/usr/bin/env python3
"""Untrusted LEC matches for a HEAD safe4 collective lane.

These names are the actual original synthesis aliases, not replacement flops.
lec.py proves every relation and the FSM constraint by ordinary induction.  A
changed synthesis mapping fails the proof rather than bypassing retention.
"""
import argparse
import json
from pathlib import Path


def oldread_valid_twin_hints(um, ns=70, ga=4):
    """ot_sram_oldread_b64 write-valid twins (DH50 10-31): the GA kept slice valid_r of one address group and the
    unkept g_address[a].valid_r share D (w_en[a]) and reset value; synthesis merges valid_r into one kept slice copy
    and the gold-only one may be paired with another slice (lane1 bank[1] w/r ce_in false difference in HOST LEC B).
    Tie them all to the group's first slice.  Keys a kit does not have are skipped by lec.py; every one is proved."""
    out = []
    for a in range((ns + ga - 1) // ga):
        rep = um + f"g_slice[{ga * a}].valid_r"
        out += [["both", um + f"g_slice[{s}].valid_r", ["eq", "gold", rep, 0]]
                for s in range(ga * a + 1, min(ga * a + ga, ns))]
        out.append(["gold", um + f"g_address[{a}].valid_r", ["eq", "gold", rep, 0]])
    return out


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
    # DH50 10-31: synthesis merges the unkept rep_r into its kept same-D / same-reset copy rep_ra[0] (the gate's
    # 'replaying' reads rep_ra[0]); the gold-only rep_r may be paired with ANY of its equal twins (u_k_rep_o.q seen in
    # HOST LEC B), which left gold replaying = u_k_rep_o.q vs gate = rep_ra[0] as two free inputs -> 812-point false
    # NOT EQUIVALENT class (rp_r / ready_r / snd / pace / k_off ...).  Tie every kept twin to rep_ra[0].
    for twin in ("u_ep.u_k_rep_o.q", "u_ep.rep_ra[1]"):
        hints.append(["both", p + twin, ["eq", "gold", p + "u_ep.rep_ra[0]", 0]])
    hints += oldread_valid_twin_hints(p + "u_ep.g_rb_safe.u_m.")
    # Name each physical alias FF against the exact kept demand, rather than
    # an interchangeable replica.  The kept-register bipartite test still
    # requires one separate gate flop per demanded bit.
    for gate, gold in (("u_ep.in_ready", "u_ep.rdy_k[3]"),
                       ("u_gb.g_pc[0].g_b[0].a0", "u_gb.g_pc[0].ps[5]"),
                       ("u_gb.g_pc[11].g_b[280].a2", "u_gb.g_pc[11].ps[3]"),
                       ("u_gb.g_pc[5].g_b[140].a1", "u_gb.g_pc[5].ps[4]")):
        hints.append(["gate", p + gate, ["eq", "gold", p + gold, 0]])
    return hints


def beat_tx_pad_hints(prefix, w, n, p=None):
    """Loaded-valid hints for the pad bits of an ot_s81hd_beat_tx g_multi hold register (DH50 10-31).

    hold[i] carries word bit P + i; bits i >= W - P are the zero pad of the last beat.  They have no reset and are
    only ever written with 0 (start loads 0, a shift shifts in 0), so synthesis folds them to 0 while the RTL holds
    X until the first start.  Every read of them (hold[i] <= hold[i + P]) happens while beats are owed (owe != 0),
    which needs a start, so the gold register is bound to (owe != 0 ? 0 : power-up X); lec.py proves the guard
    (owe' != 0 -> D == 0) with the other hypotheses and refuses it unless owe is 0 in the reset state."""
    pfx = prefix.rstrip(".") + "."
    p = p or (w + n - 1) // n
    bw = max(1, (n - 1).bit_length())
    guard = [[[pfx + f"owe[{b}]", 1]] for b in range(bw)]
    return [["gold", pfx + f"g_multi.hold[{i}]", ["loaded", 0, guard]] for i in range(w - p, n * p - p)]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lane-prefix", action="append", default=[])
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--beat-tx", action="append", default=[], metavar="PREFIX:W:N[:P]",
                    help="ot_s81hd_beat_tx instance key prefix (e.g. ff:u_dut.u_core.u_ctl_tx.u_tx) and its W/N/P")
    args = ap.parse_args()
    hints = [h for p in (args.lane_prefix or ["ff:u_dut.u_lane.u"])
             for h in collective_lec_hints(p)]
    for spec in args.beat_tx:
        pre, *num = spec.rsplit(":", 3) if spec.count(":") >= 4 else spec.rsplit(":", 2)
        hints += beat_tx_pad_hints(pre, *map(int, num))
    args.output.write_text(json.dumps(hints, indent=1) + "\n")


if __name__ == "__main__":
    main()
