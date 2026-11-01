#!/usr/bin/env python3
"""Q4 mode-replica correspondence candidates; every kit proves them inductively.

The three east st_b wrappers have four stations sharing the same config/reset.
Gold keeps per-station u_m2 representatives while synthesis may select r4's
replica. These are hints only: no RTL, clock, reset window or compare gate changes.
"""
import argparse
import json
from pathlib import Path

TYPES = ("sle_st_b_v1", "sle_st_b_v2__cl14c98df5", "sle_st_b_v2__clfde1249e")


def hints():
    name = "ff:u_dut.u_bound.u_u_r{}.g_mode_payload[0].u_m2.used_q[{}]"
    return [["gold", name.format(r, bit), ["eq", "gold", name.format(4, bit), 0]]
            for r in (5, 6, 7) for bit in (0, 1)]


def apply(raw):
    for tn in TYPES:
        t = raw["partition_types"][tn]
        assert {"u_r4", "u_r5", "u_r6", "u_r7"} <= {c["inst"] for c in t["contents"]}, tn
        current = t.setdefault("lec_hints", [])
        for hint in hints():
            if hint not in current:
                current.append(hint)
    return raw


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input")
    p.add_argument("output")
    a = p.parse_args()
    raw = apply(json.loads(Path(a.input).read_text()))
    Path(a.output).write_text(json.dumps(raw, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
