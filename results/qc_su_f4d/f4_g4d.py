#!/usr/bin/env python3
"""QC-SU-F4D f4_g4d.py = f4_g4c.py (QC-PLAN-F4A) + policy spw (COORD RULING GEOM-REVIEW-10 meander 18:43; 12.8 d2):
  spw : STRAIGHT geometric legs.  Every edge keeps its OWN shortest legal maze length (no equalisation to the level max,
        so no meander); with K>=2 the waypoint repeater is chosen among cells ON a shortest path (d(a,w)+d(w,b) in
        {s, s+1 GCell}) by the same key (router-proof for --clear levels, then pin-escape-window path cells, balance,
        mid) so the leg avoids pin windows without adding length.  Residual imbalance -> 12.8 d1 plan sizing.
  Length over Manhattan comes only from the maze (macros + 4.32 halo + keep-outs blocked) = legality jogs.
"""
"""QC-PLAN-F4A f4_g4c.py = f4_g4ab.py (QC-SU-F4-2 e74e75eee1) + --clear LEVELS (COORD RULING QC-SU-F4-2 14:49 (3)):
  * ROUTER-PROOF clearance: for an edge of a --clear level the route is fixed by its waypoint repeater w so that BOTH legs
    a->w and w->b have a bounding box that intersects no pin-escape window (any shortest path of a leg stays in its bbox,
    so GRT cannot take a shortest route through a window); this applies also to the level's longest edge (which f4_g4ab
    routed by an arbitrary shortest walk: vmr Q3 / rp1 Q0 ran y 184.1 through the west SRAM N pin band, 74 cells);
  * island re-site: an L1 island from which no 1-waypoint router-proof shortest route exists is moved to the nearest
    G2-legal 4.32-lattice square (same G2 rule, search +-8 lattice) from which one exists (minimum displacement, same sink
    membership, recorded in G2 as resited);  then T_l = max shortest edge as before (all edges of the level re-timed).
ORIGINAL DOC: QC-SU-F4-2 (COORD RULING QC-SU-F4 14:15 + RULING QC-SU-KITS-2 r2 13:54 + GEOM-REVIEW-5 14:18 conditions):
G4-STRICT plan + AS-BUILT prediction of an SU core tree (su_tree_uf structure, adopted k).

What is built is what is timed:
  * route + site maze blocks the kit MACRO_ROWS_HALO 4.32 (not the 2.2 wire halo): no clock leg runs in the pin-face halo
    (GEOM-5 cond 2); the su_tree_uf plan itself is re-run on that maze (same algorithm, HALO 4.32);
  * no plan node (island / B / leaf / repeater / waypoint) in an SRAM clock-pin column (|x - ck_x| <= 2.16, from the
    pin face out to 8.64 um beyond the row halo);
  * G4-STRICT per level, one of
      wp       : every edge of the level has length T_l = max shortest edge of the level, FIXED by placed cells: the
                 level's K_l-1 repeaters are placed so that the sum of SHORTEST legal paths between consecutive cells
                 equals T_l (one waypoint repeater w with d(a,w)+d(w,b)=T_l, |d(a,w)-d(w,b)| minimal); a level with a
                 detour and no repeater gets one (all edges of that level, equal stage count);
      straight : every edge = shortest legal path, K_l-1 repeaters at equal cuts (nothing to enforce);
    check: enforced length (sum of shortest legs between placed cells) == planned length (+-1.08 um) for every edge;
  * islands at the G2 legal 8.64 lattice square centre (as su_kit_gate G2);
  * SRAM clk pins are SINKS (GEOM-5 cond 4): each joins its nearest leaf (maze), pin cap from the SRAM liberty;
  * timing = uf_asbuilt form (driver loads the SUM of its branch wires + child pin caps, Elmore per branch end, leaf MST),
    plus separate RISE and FALL chains -> early = min, late = max per sink (NUMBER-CHECK-3 ruling 2: FF on both); the
    'avg' form (mean of rise/fall delay, = su_tree_uf / uf_asbuilt) is kept for comparison;
  * 12.8c entry trunk: chain entry pin -> n x cell (wire w each) -> root BIG, searched over the su_kit_gate chain set,
    objective min max(|TT avg mean - 250|, |FF early mean - 202.5|) with offsets applied; computed from this plan's
    prediction, before any build, no measured input.
Offsets: MODEL-REFIT TT +1.9 / FF -5.1 (avg form, btab R5 one point) applied unchanged to every basis; the prog
as-built residual (-16.6 TT / -11.8 FF, KITS-2 r2) is NOT absorbed (COORD 13:54) and is reported as a risk band.
PLAN MODEL, UNCHECKED.
usage: f4_g4ab.py NAME GEO K LIBDIR UF_PY SRAM_LIBDIR OUT_PREFIX [--l1 wp|straight] [--l2 ..] [--l3 ..] [--halo 4.32]
       [--no-sram] [--no-trunk]
"""
import hashlib
import json
import math
import os
import sys
from pathlib import Path

ARGV0 = list(sys.argv)
name, geo, K, libdir, uf_py, sramdir, outp = sys.argv[1:8]
K = int(K)


def opt(k, d):
    return sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d


