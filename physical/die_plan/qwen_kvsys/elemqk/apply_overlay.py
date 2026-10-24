"""ELEM-QK: plan COPY with macro_overlay.json applied (contents_add per type).  python3 apply_overlay.py PLAN OVERLAY OUT"""
import json
import sys
p = json.load(open(sys.argv[1]))
ov = json.load(open(sys.argv[2]))
for t, d in ov["types"].items():
    p["partition_types"][t].setdefault("contents", []).extend(d.get("contents_add", []))
p["note"] = p.get("note", "") + " | ELEM-QK kit copy: " + ov["note"]
json.dump(p, open(sys.argv[3], "w"), indent=1)
