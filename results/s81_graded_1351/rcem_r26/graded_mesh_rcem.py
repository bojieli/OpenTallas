#!/usr/bin/env python3
"""S81-CORES-R26/MS graded-mesh width-cap DIAGNOSTIC (model only): linear RC first-moment (Elmore) + charge-flow EM on the
LITERAL encoded ck_mesh metal (graded_mesh_encode encoded_metal.json), run identically on a pre-cap encoding (enc4) and the
capped encoding (enc8), so the effect of the 1528 narrowed rails (1.68/1.76 -> 1.6 um) on mesh R, load-arrival spread and
rail current density is isolated.  NOT the 12.8e mesh sign-off: no routed tree arrivals (no REC), no native extraction.

Model (declared, UNCHECKED, same constants as main tools/die_plan/kv_r7/qc_clk_mesh2.py RC_R6 + PD12 width extrapolation):
  R(w) = R6_4w * 0.16 / w  ohm/um (M8 2.115, M9 2.228 at 0.16 um);  C(w) = C6_4w * (0.9 + 0.0875 w/0.04) / 1.25 fF/um
  VIA89 cut 2.0 ohm (declared; parallel cuts rows*cols);  driver = (R_th 303 TT / 230 FF + 51.2 stack) / units BUFx24
  (thev_r2); local-tree input load 2.3 fF; bank/stub_drop/tie metal C lumped on the nearest node of its attachment.
Scenarios: (a) nominal, all drivers launch together -> Elmore m1 at the 7481 local-tree inputs (spread = mesh-only skew);
  (b) MC: per-driver launch offset N(0, s) + per-segment R,C N(1, 5 %) (same draws on both encodings): load spread and
  absorption (load spread / driver spread).
EM: per segment charge per transition Q = V * (m1_b - m1_a) / R (exact first moment for linear RC, all drivers at t=0);
  QC r2/r3 method: I_avg = Q f, I_peak = Q / tr (25 ps), I_rms = I_peak sqrt(2 tr f / 3), t = 65 nm; budget 1.0 MA/cm2.
usage: graded_mesh_rcem.py ENCODED_METAL.json OUT.json [--samples N] [--drv-sigma-ps S] [--corner TT]"""
import argparse, bisect, collections, json, math, random, time
import numpy as np, scipy.sparse as sp, scipy.sparse.linalg as spl

ap = argparse.ArgumentParser()
ap.add_argument("metal"); ap.add_argument("out")
ap.add_argument("--samples", type=int, default=8); ap.add_argument("--drv-sigma-ps", type=float, default=10.0)
ap.add_argument("--corner", default="TT"); ap.add_argument("--via-cut-ohm", type=float, default=2.0)
a = ap.parse_args()
R6 = {"M8": (2.115, 0.188), "M9": (2.228, 0.194)}
THEV = {"TT": 303.0, "FF": 230.0}; VDD = {"TT": 0.70, "FF": 0.77}; F = 1.2e9; TR = 25e-12; T_UM = 0.065; LOAD_FF = 2.3
def r_um(l, w): return R6[l][0] * 0.16 / w
def c_um(l, w): return R6[l][1] * (0.9 + 0.0875 * w / 0.04) / 1.25
t0 = time.time()
g = json.load(open(a.metal))
rails = collections.defaultdict(list)     # (layer, centre) -> [(lo, hi, w)]
for s in g["shapes"]:
    if s[1] == "ck_mesh" and s[2] == "mesh":
        lay, c0, c1, lo, hi = s[0], s[3], s[4], s[5], s[6]
        rails[(lay, round((c0 + c1) / 2, 4))].append((lo, hi, round(c1 - c0, 4)))
# points on each rail: segment ends + vias + attachments
pts = collections.defaultdict(set)
for k, segs in rails.items():
    for lo, hi, w in segs: pts[k].update((round(lo, 4), round(hi, 4)))
def rail_of(lay, x, y, tol=0.2):
    c = y if lay == "M8" else x
    for d in (0.0,):
        pass
    best = None
    for cc in (round(c, 4),):
        if (lay, cc) in rails: return (lay, cc)
    # tolerance search
    for (l2, cc), _ in near_index[lay].get(round(c), []):
        if abs(cc - c) <= tol and (best is None or abs(cc - c) < abs(best[1] - c)): best = (l2, cc)
    return best
near_index = {"M8": collections.defaultdict(list), "M9": collections.defaultdict(list)}
for k in rails:
    for r_ in (math.floor(k[1]) - 1, math.floor(k[1]), math.floor(k[1]) + 1, round(k[1])):
        near_index[k[0]][r_].append((k, None))