CLEAR = set(opt("--clear", "").split(",")) - {""}
ISL_OUT_PINWIN = "--isl-out-pinwin" in sys.argv     # GEOM-REVIEW-5 15:05 (b): no island square overlaps a pin-escape window
POL = {"L1": opt("--l1", "wp"), "L2": opt("--l2", "straight"), "L3": opt("--l3", "straight")}
assert all(v in ("wp", "straight", "spw") for v in POL.values()), POL
HALO = float(opt("--halo", "4.32"))
SRAM = "--no-sram" not in sys.argv
TRUNK = "--no-trunk" not in sys.argv
CELLS_FROM = None
WPKEY = opt("--wp-key", "conf")
if "--cells-from" in sys.argv:
    CELLS_FROM = {e["edge"]: e["repeaters"] for e in json.loads(Path(opt("--cells-from", "")).read_text())["gates"]["G4_detour_sites"]["edges"]}
OFF = {"TT": 1.9, "FF": -5.1}
TGT = {"TT": 250.0, "FF": 202.5}
ROW_HALO, LAT, ISL, ROW_H, SITE_W = 4.32, 4.32, 8.64, 0.27, 0.054
CKCOL_HALF, CKCOL_OUT = 2.16, 8.64


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


src = Path(uf_py).read_text()
assert "HALO = 2.2\n" in src and "    return dict(k=k, islands=" in src
src = src.replace("HALO = 2.2\n", f"HALO = {HALO}\n")
src = src.replace("    return dict(k=k, islands=",
                  "    _CAPT[k] = (tree, groups, isl, Bc, leafc, Bs, nB, T1, T2, T3, K1, K2, K3)\n    return dict(k=k, islands=")
sys.argv = [uf_py, geo, "/dev/null", "100", str(K), str(K), "64", libdir]
g = {"__name__": "su_tree_uf_g4", "__file__": uf_py, "_CAPT": {}}
sys.path.insert(0, str(Path(uf_py).parent))
exec(compile(src, uf_py, "exec"), g)
best = g["best"]
tree, groups, isl, Bc, leafc, Bs, nB, T1, T2, T3, K1, K2, K3 = g["_CAPT"][best["k"]]
LIBS, interp, mst, man, md, cell, xy, bfs = (g[n] for n in ("LIBS", "interp", "mst", "man", "md", "cell", "xy", "bfs"))
r, c, FFC, BIG, REP, G, NX, NY, W, blk = (g[n] for n in ("r", "c", "FFC", "BIG", "REP", "G", "NX", "NY", "W", "blk"))
core, macros, entry, sinks = g["core"], g["macros"], g["entry"], g["sinks"]
k = best["k"]
sizing = best["sizing"]

# ---- SRAM clock pins + clock-pin column keep-outs
ckpins = []
for line in open(geo):
    f = line.split()
    if f and f[0] == "MACRO":
        rr = tuple(map(float, f[3:7]))
        px, py = float(f[8]), float(f[9])
        # 0.03 um: a PLACED-geometry dump gives the clk pin RECT centre (LEF rect 0.024 tall at the edge -> 0.012 inside)
        face = "N" if abs(py - rr[3]) < 0.03 else ("S" if abs(py - rr[1]) < 0.03 else "EW")
        ckpins.append(dict(inst=f[1], master=f[2], xy=(px, py), face=face, rect=rr))
keepout = []
for p in ckpins:
    px, py = p["xy"]
    if p["face"] == "N":
        keepout.append((px - CKCOL_HALF, py, px + CKCOL_HALF, py + ROW_HALO + CKCOL_OUT))
    elif p["face"] == "S":
        keepout.append((px - CKCOL_HALF, py - ROW_HALO - CKCOL_OUT, px + CKCOL_HALF, py))


PINWIN = []                                   # pin-escape bands: pin segment x-span, halo + 8.64 um beyond each pin face
for line in open(geo):
    f = line.split()
    if f and f[0] == "MACRO":
        mr = tuple(map(float, f[3:7]))
        ckx = float(f[8])
        x_lo, x_hi = (mr[2] - 40.608, mr[2] - 0.768) if abs(ckx - mr[2]) < abs(ckx - mr[0]) else (mr[0] + 0.768, mr[0] + 40.608)
        PINWIN.append((x_lo, mr[3], x_hi, mr[3] + ROW_HALO + CKCOL_OUT))
        PINWIN.append((x_lo, mr[1] - ROW_HALO - CKCOL_OUT, x_hi, mr[1]))


def in_pinwin(x, y):
    return any(a <= x <= b2 and b <= y <= d for a, b, b2, d in PINWIN)


def in_keepout(x, y):
    return any(a <= x <= b2 and b <= y <= d for a, b, b2, d in keepout)


def in_rowhalo(x, y):
    return any(rr[0] - ROW_HALO < x < rr[2] + ROW_HALO and rr[1] - ROW_HALO < y < rr[3] + ROW_HALO for _, rr in macros)


# ---- G2 island squares (su_kit_gate G2, same rule)
def overlap(a, b):
    return a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]


def row_ok(R):
    return (abs(((R[1] - core[1]) / ROW_H) - round((R[1] - core[1]) / ROW_H)) < 1e-6
            and abs(((R[0] - core[0]) / SITE_W) - round((R[0] - core[0]) / SITE_W)) < 1e-6
            and R[0] >= core[0] - 1e-6 and R[1] >= core[1] - 1e-6 and R[2] <= core[2] + 1e-6 and R[3] <= core[3] + 1e-6)


