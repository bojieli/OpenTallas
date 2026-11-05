#!/usr/bin/env python3
"""HBM-REFORM-B d44v part 21: ot_hbm_idx_selector_static_sel -> ot_hidx_s3_ctl + 4 x ot_hidx_s3_q (proven s3 cluster, flat, kit face shells).
    mk_p21.py pre PLAN_DIR    slot 600.048x450.36 -> 596.16x449.28 (origin kept): mk_split tile edges need the 8.64 lattice
    (mk_split.py PLAN_DIR split_p21.json split_p21)
    mk_p21.py post PLAN_DIR   part21_event.json"""
import json, sys
from pathlib import Path
mode, pd = sys.argv[1], Path(sys.argv[2]); NEW = [596.16, 449.28]; OLD = [600.048, 450.36]; CORE = "ot_hbm_idx_selector_static_sel"
D = json.loads((pd / "die_plan.json").read_text())
rows = [(t, h) for t, ty in D["partition_types"].items() for h in ty.get("hard_cores") or []]
if mode == "pre":
    r = [(t, h) for t, h in rows if h["module"] == CORE]
    if not r or any(h["outline_um"] != OLD for _, h in r): raise SystemExit("selector rows not as read")
    for _, h in r: h["outline_um"] = NEW
    (pd / "die_plan.json").write_text(json.dumps(D, indent=1) + "\n")
    print("part 21 pre:", len(r), "rows", sorted({h.get("orient", "R0") for _, h in r}))
else:
    (pd / "part21_event.json").write_text(json.dumps({"schema": "opentallas.hbm_plan_event.part21", "core": CORE,
        "outline": {"from": OLD, "to": NEW}, "subs": ["ot_hidx_s3_ctl", "ot_hidx_s3_q x4"],
        "unloaded": "clk_mem stays a master port with no load: each SRAM runs on its quadrant clock",
        "cycles": "registered_s3fs: sel_in 7, sel_in_line 3, sel_out 2, sel_choose_rt 6, sel_scan_drain as the q tile (cycles/selector.tsv)"}, indent=1) + "\n")
    print("part 21 post")
