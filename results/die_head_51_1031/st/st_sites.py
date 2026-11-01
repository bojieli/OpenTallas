#!/usr/bin/env python3
"""DIE-HEAD-51 helper st: site check + snap of the l48w-st stage buffers (entry/chain/pin) on the SAME die_trial clock
SiteMap the l48c tree cells use (clock_site with DME actual_max -> native body offsets; core halo, PHY, outside-partition
forbidden), plus overlap vs tree cells / other stage buffers.  Illegal cells slide back along their own incoming leg
(SiteMap.slide toward the upstream cell), else SiteMap.nearest; then row/site snap with start_stage_emit.place_stage.
usage: st_sites.py PLAN PATCH_DIR SSE_DIR OUT_DIR [ACTUAL_MAX_UM]"""
import json, math, re, sys
from pathlib import Path
plan, pdir, sse, out = sys.argv[1:5]; amax = float(sys.argv[5]) if len(sys.argv) > 5 else 405.0
sys.path.insert(0, sse)
import die_trial as T, schema as S, start_stage_emit as E
T.DME_ACTUAL_MAX_UM = amax
P = S.Plan(S.load(plan), Path(plan)); site = T.clock_site(P)
pdir, out = Path(pdir), Path(out); out.mkdir(parents=True, exist_ok=True)
doc = json.loads((pdir / "start_stages_l48w_st.json").read_text()); st = doc["stages"]
ct = (pdir / "ctree.tcl").read_text(); cv = (pdir / "ctree.v").read_text()
loc = {m[1]: (float(m[2]), float(m[3])) for m in re.finditer(r"place_inst -name (\S+) -location \{([\d.]+) ([\d.]+)\}", ct)}
BW, CW = 0.648, E.CLK_CELL_W_UM
mine = {}; fwd = {}
for s in st:
    seq = [s["entry_buffer"]["inst"]] + [c["inst"] for c in s.get("chain", ())]
    up = [tuple(s["node_xy_um"])] + [tuple(loc[q]) for q in seq[:-1]]
    dn = [tuple(loc[q]) for q in seq[1:]] + [tuple(s["clock_pin_xy_um"])]
    for q, u, d in zip(seq, up, dn):
        mine[q] = u; fwd[q] = d
tree = {k: v for k, v in loc.items() if k not in mine}
rows = E.Rows()
for k, (x, y) in tree.items():
    rows.add(x, x + CW, y)
ill = {"core": 0, "phy": 0, "keepout": 0, "outside": 0}; ovl = 0; moved = []; new = {}
for q in sorted(mine, key=lambda q: (loc[q][1], loc[q][0])):     # stage-buffer overlap vs tree + earlier buffers
    x, y = loc[q]; w = T.ISLAND_CELL_UM
    why = site.why((x, y))
    if why:
        ill[why] = ill.get(why, 0) + 1
    if not rows.free(x, x + BW, y):
        ovl += 1
    p = (x, y)
    if why:
        cand = [c for c in (site.slide(p, mine[q]), site.slide(p, fwd[q])) if c is not None]   # die_trial: nearer of back/forward leg slides
        p = min(cand, key=lambda c: abs(c[0] - x) + abs(c[1] - y)) if cand else site.nearest(p)
    py = round(round(p[1] / E.ROW_UM) * E.ROW_UM, 3); px = round(round(p[0] / 0.054) * 0.054, 3)
    if not why and rows.free(px, px + BW, py):
        r = (px, py)
    else:
        r = None
        for k in range(E.MAX_ROW_TRIES):                          # nearest free legal row slot around p
            for dy in ((0.0,) if k == 0 else (k * E.ROW_UM, -k * E.ROW_UM)):
                for dx in (0.0, 0.648, -0.648, 1.296, -1.296, 2.592, -2.592):
                    c = (round(px + dx, 3), round(py + dy, 3))
                    if site.legal(c) and rows.free(c[0], c[0] + BW, c[1]):
                        r = c; break
                if r: break
            if r: break
        if r is None:
            raise SystemExit(f"{q}: no legal free slot near {p}")
    rows.add(r[0], r[0] + BW, r[1]); new[q] = r
    d = abs(r[0] - x) + abs(r[1] - y)
    if d > 1e-6:
        moved.append((round(d, 2), q, why))
moved.sort(reverse=True)
tree_ill = sum(1 for k, v in tree.items() if site.why(v))
t2 = ct
for q, (x, y) in new.items():
    t2 = re.sub(rf"(place_inst -name {re.escape(q)} -location \{{)[\d.]+ [\d.]+(\}})", lambda m: f"{m[1]}{x:.3f} {y:.3f}{m[2]}", t2)
(out / "ctree.tcl").write_text(t2); (out / "ctree.v").write_text(cv)
for s in st:
    s["entry_buffer"]["xy_um"] = list(new[s["entry_buffer"]["inst"]])
    for c in s.get("chain", ()):
        c["xy_um"] = list(new[c["inst"]])
(out / "start_stages_l48w_st.json").write_text(json.dumps(doc, indent=1) + "\n")
rep = dict(stage_buffers=len(mine), illegal=ill, overlaps=ovl, moved=len(moved), moved_gt_2um=sum(m[0] > 2 for m in moved),
           max_move_um=moved[0][0] if moved else 0, worst=moved[:8], tree_cells=len(tree), tree_cells_illegal_same_check=tree_ill)
(out / "sites_report.json").write_text(json.dumps(rep, indent=1) + "\n"); print(json.dumps(rep))