def on_rail(k, q, tol=0.1):
    return any(lo - tol <= q <= hi + tol for lo, hi, w in rails[k])
via_pairs = []; miss = collections.Counter()
for v in g["vias"]:
    x, y = v["x_um"], v["y_um"]
    k8, k9 = rail_of("M8", x, y), rail_of("M9", x, y)
    if not k8 or not k9 or not on_rail(k8, x) or not on_rail(k9, y): miss["via"] += 1; continue
    pts[k8].add(round(x, 4)); pts[k9].add(round(y, 4)); via_pairs.append((k8, x, k9, y, v["rows"] * v["cols"]))
att = []
for t in g["attachments"]:
    x, y = t["xy_um"]; k = rail_of(t["layer"], x, y)
    q = x if t["layer"] == "M8" else y
    if not k or not on_rail(k, q): miss[t["role"]] += 1; continue
    pts[k].add(round(q, 4)); att.append((t, k, round(q, 4)))
# nodes + wire edges
nid = {}; xy = []
def node(k, q):
    key = (k, q)
    if key not in nid:
        nid[key] = len(xy); xy.append((q, k[1]) if k[0] == "M8" else (k[1], q))
    return nid[key]
E = []   # (i, j, R, C, w, layer, len)
for k, segs in rails.items():
    P = sorted(pts[k]); segs = sorted(segs)
    for lo, hi, w in segs:
        i0 = bisect.bisect_left(P, round(lo, 4) - 1e-6); prev = None
        for q in P[i0:]:
            if q > hi + 1e-6: break
            if prev is not None and q - prev > 1e-6:
                L = q - prev; E.append((node(k, prev), node(k, q), r_um(k[0], w) * L, c_um(k[0], w) * L, w, k[0], L))
            prev = q
for k8, x, k9, y, n in via_pairs:
    E.append((node(k8, round(x, 4)), node(k9, round(y, 4)), a.via_cut_ohm / n, 0.0, None, "V89", 0.0))
N = len(xy)
Cn = np.zeros(N)
for i, j, R, C, *_ in E: Cn[i] += C / 2; Cn[j] += C / 2
drv = []; loads = []
for t, k, q in att:
    i = nid[(k, q)]
    if t["role"] == "driver": drv.append((i, len(t["units"])))
    else: loads.append(i); Cn[i] += LOAD_FF
