#!/usr/bin/env python3
"""KV-PLAN2 10-25 (plan v3.9d): per-type face pin budget from G2 evidence (COORD KV RULING 2026-10-25 05:07 (a)).

The ruling allows a type's face density above the 6 pins/um default up to the density its own G2 probe proved
(GRT overflow 0 with the plan's pins, hard cores obstructing M1-M7), track use <= 0.6, hard cap 16 pins/um, and only
after the pins sit in the channel gaps (chan_windows.py type-frame classes).  This pass reads check.py's own face
findings (same 10-um window measure), takes each type's worst window, and writes on every type that exceeds the
default:
    face_pins_per_um = worst measured density rounded up to 0.1 (<= 16)
    face_budget_g2   = "<g2 table>:<type>"  (the probe record)
only when the type's G2 record PASSes (overflow 0, usage <= 0.6).  A type without a PASS keeps the default, so its
face findings stay ERRORs.
usage: face_budget.py PLAN.json --g0 g0_report.json --g2 G2TABLE.json --g2-ref results/.../g2_v39d.json [--out PLAN]
"""
import argparse
import json
import math
import re
from collections import defaultdict
from pathlib import Path

MSG = re.compile(r"^(\S+)\.([NSEW]): (\d+) pins in the ([\d.]+)-um window at \S+ \(([\d.]+)/um > ([\d.]+)\)")
CAP = 16.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--g0", required=True)
    ap.add_argument("--g2", required=True)
    ap.add_argument("--g2-ref", required=True)
    ap.add_argument("--out")
    a = ap.parse_args()
    raw = json.loads(Path(a.plan).read_text())
    parts = raw["partitions"]
    ptype = {p["name"]: p["type"] for p in parts} if isinstance(parts, list) else {k: v["type"] for k, v in parts.items()}
    worst = defaultdict(float)
    g0 = json.loads(Path(a.g0).read_text())
    for it in g0.get("items", g0.get("findings", [])):
        if it.get("check") != "faces":
            continue
        m = MSG.match(it["msg"])
        if m and m.group(1) in ptype:
            worst[ptype[m.group(1)]] = max(worst[ptype[m.group(1)]], float(m.group(5)))
    g2 = json.loads(Path(a.g2).read_text())["types"]
    out = dict(set={}, no_g2=[], g2_fail={}, over_cap={})
    for tn, d in sorted(worst.items()):
        t = raw["partition_types"][tn]
        per = math.ceil(d * 10 - 1e-6) / 10
        rec = g2.get(tn)
        if per > CAP:
            out["over_cap"][tn] = d
        elif rec is None:
            out["no_g2"].append(tn)
        elif not rec.get("pass"):
            out["g2_fail"][tn] = rec
        else:
            t["face_pins_per_um"] = per
            t["face_budget_g2"] = f"{a.g2_ref}:{tn}"
            out["set"][tn] = per
    Path(a.out or a.plan).write_text(json.dumps(raw, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
