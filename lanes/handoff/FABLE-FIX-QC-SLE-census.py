#!/usr/bin/env python3
"""FABLE-FIX-QC-SLE static census: per-bit internal-station sites (kit is_bits knee model, out bus chains with
bit_route per_bit and no core key) that land inside a hard-core box, per type.  census.py PLAN [TYPE_RE]
Estimator only (never a gate).  Columns: type, chains, sites, sites_in_core (non-landing cores), sites_in_landing, worst_hop_um, detail"""
import json, sys, os, re
from pathlib import Path
HERE = Path(os.environ.get("OT_TOOLS", "/srv/opentallas-scratch2/claude/fable-fix-qc-sle/clone/tools/die_plan"))
sys.path[:0] = [str(HERE), str(HERE.parents[1])]
import schema as S, gen_phys
plan = sys.argv[1]; rx = re.compile(sys.argv[2] if len(sys.argv) > 2 else ".")
raw = json.load(open(plan)); P = S.Plan(raw, path=plan)
def knee(px, py, lx, ly, face, edge, edges, geo, along_first):
    xmin, ymin, xmax, ymax = geo
    if face in "EW":
        normal = max(abs(xmin - lx), abs(xmax - lx)); along = max(abs(ymin - ly), abs(ymax - ly)); cx, cy = lx, py
    else:
        normal = max(abs(ymin - ly), abs(ymax - ly)); along = max(abs(xmin - lx), abs(xmax - lx)); cx, cy = px, ly
    n1, a1 = normal, along
    if along_first:
        cx, cy = (px, ly) if face in "EW" else (lx, py); n1, a1 = along, normal
    first, second, ax, ay, bx, by = a1, n1, lx, ly, px, py
    if first < 1e-8: split, worst = 0, second / edges
    elif second < 1e-8: split, worst = edges, first / edges
    else:
        split, worst = -1, 1e99
        for j in range(1, edges):
            w = max(first / j, second / (edges - j))
            if w < worst: worst, split = w, j
    if edge <= split and split:
        f = edge / split; return (ax + f * (cx - ax), ay + f * (cy - ay)), worst
    f = (edge - split) / (edges - split); return (cx + f * (bx - cx), cy + f * (by - cy)), worst
print("type\tchains\tsites\tin_core\tin_landing\tworst_hop\tdetail")
for tn in sorted(P.types):
    if not rx.search(tn): continue
    t = P.types[tn]
    es = [e for e in t.get("internal_stations", []) if e.get("bit_route") == "per_bit" and e.get("conn", "").startswith("bus:") and not e.get("core") and "leaf_um" in e]
    if not es or not t.get("hard_cores"): continue
    try:
        pins = {}
        for name, bit, _ln, x, y, f in gen_phys.type_pins(P, tn):
            pins.setdefault(name, {})[int(bit)] = (float(x), float(y))
    except Exception as ex:
        print(f"{tn}\tERR {type(ex).__name__} {str(ex)[:80]}"); continue
    boxes = [(c["inst"], c["origin_um"][0], c["origin_um"][1], c["origin_um"][0] + c["outline_um"][0], c["origin_um"][1] + c["outline_um"][1],
              "cland" in c.get("module", "") or c["inst"].startswith("cl_")) for c in t["hard_cores"] if "origin_um" in c and "outline_um" in c]
    buses = {b["name"]: b for b in t["buses"]}
    nch = ns = nc = nl = 0; worst = 0.0; det = []
    for e in es:
        b = buses.get(e["conn"][4:])
        if not b or b["dir"] != "out" or "face" not in b or b["name"] not in pins: continue
        pp = pins[b["name"]]; n = len(e["regs_um"]); lx, ly = e["leaf_um"]
        xs = [p[0] for p in pp.values()]; ys = [p[1] for p in pp.values()]; geo = (min(xs), min(ys), max(xs), max(ys))
        nch += 1; c0 = 0; hit = set()
        for bit, (px, py) in pp.items():
            for k in range(n):
                (x, y), w = knee(px, py, lx, ly, b["face"], k + 1, n + 1, geo, e.get("leg_order") == "along_first"); worst = max(worst, w); ns += 1
                for nm, x0, y0, x1, y1, land in boxes:
                    if x0 + 0.5 < x < x1 - 0.5 and y0 + 0.5 < y < y1 - 0.5:
                        if land: nl += 1
                        else: nc += 1; c0 += 1; hit.add(nm)
        if c0: det.append(f"{b['name']}:{c0}@{'+'.join(sorted(hit))}")
    print(f"{tn}\t{nch}\t{ns}\t{nc}\t{nl}\t{worst:.0f}\t{' '.join(det)}", flush=True)
