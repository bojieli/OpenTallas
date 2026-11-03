"""Summarise prebuild_gate.py results: python3 census_table.py OUT_ROOT [> census.tsv]
one row per OUT_ROOT/<design>/prebuild_gate.json (cells, stage_ps, wns, pin_unreg, largest memory, verdict, needs)."""
import json
import sys
from pathlib import Path

COLS = ["design", "verdict", "sta_stage", "cells", "macros", "wns", "stage_ps", "r2r", "in2reg", "reg2out", "over583",
        "pin_unreg", "mem_max_bits", "reset", "straps_leaked", "needs"]


def row(name, d):
    if not d.get("schema"):
        return {"design": name, "verdict": "RUNNING"}
    c = d["checks"]
    g = d.get("groups") or {}
    sl = lambda k: (g.get(k) or {}).get("slack")
    needs = []
    if d.get("needs_stage_cut"):
        needs.append("STAGE_CUT")
    if c.get("face", {}).get("pin_unreg"):
        needs.append("FACE_REG")
    if not c["cells"]["ok"]:
        needs.append("SPLIT")
    if not c["memory"]["ok"]:
        needs.append("MACRO")
    if not c.get("reset", {}).get("ok", True):
        needs.append("RESET_RELAY")
    if d.get("sta_stage") != "place_resized":
        needs.append("FLOW@" + "/".join(x for x in d.get("flow_status", []) if x.startswith("stop=")))
    return {"design": name, "verdict": d["verdict"], "sta_stage": d.get("sta_stage"), "cells": d.get("cells"),
            "macros": d.get("macros"), "wns": d.get("wns"), "stage_ps": d.get("stage_ps"), "r2r": sl("r2r"),
            "in2reg": sl("in2reg"), "reg2out": sl("reg2out"), "over583": d.get("r2r_endpoints_stage_over_583"),
            "pin_unreg": c.get("face", {}).get("pin_unreg"), "mem_max_bits": c["memory"].get("largest"),
            "reset": "ok" if c.get("reset", {}).get("ok") else ",".join(c.get("reset", {}).get("unregistered", []) or ["?"]),
            "straps_leaked": len(c.get("straps", {}).get("leaked", []) or []), "needs": "+".join(needs) or "-"}


def main(root):
    print("\t".join(COLS))
    for f in sorted(Path(root).glob("*/prebuild_gate.json")):
        try:
            d = json.loads(f.read_text())
        except ValueError:
            d = {}
        r = row(f.parent.name, d)
        print("\t".join("" if r.get(k) is None else str(r.get(k)) for k in COLS))


if __name__ == "__main__":
    main(sys.argv[1])
