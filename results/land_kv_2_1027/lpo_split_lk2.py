"""LAND-KV-2: split landed_phase_ocv rows into NOMINAL failures (|d| alone beyond the window) and OCV-ONLY failures
(|d| inside, derated outside), at margin 0 and at the 12.13d 100 ps gate.  lpo_split_lk2.py LPO_JSON [REGIONS_JSON]"""
import json, sys
L = json.load(open(sys.argv[1]))["corners"]
reg = json.load(open(sys.argv[2]))["part_region"] if len(sys.argv) > 2 else None
B = 833.0 / 2
for k in ("TT_droop-regions_corelat250", "FF_droop-regions_corelat202.5"):
    rows = L[k]["all"]
    if reg: rows = [r for r in rows if reg[r["src"]] != reg[r["dst"]]]
    o = dict(crossings=len(rows), worst=min(r["margin_ps"] for r in rows))
    for g in (0, 100):
        f = [r for r in rows if r["margin_ps"] < g]
        nom = [r for r in f if abs(r["d_ps"]) > B - g]
        o[f"fail<{g}"] = len(f); o[f"nominal<{g}"] = len(nom); o[f"ocv_only<{g}"] = len(f) - len(nom)
    root = [r for r in rows if r["lca"] == "b0"]
    o["root_lca"] = len(root); o["root_lca_fail<0"] = sum(r["margin_ps"] < 0 for r in root)
    o["nominal_worst_abs_d"] = max(abs(r["d_ps"]) for r in rows)
    print(k, json.dumps(o))