def rect_hits_halo(R):
    if ISL_OUT_PINWIN and any(R[0] < b2 and R[2] > a and R[1] < d and R[3] > b for a, b, b2, d in PINWIN):
        return True
    return any(R[0] < rr[2] + ROW_HALO and R[2] > rr[0] - ROW_HALO and R[1] < rr[3] + ROW_HALO and R[3] > rr[1] - ROW_HALO
               for _, rr in macros) or any(overlap(R, kk) for kk in keepout)


e0 = [math.floor(entry[0] / LAT) * LAT, math.floor(entry[1] / LAT) * LAT]
e0 = [e0[0] - LAT if entry[0] - e0[0] < LAT / 2 else e0[0], e0[1] - LAT if entry[1] - e0[1] < LAT / 2 else e0[1]]
ent_rect = [e0[0], e0[1], e0[0] + ISL, e0[1] + ISL]
isl_rects, g2 = [], []
for qi, q in enumerate(isl):
    p = xy(q)
    cands = []
    for i in range(-3, 4):
        for j in range(-3, 4):
            x0 = (math.floor(p[0] / LAT) + i) * LAT
            y0 = (math.floor(p[1] / LAT) + j) * LAT
            R = [round(x0, 3), round(y0, 3), round(x0 + ISL, 3), round(y0 + ISL, 3)]
            legal = row_ok(R) and not rect_hits_halo(R) and not overlap(R, ent_rect) and not any(overlap(R, o) for o in isl_rects)
            cc = ((R[0] + R[2]) / 2, (R[1] + R[3]) / 2)
            cands.append((not legal, abs(cc[0] - p[0]) + abs(cc[1] - p[1]), R, legal))
    cands.sort(key=lambda t: (t[0], t[1]))
    _, disp, R, legal = cands[0]
    isl_rects.append(R)
    g2.append(dict(island=f"Q{qi}", plan_xy=p, rect_um=R, centre_disp_um=round(disp, 2), legal=legal))
def bbox_conf(p, q):
    x0, x1 = sorted((p[0], q[0]))
    y0, y1 = sorted((p[1], q[1]))
    return sum(1 for a_, b_, a2, d_ in PINWIN if a_ < x1 + 1e-9 and a2 > x0 - 1e-9 and b_ < y1 and d_ > y0)


def cell_legal0(cc, rects):
    x, y = xy(cc)
    return (not blk[cc[0] * W + cc[1]] and core[0] + 1.08 <= x <= core[2] - 1.08 and core[1] + 1.08 <= y <= core[3] - 1.08
            and not in_rowhalo(x, y) and not in_keepout(x, y)
            and not any(R[0] <= x <= R[2] and R[1] <= y <= R[3] for R in rects + [ent_rect]))


def proof_leg(a, w_, Da):
    """router-proof leg: its maze shortest length equals the Manhattan distance (so EVERY shortest path is monotone and
    stays inside the bounding box) and that box intersects no pin-escape window"""
    return Da[w_[0] * W + w_[1]] == abs(a[0] - w_[0]) + abs(a[1] - w_[1]) and bbox_conf(xy(a), xy(w_)) == 0


def clear_wps(a, b, lens, rects):
    """cells w (legal repeater sites) with d(a,w)+d(w,b) in lens and both legs router-proof (proof_leg)"""
    Da, Db = bfs(a), bfs(b)
    pa, pb = xy(a), xy(b)
    out = []
    for i in range(NX + 1):
        base = i * W
        for j in range(NY + 1):
            da, db = Da[base + j], Db[base + j]
            if da < 0 or db < 0 or da + db not in lens:
                continue
            if da != abs(a[0] - i) + abs(a[1] - j) or db != abs(b[0] - i) + abs(b[1] - j):
                continue
            pw = xy((i, j))
            if bbox_conf(pa, pw) + bbox_conf(pw, pb):
                continue
            if cell_legal0((i, j), rects):
                out.append((i, j, da, db))
    return out


ENT_C = cell(entry)
resite = []
if "L1" in CLEAR:
    D0 = bfs(ENT_C)
    _s0 = [D0[cell(((R[0] + R[2]) / 2, (R[1] + R[3]) / 2))[0] * W + cell(((R[0] + R[2]) / 2, (R[1] + R[3]) / 2))[1]] for R in isl_rects]
    for qi in range(len(isl_rects)):
        R = isl_rects[qi]
        b = cell(((R[0] + R[2]) / 2, (R[1] + R[3]) / 2))
        s0 = D0[b[0] * W + b[1]]
        if s0 < max(_s0) - 1:          # an edge with detour freedom is steered by the waypoint key (f4_g4ab rule)
            continue
        if clear_wps(ENT_C, b, (s0, s0 + 1), isl_rects):
            continue
        p = xy(isl[qi])
        others = [o for t_, o in enumerate(isl_rects) if t_ != qi]
        cands = []
        for i in range(-8, 9):
            for j in range(-8, 9):
                x0 = (math.floor(p[0] / LAT) + i) * LAT
                y0 = (math.floor(p[1] / LAT) + j) * LAT
                R2 = [round(x0, 3), round(y0, 3), round(x0 + ISL, 3), round(y0 + ISL, 3)]
                if not (row_ok(R2) and not rect_hits_halo(R2) and not overlap(R2, ent_rect) and not any(overlap(R2, o) for o in others)):
                    continue
                cc = ((R2[0] + R2[2]) / 2, (R2[1] + R2[3]) / 2)
                cands.append((abs(cc[0] - p[0]) + abs(cc[1] - p[1]), R2))
        cands.sort()
        found = None
        for disp, R2 in cands:
            b2 = cell(((R2[0] + R2[2]) / 2, (R2[1] + R2[3]) / 2))
            s2 = D0[b2[0] * W + b2[1]]
            if s2 < 0:
                continue
            if clear_wps(ENT_C, b2, (s2, s2 + 1), others + [R2]):
                found = (disp, R2)
                break
        if found is None:
            resite.append(dict(island=f"Q{qi}", ok=False, why="no G2-legal square within +-8 lattice has a router-proof L1 route"))
            continue
        resite.append(dict(island=f"Q{qi}", ok=True, old_rect_um=R, new_rect_um=found[1], centre_disp_from_plan_um=round(found[0], 2)))
        isl_rects[qi] = found[1]
        g2[qi].update(rect_um=found[1], centre_disp_um=round(found[0], 2), resited_for_clear_route=True, rect_before_resite_um=R)
