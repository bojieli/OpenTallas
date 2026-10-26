#!/usr/bin/env python3
"""QC-SU-KITS (COORD MASTER-PLAN-R5 ruling (c) 12:58): pre-kit PLAN GATE for the adopted unequal-fanout SU core trees.

Runs the MASTER-PLAN-R5 plan model (results/master_plan_r5/su_unequal/su_tree_uf.py, unchanged, KMIN=KMAX=adopted k) and
adds the checks the ruling requires before any kit is generated:
  G1 macro_orient : every plan macro rect matches the LEF SIZE in an orientation the LEF SYMMETRY allows
                    (R90/R270 need "SYMMETRY ... R90"; FinFET macros never rotate against the std-cell poly direction).
  G2 island_rows  : each island = 8.64 um square on the 4.32 PG lattice containing the plan island point; legal for std-cell
                    rows: inside the core rows, row/site aligned, outside every macro ROW halo (kit MACRO_ROWS_HALO 4.32, not
                    the 2.2 um wire halo of the maze), no overlap with the entry island or another island.
  G3 cell_rows    : every B / leaf driver site outside the macro row halo and inside the core rows.
  G4 detour_sites : every tree edge gets an explicit legal wire path of EXACTLY its level length T (shortest maze path or a
                    single-waypoint detour on the same maze), and its K-1 repeaters at the equal cuts j*T/K; each repeater
                    snapped along the path to the nearest row-legal site (shift reported, <= 2.16 um allowed).
                    r3 (COORD 13:5x, QC-SU-KITS-2 prog4b MIF0 measured TT 213.4 vs gate 248.6: 85/89 detour edges had no
                    cell, the router shortcut them): an edge PASSES only if its planned length is FIXED BY PLACED CELLS --
                    the sum of shortest legal maze segments between consecutive placed cells (driver -> repeaters -> child)
                    >= planned length - 2.16 um.  Planner: a detour waypoint must coincide with one of the edge's equal
                    cuts and carry that cut's repeater (a level with detours and 0 repeaters gets 1 repeater on EVERY edge
                    of the level, same stage count per path); an edge with no such waypoint is drawn STRAIGHT (shortest)
                    and timed so.  --legacy-paths = the r1 planner under the r3 check (shows the r1 failure).
  P  asbuilt      : r3 gating predictor = uf_asbuilt.py (QC-SU-KITS-2 r2, claude/qc-su-kits2-1026@97a6150209) on the G2/G4
                    cells: shortest segment between consecutive placed cells, unequal-branch loads; PASS iff TT mean within
                    250 +- 20, TT and FF windows <= 20 (with the 12.8c entry trunk when --trunk is given).
  T  entry_trunk  : (optional, 12.8c) fixed entry trunk chain computed from geometry + NLDM to bring the TT mean to the
                    common target; re-predicts TT/FF with the trunk.
Model + offset used for every prediction (COORD 12:59 ruling 4): su_tree_uf raw liberty NLDM + setRC x 0.8/0.9 Elmore, then
MODEL-REFIT su_tree_model_nldm offsets TT +1.9 / FF -5.1 (930fa9628d, one point; COORD 13:1x correction: the earlier
+13/+24.5 had the wrong sign and model). PLAN MODEL, UNCHECKED.
usage: su_kit_gate.py NAME GEO K LIBDIR UF_PY LEFDIR OUT.json [--trunk TARGET_TT] [--legacy-paths] [--asbuilt UF_ASBUILT_PY]
"""
import subprocess
import hashlib
import json
import math
import os
import runpy
import sys
from pathlib import Path


def _sha(p):
    try:
        return hashlib.sha256(Path(p).read_bytes()).hexdigest()
    except OSError:
        return None


PROV = dict(argv=[sys.executable] + list(sys.argv), cwd=os.getcwd(), script_sha256=_sha(__file__))

