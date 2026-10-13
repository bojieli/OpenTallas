#!/usr/bin/env python3
"""Normalised x-write operand comparison for tb_xload_cadence beats.txt files.

A beats.txt line is "id cyc addr grp data".  The normalised stream is every beat's
(id, addr, grp, data) in command order with the timing column (cyc) excluded; its
sha256 is taken over the lines "id addr grp data" joined by "\\n" (no trailing newline; the
definition behind results/rtl/xload_vm8_flow_1013/comparison.json).  --cycles also requires the
timing column to match (the XW_FLOW=0 default-path check).
"""
import argparse
import hashlib
import json
import sys


def load(path):
    rows = []
    with open(path) as f:
        for line in f:
            parts = line.split()
            if len(parts) != 5:
                raise SystemExit(f"{path}: malformed line {len(rows) + 1}")
            rows.append(parts)
    return rows


def normalised(rows):
    return hashlib.sha256("\n".join(f"{i} {a} {g} {d}" for i, _c, a, g, d in rows).encode()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("baseline")
    ap.add_argument("candidate")
    ap.add_argument("--cycles", action="store_true", help="also require identical cycle columns")
    ap.add_argument("--expect-sha256", default=None, help="required normalised sha256 of the baseline")
    a = ap.parse_args()
    b, c = load(a.baseline), load(a.candidate)
    mism = sum(1 for x, y in zip(b, c) if (x[0], x[2], x[3], x[4]) != (y[0], y[2], y[3], y[4]))
    cyc = sum(1 for x, y in zip(b, c) if x[1] != y[1])
    out = {
        "baseline_beats": len(b), "beats": len(c), "payload_mismatches": mism,
        "baseline_normalized_sha256": normalised(b), "normalized_sha256": normalised(c),
        "cycle_mismatches": cyc,
    }
    ok = len(b) == len(c) and mism == 0 and out["baseline_normalized_sha256"] == out["normalized_sha256"]
    if a.expect_sha256 is not None:
        ok = ok and out["baseline_normalized_sha256"] == a.expect_sha256
    if a.cycles:
        ok = ok and cyc == 0
    out["exact"] = ok
    json.dump(out, sys.stdout, indent=1)
    print()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