isl_site = [cell(((R[0] + R[2]) / 2, (R[1] + R[3]) / 2)) for R in isl_rects]


def cell_legal(cc):
    x, y = xy(cc)
    return (not blk[cc[0] * W + cc[1]] and core[0] + 1.08 <= x <= core[2] - 1.08 and core[1] + 1.08 <= y <= core[3] - 1.08
            and not in_rowhalo(x, y)
            and not in_keepout(x, y) and not any(R[0] <= x <= R[2] and R[1] <= y <= R[3] for R in isl_rects + [ent_rect]))


# ---- G3 node sites (B, leaf) legal + not in a CK column
g3bad = []
for kind, sites in (("B", Bc), ("leaf", leafc)):
    for kk, v in sites.items():
        x, y = xy(v)
        if in_rowhalo(x, y) or in_keepout(x, y) or blk[v[0] * W + v[1]]:
            g3bad.append(dict(kind=kind, node=str(kk), xy=[x, y]))

ent = cell(entry)
levedges = {"L1": [], "L2": [], "L3": []}
for q in range(k):
    levedges["L1"].append((f"Q{q}", "root", ent, isl_site[q]))
for (q, b) in Bs:
    levedges["L2"].append((f"Q{q}B{b}", f"Q{q}", isl_site[q], Bc[(q, b)]))
leafg = {}
for q, b, l, lg in tree:
    nm = f"Q{q}B{b}L{l}"
    levedges["L3"].append((nm, f"Q{q}B{b}", Bc[(q, b)], leafc[(q, b, l)]))
    leafg[nm] = list(lg)


def walk(D, start):
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


def snap_on(path, idx):
    for s in range(0, int(2.16 / G) + 1):
        for t in (idx - s, idx + s):
            if 0 <= t < len(path) and cell_legal(path[t]):
                return path[t], s * G
    ci, cj = path[idx]                                # beside the wire (su_kit_gate G4 rule): nearest legal cell
    st = int(2.16 / G)
    for rr_ in range(1, st + 1):
        for di in range(-rr_, rr_ + 1):
            for dj in (rr_ - abs(di), -(rr_ - abs(di))):
                cc = (ci + di, cj + dj)
                if 0 <= cc[0] <= NX and 0 <= cc[1] <= NY and cell_legal(cc):
                    return cc, rr_ * G
    return None, None