name, geo, K, libdir, uf_py, lefdir, out = sys.argv[1:8]
trunk_target = float(sys.argv[sys.argv.index("--trunk") + 1]) if "--trunk" in sys.argv else None
LEGACY = "--legacy-paths" in sys.argv
STRAIGHT = set(sys.argv[sys.argv.index("--straight") + 1].split(",")) if "--straight" in sys.argv else set()
asb_py = sys.argv[sys.argv.index("--asbuilt") + 1] if "--asbuilt" in sys.argv else str(Path(__file__).parent / "uf_asbuilt.py")
LEN_TOL = 2.16     # r3: the router may not shortcut a planned edge by more than this
K = int(K)
OFF = {"TT": 1.9, "FF": -5.1}   # MODEL-REFIT 930fa9628d PLAN_TREE_OFFSETS["su_tree_model_nldm"] (one point, btab R5)
ROW_H, SITE_W, LAT, ISL, ROW_HALO = 0.27, 0.054, 4.32, 8.64, 4.32
TOL_SHIFT = 2.16   # along the path, else beside it (Manhattan radius)

sys.argv = [uf_py, geo, "/dev/null", "100", str(K), str(K), "64", libdir]
g = runpy.run_path(uf_py, run_name="su_tree_uf")
best = g["best"]
core, macros, entry = g["core"], g["macros"], g["entry"]
G, NX, NY, W, blk = g["G"], g["NX"], g["NY"], g["W"], g["blk"]
bfs, cell, xy, md = g["bfs"], g["cell"], g["xy"], g["md"]
PIN_COLS = g.get("PIN_COLS", [])     # su_tree_uf_pc.py: SRAM clock-pin columns (node keepout)


def in_pincol(x, y):
    return any(q[0] <= x <= q[2] and q[1] <= y <= q[3] for q in PIN_COLS)
rep = dict(name=name, geo=geo, k=K, model="su_tree_uf raw NLDM+setRC0.8/0.9 Elmore + master_plan.plan_tree_insertion("
           "su_tree_model_nldm) offset TT+1.9/FF-5.1 (claude/model-refit-1026@930fa9628d; one calibration point, btab R5)", plan_pred_raw=best["pred"],
           plan_pred=dict((c, dict(mean=round(best["pred"][c]["mean"] + OFF[c], 2), window=best["pred"][c]["window"]))
                          for c in ("TT", "FF")), gates={})
_lefs = sorted({line.split()[2] for line in open(geo) if line.startswith("MACRO")})
rep["provenance"] = dict(PROV, inputs=dict(
    {p: _sha(p) for p in (geo, uf_py, str(Path(uf_py).parent / "lib.py"), str(Path(libdir) / "invbuf_tt.lib"),
                          str(Path(libdir) / "invbuf_ff.lib"))},
    **{str(Path(lefdir) / m / f"{m}.lef"): _sha(Path(lefdir) / m / f"{m}.lef") for m in _lefs}),
    note="re-run = provenance.argv from provenance.cwd; every input listed with its sha256")


def in_rowhalo(x, y, pad=0.0):
    for _, r in macros:
        if r[0] - ROW_HALO - pad < x < r[2] + ROW_HALO + pad and r[1] - ROW_HALO - pad < y < r[3] + ROW_HALO + pad:
            return True
    return False


def rect_hits_rowhalo(R):
    for _, r in macros:
        if R[0] < r[2] + ROW_HALO and R[2] > r[0] - ROW_HALO and R[1] < r[3] + ROW_HALO and R[3] > r[1] - ROW_HALO:
            return True
    return False


def in_core(x, y):
    return core[0] <= x <= core[2] and core[1] <= y <= core[3]


# ---- G1 macro orientation vs LEF symmetry
g1 = []
for line in open(geo):
    f = line.split()
    if f and f[0] == "MACRO":
        inst, master = f[1], f[2]
        w, h = float(f[5]) - float(f[3]), float(f[6]) - float(f[4])
        lef = Path(lefdir) / master / f"{master}.lef"
        txt = lef.read_text()
        sz = txt.split("SIZE", 1)[1].split(";")[0].split()
        lw, lh = float(sz[0]), float(sz[2])
        sym = txt.split("SYMMETRY", 1)[1].split(";")[0].split()
        rot = abs(w - lw) > 0.01 or abs(h - lh) > 0.01
        rot_ok = abs(w - lh) < 0.01 and abs(h - lw) < 0.01
        ok = (not rot) or (rot_ok and "R90" in sym)
        g1.append(dict(inst=inst, master=master, plan_wh=[round(w, 3), round(h, 3)], lef_wh=[lw, lh], symmetry=sym,
                       needs_rotation=rot, ok=ok))
