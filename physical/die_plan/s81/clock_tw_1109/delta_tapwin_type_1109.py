#!/usr/bin/env python3
"""S81 event TAPWIN-TYPE-1109 (DIE-S81-85, COORD 2026-11-09 ruling): clock.tap_window.per_type_ps for every unmeasured type.

Value = worst per-port cross-tap window of the type from die_sta_related's own chain (single_arrival, CPPR LCA, early-core
kit offsets, kit_port_needs, TT+FF, ceil 1 ps, no margin) on the S81 G50 die GRT proof.  The chain reproduces all 1915
ports of kit_window_g50_station.json exactly.  G50 is an OLDER plan (fbec14146454) than this file: same partition names,
partitions may have moved; the die STA kit-contract check proves the table on the next S81 die proof.
Types with a measured window (per_type_ps or per_port_ps) are untouched.  Values above the schema limit T/4 = 208 ps are
capped at 208 and named in type_window_g50.json capped_at_T4.  Only clock.tap_window per_type_ps + note change.

usage: delta_tapwin_type_1109.py PLAN_JSON [--check]"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NOTE = (" DIE-S81-85 TAPWIN-TYPE-1109 (COORD 2026-11-09): per_type_ps of the 159 formerly unmeasured types = worst per-port"
        " cross-tap window from die_sta_related's chain on the S81 G50 die GRT proof (older plan fbec14146454, TT+FF, ceil"
        " 1 ps, no margin; 5 types capped at T/4 = 208). Replaces the unvalidated 40 ps default; the die STA kit-contract"
        " check proves it on the next S81 die proof.")


def main():
    plan = Path(sys.argv[1])
    s = plan.read_text()
    d = json.loads(s)
    tw = d["clock"]["tap_window"]
    tab = json.loads((HERE / "type_window_g50.json").read_text())["per_type_ps"]
    pt, pp = tw.get("per_type_ps") or {}, tw.get("per_port_ps") or {}
    add = {t: v for t, v in sorted(tab.items()) if t in d["partition_types"] and t not in pt and not pp.get(t)}
    skipped = sorted(set(tab) - set(add))
    i = s.index('  "tap_window": {')
    a = s.index('"per_type_ps": {', i)
    j = s.index('\n   }', a)
    body = ",\n" + ",\n".join(f'    "{t}": {int(v) if float(v).is_integer() else v}' for t, v in add.items())
    s2 = s[:j] + body + s[j:]
    m = re.search(r'(  "tap_window": \{\n   "window_ps": [^\n]*\n   "note": "(?:[^"\\]|\\.)*)(")', s2)
    s2 = s2[:m.end(1)] + NOTE + s2[m.end(1):]
    d2 = json.loads(s2)
    assert d2["clock"]["tap_window"]["per_type_ps"] == {**pt, **add}
    d2["clock"]["tap_window"]["per_type_ps"] = pt
    d2["clock"]["tap_window"]["note"] = tw["note"]
    assert d2 == d, "only per_type_ps + note may change"
    print(f"TAPWIN-TYPE-1109: {len(add)} types added, {len(skipped)} table types skipped (measured or not in this plan)")
    if "--check" not in sys.argv:
        plan.write_text(s2)


if __name__ == "__main__":
    main()
