#!/usr/bin/env python3
"""DIE-HEAD-51 helper ptw (what-if, no plan commit): HEAD per-type tap window in the DIE-KV-56 form (1589d7e38bf/d230e4b4d9f).
W_t = ceil10(measured nominal single-arrival related-pair kit-contract damage of the type regions + 10), floor = die W,
cap T/4 (208); seam_ps = ceil10(seam damage + 10), sender_ps 0 (S81 form: kit output min delay unchanged).
usage: mk_ptw.py PLAN INTRA_NEED_JSON SEAM_NEED_JSON OUT_DIR [FLOOR_PS]"""
import json, math, sys
from pathlib import Path
plan, ni, ns, out = json.loads(Path(sys.argv[1]).read_text()), json.loads(Path(sys.argv[2]).read_text()), \
    json.loads(Path(sys.argv[3]).read_text()), Path(sys.argv[4])
floor = float(sys.argv[5]) if len(sys.argv) > 5 else 0.0
per = float(plan["die"]["period_ps"]); cap = math.floor(per / 4)
c10 = lambda v: float(math.ceil((v + 10.0) / 10.0) * 10)
rt = {p["name"]: p["type"] for p in plan["partitions"]}
bt, miss = {}, []
for reg, r in ni.items():
    tn = rt.get(reg)
    if tn is None:
        miss.append(reg); continue
    b = bt.setdefault(tn, dict(need_ps=-1e9, worst_region=None, regions=0))
    b["regions"] += 1
    if r["need"] > b["need_ps"]:
        b.update(need_ps=round(r["need"], 2), worst_region=reg, launch=r["launch"], capture=r["capture"])
ptw = {}
for tn, b in sorted(bt.items()):
    w = min(cap, max(floor, c10(b["need_ps"]))) if b["need_ps"] > 0 else floor
    b["W_t"] = w
    if w > floor:
        ptw[tn] = w
sn = max(r["need"] for r in ns.values()); sw = max(ns, key=lambda k: ns[k]["need"])
seam = max(40.0, c10(sn))
P = json.loads(json.dumps(plan)); ck = P["clock"]
note = ("DIE-HEAD-51 ptw WHAT-IF 10-31 (not plan of record): KV-56 form; W_t = ceil10(measured nominal single-arrival "
        f"(clk5 57f441649cf) kit-contract damage of the type regions + 10), floor {floor:g}, cap T/4 {cap}; proof sta/proof_l48c")
ck["tap_window"] = dict(window_ps=floor, note=note, per_type_ps=ptw)
ck["seam_hold"] = dict(sender_ps=0.0, seam_ps=seam, note=f"DIE-HEAD-51 ptw WHAT-IF: seam_ps = ceil10(seam damage {sn:.2f} ({sw}) + 10); "
                       "sender 0 (S81 form): kit output min 0 unchanged, input min -insertion_tol 40 -> -seam_ps")
out.mkdir(parents=True, exist_ok=True)
(out / "plan_ptw.json").write_text(json.dumps(P, indent=1) + "\n")
(out / "need_by_type.json").write_text(json.dumps(dict(sorted(bt.items(), key=lambda kv: -kv[1]["need_ps"])), indent=1) + "\n")
(out / "per_type_ps.json").write_text(json.dumps(dict(per_type_ps=ptw, window_ps=floor, seam_ps=seam, seam_need_ps=round(sn, 2),
                                                      seam_worst=sw, regions_unmapped=miss), indent=1) + "\n")
ws = sorted(ptw.values())
print(f"types {len(bt)} with need, {len(ptw)} windowed, W range {ws[0] if ws else 0:g}-{ws[-1] if ws else 0:g}, seam {seam:g} "
      f"(need {sn:.2f}), unmapped regions {len(miss)} {miss[:5]}")