rep["gates"]["G1_macro_orient"] = dict(verdict="PASS" if all(m["ok"] for m in g1) else "FAIL", macros=g1)

# ---- G2 islands on the 4.32 lattice, legal for std-cell rows
ent_isl = [math.floor(entry[0] / LAT) * LAT, math.floor(entry[1] / LAT) * LAT]
ent_isl = [ent_isl[0] - LAT if entry[0] - ent_isl[0] < LAT / 2 else ent_isl[0],
           ent_isl[1] - LAT if entry[1] - ent_isl[1] < LAT / 2 else ent_isl[1]]
ent_rect = [ent_isl[0], ent_isl[1], ent_isl[0] + ISL, ent_isl[1] + ISL]


def overlap(a, b):
    return a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]


def row_ok(R):
    return (abs(((R[1] - core[1]) / ROW_H) - round((R[1] - core[1]) / ROW_H)) < 1e-6
            and abs(((R[0] - core[0]) / SITE_W) - round((R[0] - core[0]) / SITE_W)) < 1e-6
            and R[0] >= core[0] - 1e-6 and R[1] >= core[1] - 1e-6 and R[2] <= core[2] + 1e-6 and R[3] <= core[3] + 1e-6)


isl_rects, g2 = [], []
for qi, p in enumerate(best["islands"]):
    cands = []
    for i in range(-3, 4):
        for j in range(-3, 4):
            x0 = (math.floor(p[0] / LAT) + i) * LAT
            y0 = (math.floor(p[1] / LAT) + j) * LAT
            R = [round(x0, 3), round(y0, 3), round(x0 + ISL, 3), round(y0 + ISL, 3)]
            legal = row_ok(R) and not rect_hits_rowhalo(R) and not overlap(R, ent_rect) and \
                not any(overlap(R, q) for q in PIN_COLS) and \
                not any(overlap(R, o) for o in isl_rects)
            c = ((R[0] + R[2]) / 2, (R[1] + R[3]) / 2)
            cands.append((not legal, abs(c[0] - p[0]) + abs(c[1] - p[1]), R, legal))
    cands.sort(key=lambda t: (t[0], t[1]))
    _, disp, R, legal = cands[0]
    contains = R[0] <= p[0] <= R[2] and R[1] <= p[1] <= R[3]
    isl_rects.append(R)
    g2.append(dict(island=f"Q{qi}", plan_xy=p, rect_um=R, centre_disp_um=round(disp, 2), contains_plan_point=contains,
                   legal=legal))
rep["gates"]["G2_island_rows"] = dict(verdict="PASS" if all(i["legal"] for i in g2) else "FAIL", entry_island=ent_rect,
                                      islands=g2, max_disp_um=max(i["centre_disp_um"] for i in g2))


def cell_legal(x, y):
    return in_core(x, y) and not in_rowhalo(x, y) and not in_pincol(x, y) and \
        not any(R[0] <= x <= R[2] and R[1] <= y <= R[3] for R in isl_rects)


# ---- G3 B / leaf driver sites
bad = []
for kind, sites in (("B", best["B_sites"]), ("leaf", best["leaf_sites"])):
    for nm, (x, y) in sites.items():
        if not (in_core(x, y) and not in_rowhalo(x, y)):
            bad.append(dict(kind=kind, node=nm, xy=[x, y]))
rep["gates"]["G3_cell_rows"] = dict(verdict="PASS" if not bad else "FAIL", n_sites=len(best["B_sites"]) + len(best["leaf_sites"]),
                                    illegal=bad)

# ---- G4 explicit detour paths + repeater sites
T = best["level_len_um"]
Kr = best["repeaters_per_edge"]
ent = cell(entry)
islc = [cell(tuple(p)) for p in best["islands"]]
Bc = {k_: cell(tuple(v)) for k_, v in best["B_sites"].items()}
Lc = {k_: cell(tuple(v)) for k_, v in best["leaf_sites"].items()}
edges = [("L1", f"Q{q}", ent, islc[q]) for q in range(len(islc))]
edges += [("L2", k_, islc[int(k_[1:].split("B")[0])], v) for k_, v in Bc.items()]
edges += [("L3", k_, Bc[k_.rsplit("L", 1)[0]], v) for k_, v in Lc.items()]
levT = {"L1": T["T1"], "L2": T["T2"], "L3": T["T3"]}
levK = {"L1": Kr["K1"] + 1, "L2": Kr["K2"] + 1, "L3": Kr["K3"] + 1}
levK_plan = dict(levK)