g4, cells_of = [], {}
LEVK = {}
for lev in ("L1", "L2", "L3"):
    E = levedges[lev]
    sh = {nm: bfs(a)[b[0] * W + b[1]] for nm, _, a, b in E}
    need = max(sh.values())
    Kl = {"L1": K1, "L2": K2, "L3": K3}[lev]          # segments per edge in su_tree_uf
    pol = POL[lev]
    if pol == "wp" and Kl == 1 and any(v < need for v in sh.values()):
        Kl = 2                                       # a detour needs a cell; give every edge of the level one
    LEVK[lev] = Kl
    for nm, par, a, b in E:
        Da, Db = bfs(a), bfs(b)
        s = sh[nm]
        rec = dict(edge=nm, level=lev, policy=pol, shortest_um=round(s * G, 2), K=Kl)
        reps = []
        need_e = s if pol == "spw" else need            # F4D spw: the edge's OWN shortest length (no equalising detour)
        if (pol == "wp" and (s < need or lev in CLEAR)) or (pol == "spw" and Kl >= 2):
            # K = 2: the waypoint is the single cut (unchanged).  K >= 3 (placed-geometry re-plan, su_tree_uf chose 3+
            # segments): the waypoint sits at one equal cut c*T/K (r3 rule: a detour waypoint coincides with a cut and
            # carries that cut's repeater); the other K-2 repeaters go at their equal cuts along the walked path.
            CUTS = [c_ * need_e / Kl for c_ in range(1, Kl)]
            bestw, cand = None, []
            for i in range(NX + 1):
                base = i * W
                for j in range(NY + 1):
                    da, db = Da[base + j], Db[base + j]
                    if da < 0 or db < 0 or da + db not in (need_e, need_e + 1):
                        continue
                    if not cell_legal((i, j)):
                        continue
                    cand.append((i, j, da, db))
            for i, j, da, db in cand:
                if Kl == 2:
                    bal = abs(da - db) > 0.25 * need_e          # leg balance within 25 % of T (stage delay), else last resort
                    dev = abs(da - db)
                else:
                    dev = 2 * min(abs(da - c_) for c_ in CUTS)
                    bal = dev > 0.5 * need_e / Kl           # same 25 %-of-stage tolerance per segment
                bc = (0 if (proof_leg(a, (i, j), Da) and proof_leg(b, (i, j), Db)) else 1) if (lev in CLEAR and s >= need_e - 1) else 0
                if lev in CLEAR and bestw is not None and bc > bestw[0][0]:
                    continue
                pth = list(reversed(walk(Da, (i, j)))) + walk(Db, (i, j))[1:]
                conf = sum(1 for cc in pth if in_pinwin(*xy(cc)))   # GEOM-5 cond 2: keep legs out of the pin-escape bands
                key = (bc,) + ((bal, conf) if WPKEY == "bal" else (conf, bal)) + (dev, abs(i - (a[0] + b[0]) / 2) + abs(j - (a[1] + b[1]) / 2))
                if bestw is None or key < bestw[0]:
                    bestw = (key, (i, j))
            if bestw is None:
                rec.update(ok=False, why="no legal waypoint cell with d(a,w)+d(w,b)=T")
                g4.append(rec)
                continue
            w = bestw[1]
            reps = [w]
            path = list(reversed(walk(Da, w))) + walk(Db, w)[1:]
            if Kl > 2:                                   # remaining equal cuts on the walked path, ordered a -> b
                dw = Da[w[0] * W + w[1]]
                cw = min(range(1, Kl), key=lambda c_: abs(dw - c_ * need_e / Kl))
                reps = []
                for jj in range(1, Kl):
                    if jj == cw:
                        reps.append(w)
                        continue
                    cc, shf = snap_on(path, round(jj * (len(path) - 1) / Kl))
                    if cc is None:
                        rec.update(ok=False, why=f"no legal repeater site near cut {jj}")
                        break
                    reps.append(cc)
                if rec.get("ok") is False:
                    g4.append(rec)
                    continue
                rec["waypoint_cut"] = cw
            planned = need_e
            rec["waypoint"] = list(xy(w))
            rec["router_proof"] = bool(proof_leg(a, w, Da) and proof_leg(b, w, Db))
            rec["longest_edge"] = bool(s >= need_e - 1)
        else:
            path = walk(Db, a)                       # a -> b shortest legal path
            planned = s
            for jj in range(1, Kl):
                if CELLS_FROM is not None:              # validation: the repeater sites of an existing su_kit_gate G4
                    reps.append(cell(tuple(CELLS_FROM[nm][jj - 1]["xy"])))
                    continue
                cc, shf = snap_on(path, round(jj * (len(path) - 1) / Kl))
                if cc is None:
                    rec.update(ok=False, why=f"no legal repeater site near cut {jj}")
                    break
                reps.append(cc)
            if rec.get("ok") is False:
                g4.append(rec)
                continue
        seq = [a] + reps + [b]
        enforced = sum(bfs(seq[i])[seq[i + 1][0] * W + seq[i + 1][1]] for i in range(len(seq) - 1))
        ok = abs(enforced - planned) <= 2 and all(cell_legal(x_) for x_ in reps)
        if CELLS_FROM is not None:
            planned = enforced
        rec["pinwin_cells"] = sum(1 for cc in path if in_pinwin(*xy(cc)))
        rec.update(ok=ok, planned_um=round(planned * G, 2), enforced_um=round(enforced * G, 2),
                   detour=planned > s, cells=[list(xy(x_)) for x_ in reps],
                   legs_um=[round(bfs(seq[i])[seq[i + 1][0] * W + seq[i + 1][1]] * G, 2) for i in range(len(seq) - 1)],
                   path_um=[list(xy(x_)) for x_ in path[::4]] + [list(xy(path[-1]))])
        g4.append(rec)
        cells_of[nm] = (par, reps, b)

# ---- build the node graph
nodes = {"root": (None, ent, BIG)}
order = ["root"]
for lev in ("L1", "L2", "L3"):
    for nm, par, a, b in levedges[lev]:
        if nm not in cells_of:
            continue
        p = par
        for jj, cc in enumerate(cells_of[nm][1]):
            rn = f"{nm}_r{jj}"
            nodes[rn] = (p, cc, REP)
            order.append(rn)
            p = rn
        drv = BIG if lev == "L3" else (sizing[f"Q_{nm[1:]}"] if lev == "L1" else sizing["B_" + "_".join(nm[1:].split("B"))])
        nodes[nm] = (p, b, drv)
        order.append(nm)
kids = {}
for n in order:
    if nodes[n][0]:
        kids.setdefault(nodes[n][0], []).append(n)

# SRAM pins -> nearest leaf (maze from the pin's nearest free cell)
sram_cap = {}
for corner in ("TT", "FF"):
    for p in ckpins:
        lf = Path(sramdir) / p["master"] / f"{p['master']}_{corner.lower()}.lib"
        t = lf.read_text()
        i = t.find("pin (clk)")
        sram_cap[(p["master"], corner)] = float(t[i:i + 400].split("capacitance :")[1].split(";")[0])
leaf_sram = {}
if SRAM:
    for p in ckpins:
        pc = cell(p["xy"])
        lf = min(leafg, key=lambda nm: bfs(nodes[nm][1])[pc[0] * W + pc[1]] if bfs(nodes[nm][1])[pc[0] * W + pc[1]] >= 0 else 1e9)
        leaf_sram.setdefault(lf, []).append(p)


def seg(a_, b_):
    A, B = nodes[a_][1], nodes[b_][1]
    return bfs(A)[B[0] * W + B[1]] * G