# lump bank / stub_drop metal C onto the nearest attachment node (grid hash)
H = collections.defaultdict(list)
for t, k, q in att:
    i = nid[(k, q)]; H[(int(xy[i][0] // 50), int(xy[i][1] // 50))].append(i)
lumped = 0.0
for s in g["shapes"]:
    if s[1] == "ck_mesh" and s[2] in ("bank", "stub_drop"):
        lay, c0, c1, lo, hi = s[0], s[3], s[4], s[5], s[6]; w = c1 - c0; L = hi - lo
        cx, cy = ((lo + hi) / 2, (c0 + c1) / 2) if lay == "M8" else ((c0 + c1) / 2, (lo + hi) / 2)
        best = None
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for i in H.get((int(cx // 50) + dx, int(cy // 50) + dy), []):
                    d = abs(xy[i][0] - cx) + abs(xy[i][1] - cy)
                    if best is None or d < best[0]: best = (d, i)
        if best: Cn[best[1]] += c_um(lay, max(w, 0.08)) * L; lumped += c_um(lay, max(w, 0.08)) * L
        else: miss["lump"] += 1
rth = THEV[a.corner] + 51.2
di = np.array([d[0] for d in drv]); gd = np.zeros(N); np.add.at(gd, di, np.array([d[1] for d in drv]) / rth)
I = np.array([e[0] for e in E]); J = np.array([e[1] for e in E]); Rv = np.array([e[2] for e in E]); Cv = np.array([e[3] for e in E])
def solve(rs=None, cs=None, offs=None):
    Rx = Rv * (rs if rs is not None else 1.0); gg = 1.0 / Rx
    G = sp.coo_matrix((np.r_[gg, gg, -gg, -gg], (np.r_[I, J, I, J], np.r_[I, J, J, I])), shape=(N, N)).tocsc() + sp.diags(gd)
    Cn_ = Cn.copy()
    if cs is not None:
        Cn_ = Cn - np.bincount(I, Cv / 2, N) - np.bincount(J, Cv / 2, N) + np.bincount(I, Cv * cs / 2, N) + np.bincount(J, Cv * cs / 2, N)
    lu = spl.splu(G)
    m1 = lu.solve(Cn_ * 1e-15) * 1e12       # ps (ohm*F)
    if offs is not None:
        b = np.zeros(N); np.add.at(b, di, gd[di] * 0 + offs * (np.array([d[1] for d in drv]) / rth)); m1 = m1 + lu.solve(b)
    return m1, Rx
m1, Rx = solve()
L_ = np.array(loads); lm = m1[L_]
# EM per wire segment
V = VDD[a.corner]
Q = V * np.abs(m1[I] - m1[J]) * 1e-12 / Rx         # C per transition
wire = np.array([e[4] is not None for e in E]); W = np.array([e[4] if e[4] else 0 for e in E])
area_cm2 = np.where(wire, W * T_UM * 1e-8, np.nan)
Iavg = Q * F; Ipk = Q / TR; Irms = Ipk * math.sqrt(2 * TR * F / 3)
Javg = np.where(wire, Iavg / area_cm2 / 1e6, 0); Jrms = np.where(wire, Irms / area_cm2 / 1e6, 0)
nar = wire & (np.abs(W - 1.6) < 1e-3)
def wst(mask, arr):
    if not mask.any(): return None
    k = int(np.argmax(np.where(mask, arr, -1))); e = E[k]
    return dict(J=round(float(arr[k]), 4), layer=e[5], width_um=e[4], xy=[round(v, 2) for v in xy[e[0]]])
# MC
rng = np.random.default_rng(26)
mc = []
for s in range(a.samples):
    offs = rng.normal(0, a.drv_sigma_ps, len(drv)); rs = rng.normal(1, 0.05, len(E)); cs = rng.normal(1, 0.05, len(E))
    rs[~wire] = 1.0
    m, _ = solve(rs, cs, offs)
    v = m[L_]; mc.append(dict(load_spread_ps=round(float(v.max() - v.min()), 3), load_sd_ps=round(float(v.std()), 3),
                              drv_spread_ps=round(float(offs.max() - offs.min()), 3)))
rec = dict(schema="opentallas.s81.graded_mesh_rcem.v1", metal=a.metal, corner=a.corner, model=__doc__.split("Model")[1][:900],
           graph=dict(nodes=N, wire_edges=int(wire.sum()), via_edges=int((~wire).sum()), drivers=len(drv), drv_units=int(sum(d[1] for d in drv)),
                      loads=len(loads), unmatched=dict(miss), components=None),
           totals=dict(mesh_wire_mm=round(float(sum(e[6] for e in E)) / 1000, 3), mesh_C_pF=round(float(Cv.sum()) / 1000, 3),
                       lumped_C_pF=round(lumped / 1000, 3), total_C_pF=round(float(Cn.sum()) / 1000, 3),
                       narrowed_1p6_um=round(float(sum(e[6] for k_, e in enumerate(E) if nar[k_])), 1)),
           nominal=dict(load_m1_min_ps=round(float(lm.min()), 3), load_m1_max_ps=round(float(lm.max()), 3),
                        load_spread_ps=round(float(lm.max() - lm.min()), 3), load_p50_ps=round(float(np.median(lm)), 3),
                        load_p99_ps=round(float(np.percentile(lm, 99)), 3)),
           mc=dict(samples=mc, drv_sigma_ps=a.drv_sigma_ps, wire_rel=0.05,
                   load_spread_max_ps=max(m["load_spread_ps"] for m in mc) if mc else None,
                   load_sd_max_ps=max(m["load_sd_ps"] for m in mc) if mc else None),
           em=dict(budget_MA_cm2=1.0, method="QC r2/r3 budgets_em: I_avg=Qf, I_peak=Q/tr(25ps), I_rms=I_peak*sqrt(2 tr f/3), t 65 nm, declared UNCHECKED",
                   worst_Javg_all=wst(wire, Javg), worst_Jrms_all=wst(wire, Jrms),
                   worst_Javg_1p6=wst(nar, Javg), worst_Jrms_1p6=wst(nar, Jrms),
                   n_Jrms_over_budget=int((Jrms > 1.0).sum()), n_Javg_over_budget=int((Javg > 1.0).sum()),
                   n_Jrms_over_budget_1p6=int(((Jrms > 1.0) & nar).sum())),
           runtime_s=round(time.time() - t0, 1))
# connectivity check
from scipy.sparse.csgraph import connected_components
A = sp.coo_matrix((np.ones(len(E)), (I, J)), shape=(N, N))
rec["graph"]["components"] = int(connected_components(A, directed=False)[0])
json.dump(rec, open(a.out, "w"), indent=1)
print(json.dumps({k: rec[k] for k in ("graph", "totals", "nominal", "em", "runtime_s")}, indent=1))
print("mc", rec["mc"]["load_spread_max_ps"], rec["mc"]["load_sd_max_ps"])
