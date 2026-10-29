#!/usr/bin/env python3
"""DIE-QC-25: read a die gate dir (sta_gate / sta_declared die_sta_related.json): intra/seam kit-contract hold plain+OCV,
CA TT/FF, summary verdicts.  usage: read_gate25.py GATE_DIR"""
import json, sys
from pathlib import Path
G = Path(sys.argv[1])
def find(o, key, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            p = f"{path}/{k}"
            if k == key: yield p, v
            yield from find(v, key, p)
    elif isinstance(o, list):
        for i, v in enumerate(o): yield from find(v, key, f"{path}[{i}]")
for run in ("sta_gate", "sta_declared"):
    f = G / run / "die_sta_related.json"
    if not f.exists():
        print(run, "MISSING"); continue
    d = json.loads(f.read_text())
    print("==", run, "gate:", json.dumps(d.get("gate"))[:300])
    for key in ("kit_contract_hold", "kit_contract_hold_ocv"):
        for p, v in find(d, key):
            print(f"  {p}: W {v.get('window_ps')} worst {v.get('worst_hold_bound_ps')} neg {v.get('neg_pairs')} need {v.get('window_needed_ps')} worst {json.dumps(v.get('worst'))[:200]} {v.get('verdict')}")
    print("  summary:", json.dumps(d.get("summary"))[:1500])
    ca = d.get("count_aligned")
    if ca: print("  count_aligned:", json.dumps({k: v for k, v in ca.items() if not isinstance(v, (list, dict)) or k in ("TT", "FF")})[:800])