TRUNK_CELLS = ["BUFx4_ASAP7_75t_R", "BUFx6f_ASAP7_75t_R", "BUFx8_ASAP7_75t_R"]
for corner in ("TT", "FF"):
    LIBS[corner].update(g["lib"].cells(str(Path(libdir) / f"invbuf_{corner.lower()}.lib"), TRUNK_CELLS))


def dly(L, s, C, mode):
    rd, fd = interp(L["rise"], s, C), interp(L["fall"], s, C)
    return {"rise": rd, "fall": fd, "avg": 0.5 * (rd + fd)}[mode]


def timing(corner, mode, trunk=None):
    L = LIBS[corner]
    t0, s0 = 0.0, 20.0
    if trunk and trunk[1] > 0:
        cname, n, w = trunk
        for i in range(n):
            cp = L[cname]["cin"] if i < n - 1 else L[BIG]["cin"]
            C = c * w + cp
            t0 += dly(L[cname], s0, C, mode) + r * w * (c * w / 2 + cp)
            s0 = interp(L[cname]["trise"], s0, C)
    arr = {"root": (t0, s0)}
    out = {}
    for n in order:
        if n in leafg:
            continue
        ta, sa = arr[n]
        ch = kids.get(n, [])
        ws = [seg(n, x_) for x_ in ch]
        cps = [L[nodes[x_][2]]["cin"] for x_ in ch]
        C = sum(c * w + cp for w, cp in zip(ws, cps))
        Lc = L[nodes[n][2]]
        d = dly(Lc, sa, C, mode)
        so = interp(Lc["trise"], sa, C)
        for x_, w, cp in zip(ch, ws, cps):
            arr[x_] = (ta + d + r * w * (c * w / 2 + cp), so)
    sram_arr = {}
    for nm, lg in leafg.items():
        ta, s3 = arr[nm]
        lc = xy(nodes[nm][1])
        sp = leaf_sram.get(nm, [])
        pts = [lc] + [p_[:2] for p_ in lg] + [p_["xy"] for p_ in sp]
        wl = mst(pts)
        C = c * wl + len(lg) * FFC[corner] + sum(sram_cap[(p_["master"], corner)] for p_ in sp)
        d = dly(L[BIG], s3, C, mode)
        nload = len(lg) + len(sp)
        rad = (sum(man(p_, lc) for p_ in lg) + sum(man(p_["xy"], lc) for p_ in sp)) / nload
        out[nm] = ta + d + r * rad * C / 2
        for p_ in sp:
            sram_arr[p_["inst"]] = ta + d + r * man(p_["xy"], lc) * C / 2
    return out, sram_arr


def summary(trunk=None):
    res = {}
    for corner in ("TT", "FF"):
        rr_ = {m: timing(corner, m, trunk) for m in ("rise", "fall", "avg")}
        early = {nm: min(rr_["rise"][0][nm], rr_["fall"][0][nm]) for nm in leafg}
        late = {nm: max(rr_["rise"][0][nm], rr_["fall"][0][nm]) for nm in leafg}
        avg = rr_["avg"][0]
        se = {i: min(rr_["rise"][1][i], rr_["fall"][1][i]) for i in rr_["avg"][1]}
        sl = {i: max(rr_["rise"][1][i], rr_["fall"][1][i]) for i in rr_["avg"][1]}
        d = {}
        for basis, v, sv in (("avg", avg, rr_["avg"][1]), ("early", early, se), ("late", late, sl)):
            vals = list(v.values())
            allv = vals + list(sv.values())
            d[basis] = dict(mean_raw=round(sum(vals) / len(vals), 2), mean=round(sum(vals) / len(vals) + OFF[corner], 2),
                            min=round(min(vals), 2), max=round(max(vals), 2), window=round(max(vals) - min(vals), 2),
                            window_incl_sram=round(max(allv) - min(allv), 2),
                            sram_pin={i: round(x_ + OFF[corner], 2) for i, x_ in sv.items()})
        d["leaf_avg"] = {nm: round(x_, 2) for nm, x_ in avg.items()}
        res[corner] = d
    return res


_fail = [e for e in g4 if not e["ok"] and e["edge"] not in cells_of]
if _fail:
    print("G4 edges with no cell sequence:", [(e["edge"], e.get("why")) for e in _fail])
    Path(outp + ".json").write_text(json.dumps(dict(command=" ".join(ARGV0), verdict="FAIL", failures=_fail), indent=1))
    sys.exit(2)