def walk(D, start):
    """cells from start down the BFS gradient of D to its source."""
    path = [start]
    u = start[0] * W + start[1]
    while D[u] > 0:
        i, j = divmod(u, W)
        for v, ok in ((u + W, i < NX), (u - W, i > 0), (u + 1, j < NY), (u - 1, j > 0)):
            if ok and D[v] == D[u] - 1:
                u = v
                break
        path.append(divmod(u, W))
    return path


g4, edge_paths = [], {}
if not LEGACY:      # r3: a level with any detour and no repeater gets ONE repeater on every edge (equal stage count)
    for lev in ("L1", "L2", "L3"):
        if lev not in STRAIGHT and levK[lev] == 1 and any(round(levT[l_] / G) > bfs(a_)[b_[0] * W + b_[1]] for l_, _, a_, b_ in edges
                                  if l_ == lev):
            levK[lev] = 2


def seg_sum(cells_):
    return sum(md(p, q) for p, q in zip(cells_, cells_[1:]))


for lev, nm, a, b in edges:
    Da, Db = bfs(a), bfs(b)
    need = round(levT[lev] / G)
    short = Da[b[0] * W + b[1]]
    if short < 0:
        g4.append(dict(edge=nm, level=lev, ok=False, why="unreachable"))
        continue
    if need < short:
        g4.append(dict(edge=nm, level=lev, ok=False, why=f"shortest {short*G:.2f} > T {levT[lev]}"))
        continue
    mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    wbest = None
    straight = False
    cut_at_w = None
    if need == short:
        wbest = a
    elif not LEGACY and lev in STRAIGHT:     # r3 option: the whole level drawn straight (no detour at all)
        straight, wbest = True, a
    elif not LEGACY:
        # r3: the waypoint must sit ON an equal cut (its repeater pins the detour), at a row-legal site
        cuts_ = {round(jj * need / levK[lev]): jj for jj in range(1, levK[lev])}
        for i in range(NX + 1):
            base = i * W
            for j in range(NY + 1):
                da = Da[base + j]
                if da < 0 or da not in cuts_:
                    continue
                db = Db[base + j]
                if db < 0 or da + db not in (need, need + 1) or not cell_legal(*xy((i, j))):
                    continue
                d = abs(i - mid[0]) + abs(j - mid[1])
                if wbest is None or d < wbest[0]:
                    wbest = (d, (i, j), cuts_[da])
        if wbest is None:
            straight, wbest = True, a          # no pinnable detour: draw straight, timed as built
        else:
            cut_at_w, wbest = wbest[2], wbest[1]
    else:
        for i in range(NX + 1):
            base = i * W
            for j in range(NY + 1):
                da = Da[base + j]
                if da < 0:
                    continue
                db = Db[base + j]
                if db < 0 or da + db not in (need, need + 1):   # grid parity: +1 step (0.54 um) allowed
                    continue
                d = abs(i - mid[0]) + abs(j - mid[1])
                if wbest is None or d < wbest[0]:
                    wbest = (d, (i, j))
        wbest = wbest[1] if wbest else None
    if wbest is None:
        g4.append(dict(edge=nm, level=lev, ok=False, why="no single-waypoint detour of length T"))
        continue
    p1 = list(reversed(walk(Da, wbest)))          # a -> w
    p2 = walk(Db, wbest)[1:]                       # w -> b
    path = p1 + p2
    nrep = levK[lev] - 1
    reps, okall, maxshift = [], True, 0.0
    for jj in range(1, nrep + 1):
        idx = round(jj * (len(path) - 1) / levK[lev])
        if jj == cut_at_w:                          # the pinning repeater sits exactly on the waypoint
            idx = len(p1) - 1
        found = None
        for s in range(0, int(TOL_SHIFT / G) + 1):
            for t_ in (idx - s, idx + s):
                if 0 <= t_ < len(path):
                    x, y = xy(path[t_])
                    if cell_legal(x, y):
                        found = (s * G, [x, y], t_)
                        break
            if found:
                break
        if not found:                                   # beside the wire: nearest row-legal site within TOL_SHIFT
            cx, cy = xy(path[idx])
            st = int(TOL_SHIFT / G)
            for rr in range(1, st + 1):
                for di in range(-rr, rr + 1):
                    for dj in (rr - abs(di), -(rr - abs(di))):
                        x, y = round(cx + di * G, 3), round(cy + dj * G, 3)
                        if cell_legal(x, y) and found is None:
                            found = (rr * G, [x, y], idx)
                if found:
                    break
        if not found:
            okall = False
            reps.append(dict(cut=jj, xy=list(xy(path[idx])), legal=False))
        else:
            maxshift = max(maxshift, found[0])
            reps.append(dict(cut=jj, xy=found[1], shift_um=round(found[0], 2), legal=True))
    edge_paths[nm] = [list(xy(c_)) for c_ in path[::4]] + [list(xy(path[-1]))]
    plen = (len(path) - 1) * G
    chain = [a] + [cell(tuple(rp["xy"])) for rp in reps] + [b]
    fixed = seg_sum(chain)
    len_fixed = fixed >= plen - LEN_TOL
    g4.append(dict(edge=nm, level=lev, ok=okall and len_fixed, len_um=round(plen, 2), T_um=levT[lev],
                   shortest_um=round(short * G, 2), detour=(need > short) and not straight, straight=straight,
                   cells_fixed_len_um=round(fixed, 2), length_fixed=len_fixed, pin_cut=cut_at_w,
                   repeaters=reps, max_shift_um=round(maxshift, 2)))
