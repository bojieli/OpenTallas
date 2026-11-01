#!/usr/bin/env python3
"""DIE-QC-59 11-01: macro channel one-block fix for the QC st_a / slw_st_b_v2 SRAM columns (KIT-WAVE-12 FAIL PLAN
@preflight macro_channels, tools/die_plan/kit_contract.py, min channel 10.8 um = 2x4.32 halo + 8 rows).

Every failing type has ONE 32x64 SRAM placed 8.64 um off its column, leaving a 2.592 um vertical channel between two
macro columns (no routable rows between the halos):
  * sle_st_a_v1__* (3), sle_st_a_v2, slw_st_a_v1__* (2), slw_st_a_v2__* (2): u_u_r0.u_hb / u_skn / u_sks at x 345.6
    (col [345.6,386.208] vs col [267.84,343.008]) -> x 354.24, the r0 scale_wait column (same column the r1..r3
    scale_wait macros use).  The y stack keeps its 8.64 um halo abutment to u_scale_wait (112.32..129.6 -> 138.24).
  * slw_st_b_v2: u_u_r5.u_skn at x 233.28 (col [233.28,265.248] vs col [267.84,299.808]) -> x 224.64.
Only hard_cores[*].origin_um[0] changes (8.64 um, on the existing x grid); no logic, pins, ports, taps or outlines.
usage: delta_mchan_1101.py PLAN_IN PLAN_OUT"""
import json
import sys

MOVES = {  # (type prefix tuple, inst suffix, old x, new x)
    "st_a": (("sle_st_a_v", "slw_st_a_v"), ("u_u_r0.u_hb.", "u_u_r0.u_skn.", "u_u_r0.u_sks."), 345.6, 354.24),
    "st_b": (("slw_st_b_v2",), ("u_u_r5.u_skn.",), 233.28, 224.64),
}


def main():
    pin, pout = sys.argv[1:3]
    text = open(pin).read()
    raw = json.loads(text)
    assert json.dumps(raw) + "\n" == text, "plan text style is not one-line json.dumps"
    n = 0
    for tn, t in raw["partition_types"].items():
        for key, (pref, insts, old, new) in MOVES.items():
            if not tn.startswith(pref):
                continue
            for hc in t.get("hard_cores", []):
                if any(s in hc["inst"] for s in insts):
                    assert abs(hc["origin_um"][0] - old) < 1e-6, (tn, hc["inst"], hc["origin_um"])
                    hc["origin_um"][0] = new
                    n += 1
                    print(f"MCHAN {tn} {hc['inst']} x {old:g} -> {new:g}")
    assert n == 8 * 3 + 1, n
    open(pout, "w").write(json.dumps(raw) + "\n")


if __name__ == "__main__":
    main()