base = summary()
rep = dict(lane="QC-SU-F4D", name=name, clear_levels=sorted(CLEAR), isl_out_pinwin=ISL_OUT_PINWIN,
           pinwin_path_cells={lv: sum(e.get("pinwin_cells", 0) for e in g4 if e["level"] == lv) for lv in ("L1", "L2", "L3")},
           edges_with_pinwin_cells={lv: sum(1 for e in g4 if e["level"] == lv and e.get("pinwin_cells", 0)) for lv in ("L1", "L2", "L3")}, island_resite=resite, scope="G4-STRICT plan + AS-BUILT re-timing; PLAN MODEL, UNCHECKED",
           command=" ".join(ARGV0), cwd=os.getcwd(),
           inputs={p_: sha(p_) for p_ in [geo, uf_py, __file__, str(Path(uf_py).parent / "lib.py"),
                                         str(Path(libdir) / "invbuf_tt.lib"), str(Path(libdir) / "invbuf_ff.lib")]
                   + [str(Path(sramdir) / m / f"{m}_{cc}.lib") for m in sorted({p["master"] for p in ckpins}) for cc in ("tt", "ff")]},
           model=dict(form="uf_asbuilt (sum-of-branch loads, Elmore per branch, leaf MST) + rise/fall chains; NLDM + setRC 0.8/0.9",
                      offsets=OFF, offset_basis="MODEL-REFIT 930fa9628d avg form (btab R5, one point); applied unchanged to early/late",
                      unabsorbed_residual="prog as-built residual TT -16.6 sd3.6 / FF -11.8 sd2.9 (KITS-2 r2) NOT applied",
                      halo_um=HALO, policies=POL, pin_windows=PINWIN,
                      wp_key=WPKEY, waypoint_rule="legal cell w with d(a,w)+d(w,b)=T; key = (legs unbalanced >25% T, path cells in pin-escape bands [order swapped with --wp-key conf], |d(a,w)-d(w,b)|, distance to edge midpoint)", sram_sinks=SRAM, ckcol_keepout=keepout),
           k=k, n_sinks=len(sinks), n_sram_sinks=sum(len(v) for v in leaf_sram.values()), uf_equalT_pred=best["pred"],
           levels=dict(T_um=dict(T1=round(T1 * 1, 2), T2=round(T2, 2), T3=round(T3, 2)), segments_per_edge=LEVK),
           clear_route=dict(verdict=("PASS" if all(e.get("router_proof") for e in g4 if e["level"] in CLEAR and e.get("longest_edge"))
                                     and all(x_["ok"] for x_ in resite) else "FAIL") if CLEAR else "NOT_RUN",
                            rule="longest edge(s) of each --clear level: both waypoint legs router-proof (maze shortest = Manhattan, bbox free of pin-escape windows); other edges keep the f4_g4ab waypoint key; router_proof reported for all",
                            edges={e["edge"]: dict(router_proof=e.get("router_proof"), longest=e.get("longest_edge"), walked_pinwin_cells=e.get("pinwin_cells")) for e in g4 if e["level"] in CLEAR}),
           gates=dict(G2_island_rows=dict(verdict="PASS" if all(i_["legal"] for i_ in g2) else "FAIL", islands=g2),
                      G3_node_sites=dict(verdict="PASS" if not g3bad else "FAIL", illegal=g3bad),
                      G4_strict=dict(verdict="PASS" if all(e["ok"] for e in g4) else "FAIL", n_edges=len(g4),
                                     n_detours=sum(1 for e in g4 if e.get("detour")),
                                     n_cells=sum(len(e.get("cells", [])) for e in g4),
                                     failures=[e for e in g4 if not e["ok"]], edges=g4)),
           pred_no_trunk={cc: {b_: v for b_, v in base[cc].items() if b_ != "leaf_avg"} for cc in base})
if TRUNK:
    tt0 = summary(None)
    ch = [(round(max(abs(tt0["TT"]["avg"]["mean"] - TGT["TT"]), abs(tt0["FF"]["early"]["mean"] - TGT["FF"])), 1), 0, 0.0, "none", tt0)]
    for cname in TRUNK_CELLS:
        for n in range(1, 9):
            for w10 in range(5, 61, 5):
                w = float(w10)
                if n * w > 43.2:
                    continue
                tt = summary((cname, n, w))
                err = max(abs(tt["TT"]["avg"]["mean"] - TGT["TT"]), abs(tt["FF"]["early"]["mean"] - TGT["FF"]))
                ch.append((round(err, 1), n, w, cname, tt))
    ch.sort(key=lambda t: (t[0], t[1], t[2]))
    err, n, w, cname, tt = ch[0]
    rep["entry_trunk"] = dict(cell=cname, stages=n, wire_um_each=w, max_err_ps=err, run="N-S in the centre gap from the entry island",
                              objective="min max(|TT avg mean-250|, |FF early mean-202.5|), offsets applied; 12.8c/d1 plan-computed")
    rep["pred"] = {cc: {b_: v for b_, v in tt[cc].items() if b_ != "leaf_avg"} for cc in tt}
    rep["leaf_avg_with_trunk"] = {cc: tt[cc]["leaf_avg"] for cc in tt}
else:
    rep["pred"] = rep["pred_no_trunk"]
P = rep["pred"]
band = dict(TT_mean=P["TT"]["avg"]["mean"], TT_window=P["TT"]["avg"]["window"], TT_window_incl_sram=P["TT"]["avg"]["window_incl_sram"],
            FF_early_mean=P["FF"]["early"]["mean"], FF_late_mean=P["FF"]["late"]["mean"], FF_early_window=P["FF"]["early"]["window"])
band["in_band_12_3"] = (230 <= band["TT_mean"] <= 270 and band["TT_window"] <= 20 and 182.5 <= band["FF_early_mean"] <= 222.5
                        and band["FF_early_window"] <= 20)