rep["gates"]["G4_detour_sites"] = dict(
    verdict="PASS" if all(e["ok"] for e in g4) else "FAIL", n_edges=len(g4),
    planner="r1 (legacy waypoint, no pinning cell)" if LEGACY else "r3 (waypoint on an equal cut, pinned by its repeater)",
    straight_levels=sorted(STRAIGHT),
    repeaters_per_edge_plan={l_: v - 1 for l_, v in levK_plan.items()}, repeaters_per_edge={l_: v - 1 for l_, v in levK.items()},
    n_straight=sum(1 for e in g4 if e.get("straight")),
    n_length_not_fixed=sum(1 for e in g4 if e.get("length_fixed") is False),
    length_rule=f"planned length fixed by placed cells: sum of shortest segments between consecutive cells >= len - {LEN_TOL}",
    n_repeaters=sum(len(e.get("repeaters", [])) for e in g4), n_detours=sum(1 for e in g4 if e.get("detour")),
    max_shift_um=max([e.get("max_shift_um", 0) for e in g4] or [0]), failures=[e for e in g4 if not e["ok"]], edges=g4)
rep["edge_paths_um"] = edge_paths

# ---- G5 SRAM structure (COORD addendum, GEOM-REVIEW-4): no plan node in an SRAM clock-pin column, no leg across an SRAM
g5_nodes = [("island", f"Q{i['island'][1:]}", ((i["rect_um"][0] + i["rect_um"][2]) / 2, (i["rect_um"][1] + i["rect_um"][3]) / 2))
            for i in g2]
g5_nodes += [("B", k_, tuple(v)) for k_, v in best["B_sites"].items()]
g5_nodes += [("leaf", k_, tuple(v)) for k_, v in best["leaf_sites"].items()]
g5_nodes += [("rep", f"{e['edge']}_r{j}", tuple(rp["xy"])) for e in g4 for j, rp in enumerate(e.get("repeaters", []))]
in_col = [dict(kind=k_, node=n_, xy=[round(p[0], 3), round(p[1], 3)]) for k_, n_, p in g5_nodes if in_pincol(*p)]
across = []
for e_, pts in edge_paths.items():
    for p in pts:
        if any(r[0] < p[0] < r[2] and r[1] < p[1] < r[3] for _, r in macros):
            across.append(dict(edge=e_, xy=p))
            break
