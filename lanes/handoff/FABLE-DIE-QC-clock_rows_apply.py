#!/usr/bin/env python3
"""FABLE-DIE-QC: apply the die clock rows file to a plan (rows only).  Refuses when a type's clock port set (plan
clock.tap_offset.per_port_ps keys = the kit clock ports of the proof) differs from the rows: then the die clock must be
re-run on that plan.  usage: clock_rows_apply.py PLAN ROWS.json[.gz] OUT [--allow-missing-types]"""
import json, sys, gzip
plan, rows, out = sys.argv[1:4]
R = json.load(gzip.open(rows, "rt") if rows.endswith(".gz") else open(rows)); P = json.load(open(plan)); c = P["clock"]
old = c["tap_offset"]["per_port_ps"]; bad = []
for tn in P["partition_types"]:
    if tn not in R["tap_offset_per_port_ps"]: bad.append(f"{tn}: type not in the rows"); continue
    if tn in old and set(old[tn]) != set(R["tap_offset_per_port_ps"][tn]) and set(R["tap_offset_per_port_ps"][tn]) - set(old[tn]) - set(R["new_ports"].get(tn, [])):
        bad.append(f"{tn}: clock ports differ from the proof")
if bad and "--allow-missing-types" not in sys.argv:
    sys.exit("REFUSED, re-run the die clock on this plan:\n  " + "\n  ".join(bad[:20]))
c["tap_offset"]["per_port_ps"] = R["tap_offset_per_port_ps"]; c["tap_offset"]["source"] = R["source"]
c["tap_window"]["per_port_ps"] = R["tap_window_per_port_ps"]; c["seam_hold"]["seam_ps"] = max(c["seam_hold"]["seam_ps"], R["seam_ps"])
json.dump(P, open(out, "w"), separators=(",", ":")); print("applied", len(R["tap_offset_per_port_ps"]), "types; changed", len(R["types_changed"]))
