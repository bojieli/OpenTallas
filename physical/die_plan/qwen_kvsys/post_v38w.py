#!/usr/bin/env python3
"""KV-G3 10-24: plan v3.8w = v3.8v + core spreads from the KVG3-CORES review-before-route (FAIL x2; core views unchanged:
only origins move, pins files are core-relative).
  * kv3_pv*: each pv group's p0 (R0) N face sat 25.92 um under p1, p3 (MX) S face 25.92 um over p2; 1030 of 1652 pins
    per pair detour through those gaps; KV-G3 render: the join's 1024 S-face pins (to p0, not p1) also sat 25.92 um over
    p1.  p1 +77.76, join / p2 +155.52, p3 +233.28 um (18/36/54 x 4.32) -> p0|p1, p1|join, p2|p3 gaps 103.68 um; join|p2
    stays 25.92 (join N <-> p2 S connect); the empty top of the partition absorbs it (p3 top 1304.64 < 1520.64 - 34.56).
  * kv3_pc*: kvpc2/kvpc3 S faces (1107 pins each) sat 25.92 um over kvpc1/kvpc0; kvpc0/kvpc1 -77.76 um -> gap 103.68 um
    (lower 750 um of the partition is empty).
G0/G0C re-check every hard-core overlap, halo and internal-station hop.   usage: post_v38w.py die_plan.json > die_plan.json"""
import json
import re
import sys

D1, D2, D3 = 77.76, 155.52, 233.28


def mv(c, dy):
    c["origin_um"] = [c["origin_um"][0], round(c["origin_um"][1] + dy, 3)]
    c["note"] = c.get("note", "") + f" | v3.8w moved {dy:+g} um y (KVG3-CORES review: pin gap)"


def main():
    p = json.load(open(sys.argv[1]))
    n = 0
    for tn, t in p["partition_types"].items():
        for c in t.get("hard_cores") or []:
            if re.fullmatch(r"kv3_pv(_v\d+)?", tn):
                if re.fullmatch(r"pvg\d+_p1", c["inst"]):
                    mv(c, D1); n += 1
                elif re.fullmatch(r"pvg\d+_p2|pv__u_g\d+_j", c["inst"]):
                    mv(c, D2); n += 1
                elif re.fullmatch(r"pvg\d+_p3", c["inst"]):
                    mv(c, D3); n += 1
            elif re.fullmatch(r"kv3_pc(_v\d+)?", tn) and c["inst"] in ("kvpc0", "kvpc1"):
                mv(c, -D1); n += 1
    p["note"] = p.get("note", "") + " | v3.8w (KV-G3 10-24): pv pair / pc core spreads (KVG3-CORES review, gaps 25.92 -> 103.68 um)"
    sys.stderr.write(f"post_v38w: moved {n} hard cores\n")
    json.dump(p, sys.stdout, indent=1)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