rep["gates"]["G5_sram_structure"] = dict(
    verdict="PASS" if PIN_COLS and not in_col and not across else "FAIL", pin_columns_um=[[round(v, 3) for v in q] for q in PIN_COLS],
    pin_column_rule="15.12 um (3.5 PG pitches) beside each SRAM clock-pin face, macro height +- 4.32 row halo",
    nodes_checked=len(g5_nodes), nodes_in_pin_column=in_col, legs_across_sram=across,
    note="legs are maze paths (macros + 2.2 um halo blocked) -> they run in the gaps between SRAMs" if PIN_COLS else
    "UF_PY without PIN_COLS (use su_tree_uf_pc.py)")

# ---- P as-built predictor (r3 gating predictor): uf_asbuilt on this gate's cells
Path(out).write_text(json.dumps(rep, indent=1))
asb_out = str(Path(out).with_suffix("")) + ".asbuilt"
subprocess.run([sys.executable, asb_py, geo, str(K), libdir, uf_py, out, asb_out], check=True,
               stdout=open(asb_out + ".log", "w"), stderr=subprocess.STDOUT)
abj = json.loads(Path(asb_out + ".json").read_text())
ab = abj["asbuilt"]
el = abj["early_late"]
rep["asbuilt"] = dict(json=asb_out + ".json", json_sha256=_sha(asb_out + ".json"), spec=asb_out + ".tcl",
                      spec_sha256=_sha(asb_out + ".tcl"), TT=ab["TT"], FF=ab["FF"], early_late=el,
                      predictor_provenance=abj["provenance"])
base_raw = {c_: ab[c_]["mean_raw"] for c_ in ("TT", "FF")}


def p_verdict(tt, wtt, wff):
    return "PASS" if abs(tt - 250.0) <= 20.0 and wtt <= 20.0 and wff <= 20.0 else "FAIL"


# NUMBER-CHECK-3: FF gated on EARLY arrival (separate rise/fall propagation); late reported
rep["gates"]["P_asbuilt"] = dict(verdict=p_verdict(ab["TT"]["mean"], ab["TT"]["window"], el["FF"]["early"]["window"]),
                                 TT=ab["TT"], FF=ab["FF"], FF_early=el["FF"]["early"], FF_late=el["FF"]["late"],
                                 TT_early=el["TT"]["early"], TT_late=el["TT"]["late"],
                                 band="TT mean 250 +- 20 (rise/fall-average model), TT window <= 20, FF EARLY window <= 20")

