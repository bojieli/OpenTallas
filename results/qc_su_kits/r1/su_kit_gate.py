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
  T  entry_trunk  : (optional, 12.8c) fixed entry trunk chain computed from geometry + NLDM to bring the TT mean to the
                    common target; re-predicts TT/FF with the trunk.
Model + offset used for every prediction (COORD 12:59 ruling 4): su_tree_uf raw liberty NLDM + setRC x 0.8/0.9 Elmore, then
MODEL-REFIT su_tree_model_nldm offsets TT +1.9 / FF -5.1 (930fa9628d, one point; COORD 13:1x correction: the earlier
+13/+24.5 had the wrong sign and model). PLAN MODEL, UNCHECKED.
usage: su_kit_gate.py NAME GEO K LIBDIR UF_PY LEFDIR OUT.json [--trunk TARGET_TT]
"""
import json
import math
import runpy
import sys
from pathlib import Path

name, geo, K, libdir, uf_py, lefdir, out = sys.argv[1:8]
trunk_target = float(sys.argv[sys.argv.index("--trunk") + 1]) if "--trunk" in sys.argv else None
K = int(K)
OFF = {"TT": 1.9, "FF": -5.1}   # MODEL-REFIT 930fa9628d PLAN_TREE_OFFSETS["su_tree_model_nldm"] (one point, btab R5)
ROW_H, SITE_W, LAT, ISL, ROW_HALO = 0.27, 0.054, 4.32, 8.64, 4.32
TOL_SHIFT = 2.16   # along the path, else beside it (Manhattan radius)

sys.argv = [uf_py, geo, "/dev/null", "100", str(K), str(K), "64", libdir]
g = runpy.run_path(uf_py, run_name="su_tree_uf")
best = g["best"]
core, macros, entry = g["core"], g["macros"], g["entry"]
G, NX, NY, W, blk = g["G"], g["NX"], g["NY"], g["W"], g["blk"]
bfs, cell, xy = g["bfs"], g["cell"], g["xy"]
rep = dict(name=name, geo=geo, k=K, model="su_tree_uf raw NLDM+setRC0.8/0.9 Elmore + master_plan.plan_tree_insertion("
           "su_tree_model_nldm) offset TT+1.9/FF-5.1 (claude/model-refit-1026@930fa9628d; one calibration point, btab R5)", plan_pred_raw=best["pred"],
           plan_pred=dict((c, dict(mean=round(best["pred"][c]["mean"] + OFF[c], 2), window=best["pred"][c]["window"]))
                          for c in ("TT", "FF")), gates={})


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
    return in_core(x, y) and not in_rowhalo(x, y) and not any(R[0] <= x <= R[2] and R[1] <= y <= R[3] for R in isl_rects)


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
    if need == short:
        wbest = a
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
    g4.append(dict(edge=nm, level=lev, ok=okall, len_um=round((len(path) - 1) * G, 2), T_um=levT[lev],
                   shortest_um=round(short * G, 2), detour=need > short, repeaters=reps, max_shift_um=round(maxshift, 2)))
rep["gates"]["G4_detour_sites"] = dict(
    verdict="PASS" if all(e["ok"] for e in g4) else "FAIL", n_edges=len(g4),
    n_repeaters=sum(len(e.get("repeaters", [])) for e in g4), n_detours=sum(1 for e in g4 if e.get("detour")),
    max_shift_um=max([e.get("max_shift_um", 0) for e in g4] or [0]), failures=[e for e in g4 if not e["ok"]], edges=g4)
rep["edge_paths_um"] = edge_paths

# ---- T entry trunk (12.8c): fixed chain entry -> trunk -> level-1 driver, sized from geometry + NLDM before build
if trunk_target is not None:
    LIBS, level_chain, stage = g["LIBS"], g["level_chain"], g["stage"]
    TRUNK = ["BUFx4_ASAP7_75t_R", "BUFx6f_ASAP7_75t_R", "BUFx8_ASAP7_75t_R"]
    for corner in ("TT", "FF"):          # same liberty files as the plan model; mutates the model's shared LIBS dict
        LIBS[corner].update(g["lib"].cells(str(Path(libdir) / f"invbuf_{corner.lower()}.lib"), TRUNK))
    BIG, REP = g["BIG"], g["REP"]
    # trunk lies in the 21.6-um centre gap beside the entry island: n stages of cell X, equal wire w each, last drives BIG
    gap_len = 2 * 4.32 * 5          # straight N-S run available in the gap next to the entry island (plan: >= 43.2 um)
    raw_tt = best["pred"]["TT"]["mean"]
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
                err = max(abs(best["pred"][c_]["mean"] + dl[c_] + OFF[c_] - tgt[c_]) for c_ in ("TT", "FF"))
                choices.append((err, n, cname, w, dl))
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
                                      mean=round(best["pred"][c]["mean"] + dl[c] + OFF[c], 2),
                                      window=best["pred"][c]["window"])) for c in ("TT", "FF")))
    else:
        rep["entry_trunk"] = dict(error="no trunk cell in liberty set")

rep["verdict"] = "PASS" if all(v["verdict"] == "PASS" for v in rep["gates"].values()) else "FAIL"
Path(out).write_text(json.dumps(rep, indent=1))
print(name, "VERDICT", rep["verdict"], {k_: v["verdict"] for k_, v in rep["gates"].items()})
print(" pred", rep["plan_pred"], "trunk", rep.get("entry_trunk", {}).get("pred_with_trunk"),
      rep.get("entry_trunk", {}).get("cell"), rep.get("entry_trunk", {}).get("stages"),
      rep.get("entry_trunk", {}).get("wire_um_each"))
for gk in ("G2_island_rows", "G3_cell_rows", "G4_detour_sites"):
    v = rep["gates"][gk]
    print(" ", gk, v["verdict"], {k_: v[k_] for k_ in v if k_ in ("max_disp_um", "n_sites", "n_edges", "n_repeaters",
                                                                  "n_detours", "max_shift_um")},
          "fail", len(v.get("failures", v.get("illegal", [])) or [i for i in v.get("islands", []) if not i["legal"]]))
