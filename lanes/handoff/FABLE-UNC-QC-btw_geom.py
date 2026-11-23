#!/usr/bin/env python3
"""FABLE-UNC-QC STA-BTW-1 geometry: per st_a type, the tail split the bind will make for the cfg bits at pad PAD and the hop lengths
the kit hook (tail_copy_anchor.tcl) gives: bin -> trunk end T (L1 centre of the consumer pins) -> copy stage 1 -> copy stage K at the pin.
usage (cwd = launch tree): btw_geom.py PLAN [PAD]"""
import sys, json, re, math
from pathlib import Path
sys.path.insert(0, "tools/die_plan")
import bind_pad_tail_split as TS
plan = sys.argv[1]; PAD = int(sys.argv[2]) if len(sys.argv) > 2 else 3
raw = json.load(open(plan)); pd = Path(plan).resolve().parent
cfg = dict(min_spread_um=400.0, hop_um=380.0, route=False)
PORTS = [("cfg_kcm1_p", 8, 0), ("cfg_sbase_p", 9, 8), ("cfg_nwords_p", 8, 17), ("cfg_wsrc_p", 1, 25), ("cfg_mode_p", 2, 26), ("cfg_v_p", 1, 28)]
print("type\tK\ttrunk\tS_um\tbin_xy\tT_xy\tbin_to_T\tmax_T_to_pin\tmax_copy_hop\tworst_hop\tcores")
worst = 0
for tn, ty in raw["partition_types"].items():
    if not re.match(r"sl[ew]_st_a", tn): continue
    hcs = ty["hard_cores"]
    for plan_dir in (Path("physical/die_plan/qwen_compute/plan_of_record"), pd, pd.parent):
        tab = TS.pin_table(hcs, plan_dir)
        if any("cfg_kcm1_p" in v for v in tab.values()): break
    boxes = TS.core_boxes(hcs)
    cores = [c for c in tab if "cfg_kcm1_p" in tab[c]]
    rs = ty.get("relay_sites") or {}
    band = (((ty.get("clock") or {}).get("landing_contract") or {}).get("bands") or {}).get("b_tw_data_i", {}).get("rect_um")
    cl = [h for h in hcs if h["inst"] == "cl_b_tw_data_i"]
    res = []
    for pn, w, lo in PORTS:
        for i in range(w):
            j = lo + i
            by = {}
            for c in cores:
                _inst, xy = TS.pin_xy(tab, c, pn, i, w)
                if xy: by[c] = [xy]
            if len(by) < 2: continue
            ks = TS.tail_depth(PAD, by, cfg, boxes)
            if ks is None: res.append((j, None)); continue
            K, Sp = ks
            pts = [p for v in by.values() for p in v]; T = TS.l1_centre(pts)
            src = rs.get(f"u_bin_b_tw_data_i.q[{j}]") or rs.get(f"u_bin_b_tw_data_i/q[{j}]")
            if src is None:
                if cl: src = (cl[0]["origin_um"][0], cl[0]["origin_um"][1] + cl[0]["outline_um"][1] / 2.0)   # W edge of the landing macro
                elif band: src = ((band[0] + band[2]) / 2, (band[1] + band[3]) / 2)
                else: src = (ty["outline_um"][0], sum(b["window_um"][0] + b["window_um"][1] for b in ty["buses"] if b["name"] == "b_tw_data_i") / 2)
            d0 = TS.md(src, T) if PAD > K else 0.0
            tp = max(TS.route_len(T if PAD > K else src, p, boxes)[0] for p in pts)
            res.append((j, K, Sp, src, T, d0, tp))
    ok = [r for r in res if r[1]]
    if not ok: print(tn, "NO SPLIT", len(res)); continue
    K = {r[1] for r in ok}; d0 = max(r[5] for r in ok); tp = max(r[6] for r in ok); ch = tp / max(K)
    w = max(d0 / max(1, PAD - max(K)) if PAD > max(K) else 0, ch); worst = max(worst, w)
    r = ok[0]
    print(f"{tn}\t{sorted(K)}\t{PAD - max(K)}\t{max(x[2] for x in ok):.0f}\t({r[3][0]:.0f},{r[3][1]:.0f})\t({r[4][0]:.0f},{r[4][1]:.0f})\t{d0:.0f}\t{tp:.0f}\t{ch:.0f}\t{w:.0f}\t{len(cores)} bits {len(ok)}/{len(res)}")
print("BTW-GEOM worst hop um", round(worst), "pad", PAD)