# ---- T entry trunk (12.8c): fixed chain entry -> trunk -> level-1 driver, sized from geometry + NLDM before build
if trunk_target is not None:
    LIBS, level_chain, stage = g["LIBS"], g["level_chain"], g["stage"]
    TRUNK = ["BUFx4_ASAP7_75t_R", "BUFx6f_ASAP7_75t_R", "BUFx8_ASAP7_75t_R"]
    for corner in ("TT", "FF"):          # same liberty files as the plan model; mutates the model's shared LIBS dict
        LIBS[corner].update(g["lib"].cells(str(Path(libdir) / f"invbuf_{corner.lower()}.lib"), TRUNK))
    BIG, REP = g["BIG"], g["REP"]
    # trunk lies in the 21.6-um centre gap beside the entry island: n stages of cell X, equal wire w each, last drives BIG
    gap_len = 2 * 4.32 * 5          # straight N-S run available in the gap next to the entry island (plan: >= 43.2 um)
    raw_tt = base_raw["TT"]                       # r3: trunk sized on the AS-BUILT prediction
    want = trunk_target - OFF["TT"] - raw_tt
    tgt = {"TT": trunk_target, "FF": 202.5}           # 12.3 common latency TT 250 / FF 202.5, both corners in band
    choices = []
    for cname in ("BUFx4_ASAP7_75t_R", "BUFx6f_ASAP7_75t_R", "BUFx8_ASAP7_75t_R"):
        for n in range(1, 9):
            for w10 in range(5, 61, 5):
                w = w10 / 1.0
                if n * w > gap_len:
                    continue
                dl = {}
                for corner in ("TT", "FF"):
                    L = LIBS[corner]
                    if cname not in L:
                        dl = None
                        break
                    s, t = 20.0, 0.0
                    for i in range(n):
                        cp = L[cname]["cin"] if i < n - 1 else L[BIG]["cin"]
                        d, s = stage(corner, cname, s, 1, w, cp)
                        t += d
                    # the trunk replaces the 20 ps ideal entry slew into BIG: first-order, the level-1 delay change
                    # from the new input slew s is evaluated with the same chain model
                    t1a, _ = level_chain(corner, BIG, 20.0, best["k"], best["level_len_um"]["T1"],
                                         best["repeaters_per_edge"]["K1"] + 1, L[BIG]["cin"])
                    t1b, _ = level_chain(corner, BIG, s, best["k"], best["level_len_um"]["T1"],
                                         best["repeaters_per_edge"]["K1"] + 1, L[BIG]["cin"])
                    dl[corner] = t + (t1b - t1a)
                if dl is None:
                    break
                err = max(abs(base_raw[c_] + dl[c_] + OFF[c_] - tgt[c_]) for c_ in ("TT", "FF"))
                choices.append((err, n, cname, w, dl))
    err0 = max(abs(base_raw[c_] + OFF[c_] - tgt[c_]) for c_ in ("TT", "FF"))
    if choices and min(t[0] for t in choices) >= err0:      # r3: pad up only when the trunk brings the means closer
        rep["entry_trunk"] = dict(cell=None, stages=0, max_err_ps=round(err0, 2),
                                  note="no trunk: the as-built means are already nearest the targets without one")
        choices = []
        rep["_no_trunk"] = True
    if choices:
        choices.sort(key=lambda t: (round(t[0], 1), t[1], t[3]))
        _, n, cname, w, dl = choices[0]
        rep["entry_trunk"] = dict(objective="min over chains of max(|TT-250|, |FF-202.5|) (predicted means)",
                                  max_err_ps=round(choices[0][0], 2), rule="12.8c designed fixed trunk at the entry, same chain every instance, computed from "
                                  "plan geometry + NLDM before build (12.8 d1); no measured input",
                                  target_tt=trunk_target, need_raw_ps=round(want, 2), cell=cname, stages=n, wire_um_each=w,
                                  run="N-S in the centre gap from the entry island", added_raw=dict(
                                      TT=round(dl["TT"], 2), FF=round(dl["FF"], 2)),
                                  pred_with_trunk=dict((c, dict(
                                      mean=round(base_raw[c] + dl[c] + OFF[c], 2),
                                      window=ab[c]["window"])) for c in ("TT", "FF")),
                                  note="first-order: trunk delay added to the as-built leaf arrivals (same chain every leaf)")
        pw = rep["entry_trunk"]["pred_with_trunk"]
        rep["gates"]["P_asbuilt"].update(verdict=p_verdict(pw["TT"]["mean"], pw["TT"]["window"], el["FF"]["early"]["window"]),
                                         with_trunk=pw)
    elif not rep.pop("_no_trunk", False):
        rep["entry_trunk"] = dict(error="no trunk cell in liberty set")

rep["verdict"] = "PASS" if all(v["verdict"] == "PASS" for v in rep["gates"].values()) else "FAIL"
Path(out).write_text(json.dumps(rep, indent=1))
print(name, "VERDICT", rep["verdict"], {k_: v["verdict"] for k_, v in rep["gates"].items()})
print(" pred", rep["plan_pred"], "trunk", rep.get("entry_trunk", {}).get("pred_with_trunk"),
      rep.get("entry_trunk", {}).get("cell"), rep.get("entry_trunk", {}).get("stages"),
      rep.get("entry_trunk", {}).get("wire_um_each"))
print(" asbuilt", rep["gates"]["P_asbuilt"])
print(" G5", rep["gates"]["G5_sram_structure"]["verdict"], "nodes_in_pin_column",
      len(rep["gates"]["G5_sram_structure"]["nodes_in_pin_column"]), "legs_across", len(rep["gates"]["G5_sram_structure"]["legs_across_sram"]))
for gk in ("G2_island_rows", "G3_cell_rows", "G4_detour_sites"):
    v = rep["gates"][gk]
    print(" ", gk, v["verdict"], {k_: v[k_] for k_ in v if k_ in ("max_disp_um", "n_sites", "n_edges", "n_repeaters",
                                                                  "n_detours", "max_shift_um", "n_straight",
                                                                  "n_length_not_fixed", "repeaters_per_edge")},
          "fail", len(v.get("failures", v.get("illegal", [])) or [i for i in v.get("islands", []) if not i["legal"]]))