band["with_prog_residual_TT"] = round(band["TT_mean"] - 16.6, 2)
rep["band"] = band
# G1 macro-pin track check (COORD RULING QC-PLAN-F4A (1)): every macro signal pin centre on its layer's kit track
# (M5 x / M4 y, offset 0.012 pitch 0.048), orientation from the floorplan meta (GEO.json); missing meta = FAIL
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools/die_plan"))
import macro_tracks as MT  # noqa: E402
_g1 = []
try:
    _meta = json.loads(Path(geo + ".json").read_text())
    for _n, _cell, _box, _o, _ck in _meta["macros"]:
        _sz, _pins = MT.lef_pins(Path(sramdir) / _cell / (_cell + ".lef"))
        _bad = MT.check(_sz, _pins, _box[0], _box[1], _o)
        _g1.append(dict(inst=_n, cell=_cell, origin=[round(_box[0], 4), round(_box[1], 4)], orient=_o,
                        pins_checked=sum(1 for q in _pins if q[1] in MT.TRK), off_track=len(_bad), first=_bad[:3]))
    _g1v = "PASS" if _g1 and all(m["off_track"] == 0 for m in _g1) else "FAIL"
except (OSError, KeyError, ValueError, StopIteration) as _e:
    _g1v, _g1 = "FAIL", [dict(error=repr(_e))]
# ---- G5 SRAM structure (GEOM-REVIEW-4 addendum, column-view form): no tree node (island centre, driver, repeater) in an
# SRAM clock-pin column (the N/S-face keep-out above), none inside a macro; legs are maze paths with macros + 2.2 um halo
# blocked, so no leg crosses an SRAM.  (The r3 su_kit_gate G5 puts the pin column BESIDE the E/W macro edge -- the m2
# view pin face -- which is not the column-view pin face.)
_g5n = [(n_, xy(v_[1])) for n_, v_ in nodes.items()] + [(i_["island"], ((i_["rect_um"][0] + i_["rect_um"][2]) / 2,
        (i_["rect_um"][1] + i_["rect_um"][3]) / 2)) for i_ in g2 if "rect_um" in i_]
_g5c = [dict(node=n_, xy=[round(q_[0], 3), round(q_[1], 3)]) for n_, q_ in _g5n if in_keepout(*q_)]
_g5m = [dict(node=n_, xy=[round(q_[0], 3), round(q_[1], 3)]) for n_, q_ in _g5n
        if any(r_[0] < q_[0] < r_[2] and r_[1] < q_[1] < r_[3] for _, r_ in macros)]
rep["gates"]["G5_sram_structure"] = dict(verdict="PASS" if keepout and not _g5c and not _g5m else "FAIL",
    pin_columns_um=[[round(v_, 3) for v_ in q_] for q_ in keepout], nodes_checked=len(_g5n), nodes_in_pin_column=_g5c,
    nodes_in_macro=_g5m, legs_across_sram="0 by construction (maze legs, macros + halo blocked)")
rep["gates"] = dict(G1_macro_pin_track=dict(verdict=_g1v, macros=_g1), **rep["gates"])
rep["verdict"] = "PASS" if all(v["verdict"] == "PASS" for v in rep["gates"].values()) else "FAIL"
Path(outp + ".json").write_text(json.dumps(rep, indent=1))
with open(outp + ".tcl", "w") as fo:       # mscts_h spec (uf_asbuilt format): every plan cell incl. waypoint repeaters, FIRM
    fo.write("# QC-PLAN-F4A (f4_g4c) mscts_h spec, G4-strict plan %s (k=%d, policies %s), plan-computed (12.8 d1), no measured input.\n" % (name, k, POL))
    fo.write("# command: %s\n" % " ".join(ARGV0))
    fo.write("set ot_ms_port ck\nset ot_ms_root {%.3f %.3f}\nset ot_h_entry_n 0\n" % xy(ent))
    fo.write("set ot_h_fixed {\n {ot_ms_root %s %.3f %.3f}\n}\n" % ((BIG,) + xy(ent)))
    fo.write("set ot_ms_tree {\n")
    for n in order:
        if n == "root" or n in leafg:
            continue
        pp, cc, cl = nodes[n]
        fo.write(" {%s %s %.3f %.3f %s}\n" % ((n, pp) + xy(cc) + (cl,)))
    fo.write("}\nset ot_ms_leaves {\n")
    for nm, lg in leafg.items():
        pp, cc, cl = nodes[nm]
        regs = " ".join("{{%s} {%s}}" % (sk[2], sk[3]) for sk in lg)
        fo.write(" {%s %s {%.3f %.3f} {%s} %s}\n" % ((nm, pp) + xy(cc) + (regs, cl)))
    fo.write("}\nset ot_ms_macros {\n")
    for nm, sp in leaf_sram.items():
        for p_ in sp:
            fo.write(" {{%s} %s {%.3f %.3f}}\n" % (p_["inst"], nm, p_["xy"][0], p_["xy"][1]))
    fo.write("}\n")
print(name, "VERDICT", rep["verdict"], {kk: v["verdict"] for kk, v in rep["gates"].items()},
      "G4", {kk: rep["gates"]["G4_strict"][kk] for kk in ("n_edges", "n_detours", "n_cells")}, "K", LEVK)
print(" T", rep["levels"]["T_um"], "trunk", rep.get("entry_trunk", {}).get("cell"), rep.get("entry_trunk", {}).get("stages"),
      rep.get("entry_trunk", {}).get("wire_um_each"))
for cc in ("TT", "FF"):
    print(" ", cc, "notrunk avg", {a_: base[cc]["avg"][a_] for a_ in ("mean", "window", "window_incl_sram")},
          "| pred", {b_: {a_: P[cc][b_][a_] for a_ in ("mean", "window", "window_incl_sram")} for b_ in ("avg", "early", "late")})
print(" BAND", band)
