#!/usr/bin/env python3
"""DIE-PROTO 2325 structural QC die-clock study: M8 (H) / M9 (V) clock MESH driven at every intersection, taps on
straight stubs to the nearest mesh line.  Linear RC transient (backward Euler, sparse LU); drivers = Thevenin ramp
sources (R_drv per BUFx24 / m in parallel) whose input arrivals carry the H-tree residue (uniform random +-S/2 and a
die-wide linear gradient G).  Pairs = die_clock.seam_pairs / intra_pairs of the plan (same rule as the die_clock report).
usage: mesh_model.py PLAN TREE_JSON OUT.json --pitch 1000 --m 2 --spread 0 --grad 0 [--ndr 4w|8w]
"""
import argparse, json, math, sys, random
from collections import defaultdict
from pathlib import Path
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as sla
HERE = Path(sys.argv[0]).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument("plan"); ap.add_argument("tree"); ap.add_argument("out")
ap.add_argument("--tools", required=True)
ap.add_argument("--pitch", type=float, default=1000.0)
ap.add_argument("--m", type=float, default=2.0, help="BUFx24 in parallel per intersection")
ap.add_argument("--rdrv", type=float, default=0.12, help="kohm per BUFx24 (die_clock R_DRV_KOHM)")
ap.add_argument("--slew", type=float, default=40.0, help="driver input-to-output ramp 0-100 ps")
ap.add_argument("--spread", type=float, default=0.0); ap.add_argument("--grad", type=float, default=0.0)
ap.add_argument("--ndr", default="4w"); ap.add_argument("--seg", type=float, default=100.0)
ap.add_argument("--tapc", type=float, default=3.0); ap.add_argument("--stubbuf", action="store_true"); ap.add_argument("--drop-keepout", action="store_true"); ap.add_argument("--drv-every", type=int, default=1); ap.add_argument("--relocate", action="store_true", help="a driver on a keep-out moves to the nearest legal point (4 directions, <= pitch/2) on a 4W stub"); ap.add_argument("--seed", type=int, default=1)
a = ap.parse_args()
sys.path.insert(0, a.tools)
import schema as S, die_clock as DC
P = S.Plan(S.load(a.plan)); tree = json.load(open(a.tree)); taps = tree["taps"]
W, H = P.die["outline_um"] if "outline_um" in P.die else (31216.32, 26265.6)
fr, fc = {"2w": (0.5, 1.1), "4w": (0.25, 1.3), "8w": (0.125, 1.6)}[a.ndr]
RC = {L: (r * fr, c * fc) for L, (r, c) in DC.LAYER_RC.items()}   # kohm/um, fF/um
p = a.pitch
xs = np.round(np.arange(p / 2, W, p), 0); ys = np.round(np.arange(p / 2, H, p), 0)
nodes_stub = []
nodes = {}; caps = []; edges = []
def node(key):
    if key not in nodes:
        nodes[key] = len(nodes); caps.append(0.0)
    return nodes[key]
def wire(k0, k1, length, L):
    r, c = RC[L]; n = max(1, int(math.ceil(length / a.seg))); prev = k0
    for i in range(1, n + 1):
        cur = k1 if i == n else (k0, k1, i)
        i0, i1 = node(prev), node(cur)
        edges.append((i0, i1, r * length / n)); caps[i0] += c * length / n / 2; caps[i1] += c * length / n / 2
        prev = cur
# taps: straight stub to the nearest mesh line; landing points are inserted INTO that line (no parallel wire)
hpos = defaultdict(set); vpos = defaultdict(set); tapland = {}
for t in taps:
    x, y = t["xy"]
    j = int(np.argmin(abs(ys - y))); i = int(np.argmin(abs(xs - x)))
    dy, dx = abs(ys[j] - y), abs(xs[i] - x)
    if dy <= dx:
        X = round(min(max(x, xs[0]), xs[-1]), 0); hpos[j].add(X); tapland[t["port"]] = (("H", j, X), dy, "M9")
    else:
        Y = round(min(max(y, ys[0]), ys[-1]), 0); vpos[i].add(Y); tapland[t["port"]] = (("V", i, Y), dx, "M8")
def key_h(j, X):
    i = np.where(np.isclose(xs, X))[0]
    return ("X", int(i[0]), j) if len(i) else ("H", j, X)
def key_v(i, Y):
    j = np.where(np.isclose(ys, Y))[0]
    return ("X", i, int(j[0])) if len(j) else ("V", i, Y)
for j, y in enumerate(ys):                 # horizontal M8 lines
    pts = sorted(set(round(float(x), 0) for x in xs) | hpos[j])
    for u, w in zip(pts, pts[1:]): wire(key_h(j, u), key_h(j, w), w - u, "M8")
for i, x in enumerate(xs):                 # vertical M9 lines
    pts = sorted(set(round(float(y), 0) for y in ys) | vpos[i])
    for u, w in zip(pts, pts[1:]): wire(key_v(i, u), key_v(i, w), w - u, "M9")
for port, (land, d, L) in tapland.items():
    land = key_h(land[1], land[2]) if land[0] == "H" else key_v(land[1], land[2])
    tk = ("T", port)
    if a.stubbuf:   # local stub buffer at the landing point: BUFx24 input cap on the mesh, it drives the stub
        caps[node(land)] += DC.BUF_CIN_FF; nodes_stub.append((tk, land, d, L))
    else:
        wire(land, tk, max(d, 1.0), L); caps[nodes[tk]] += a.tapc
rng = random.Random(a.seed)
drv = []; gd = 1.0 / (a.rdrv * 1e3 / a.m)
KO = DC.keepouts(P) if a.drop_keepout else []
dropped = 0; relocated = []; extra_edges = []; drv_nodes = []
for i, x in enumerate(xs):
    for j, y in enumerate(ys):
        if i % a.drv_every or j % a.drv_every: continue
        inko = lambda X, Y: any(r[0] <= X <= r[2] and r[1] <= Y <= r[3] for r in KO)
        k = nodes[("X", i, j)]
        if KO and inko(x, y):
            if not a.relocate: dropped += 1; continue
            best = None
            for st in range(1, int(p / 2 / 8.64) + 1):
                for dx, dy, L in ((1, 0, "M8"), (-1, 0, "M8"), (0, 1, "M9"), (0, -1, "M9")):
                    X, Y = x + dx * st * 8.64, y + dy * st * 8.64
                    if 0 <= X <= W and 0 <= Y <= H and not inko(X, Y): best = (st * 8.64, L); break
                if best: break
            if not best: dropped += 1; continue
            relocated.append(best[0]); r_, c_ = RC[best[1]]
            kk = len(caps); caps.append(c_ * best[0] / 2); caps[k] += c_ * best[0] / 2; extra_edges.append((k, kk, r_ * best[0])); k = kk
        drv_nodes.append(k)
        off = rng.uniform(-a.spread / 2, a.spread / 2) + a.grad * ((x / W) + (y / H) - 1.0) / 2
        drv.append((k, off)); drv_nodes.pop(); drv_nodes.append(k)
N = len(caps); C = np.array(caps) * 1e-15                     # F
G = sp.lil_matrix((N, N))
for i0, i1, r in edges + extra_edges:
    g = 1.0 / (r * 1e3); G[i0, i0] += g; G[i1, i1] += g; G[i0, i1] -= g; G[i1, i0] -= g
for k in drv_nodes: G[k, k] += gd
G = G.tocsc(); dt = 1e-12
A = (G + sp.diags(C / dt)).tocsc(); lu = sla.splu(A)
dk = np.array([k for k, _ in drv]); doff = np.array([o for _, o in drv]) * 1e-12
stub = {}
for tk, land, d, L in nodes_stub:
    r, c = RC[L]; Rw, Cw = r * d, c * d
    stub[tk[1]] = (nodes[land], (DC.STAGE_PS + 0.69 * (a.rdrv * (Cw + a.tapc) + Rw * (Cw / 2 + a.tapc))))
tn = np.array([stub[t["port"]][0] if t["port"] in stub else nodes[("T", t["port"])] for t in taps])
tadd = np.array([stub[t["port"]][1] if t["port"] in stub else 0.0 for t in taps])
v = np.zeros(N); cross = np.full(len(tn), np.nan); t_end = 2000e-12
tr = a.slew * 1e-12; t0 = -doff.min() + 5e-12
for s in range(int(t_end / dt)):
    tt = (s + 1) * dt
    vin = np.clip((tt - t0 - doff) / tr, 0, 1)
    b = C / dt * v; np.add.at(b, dk, gd * vin)
    vn = lu.solve(b)
    vt0, vt1 = v[tn], vn[tn]; hit = np.isnan(cross) & (vt1 >= 0.5) & (vt0 < 0.5)
    cross[hit] = (tt - dt + dt * (0.5 - vt0[hit]) / (vt1[hit] - vt0[hit]) - t0 - tr / 2) * 1e12
    v = vn
    if not np.isnan(cross).any(): break
cross = cross + tadd
arr = {t["port"]: float(c) for t, c in zip(taps, cross)}
tb = defaultdict(list)
for t in taps: tb[t["part"]].append(t)
seam = DC.seam_pairs(P, tb); intra = DC.intra_pairs(tb, float(P.budgets.get("tap_pitch_um", 400.0)))
sk = [abs(arr[x[0]] - arr[x[1]]) for x in seam]; ik = [abs(arr[x[0]] - arr[x[1]]) for x in intra]
wire_um = len(ys) * (xs[-1] - xs[0]) + len(xs) * (ys[-1] - ys[0])
res = dict(args=vars(a), dropped_on_keepout=dropped, relocated=len(relocated), reloc_max_um=round(max(relocated or [0]),1), mesh_lines=[len(xs), len(ys)], drivers=len(drv), bufx24=len(drv) * a.m, nodes=N,
           mesh_cap_pF=round(float(C.sum()) * 1e12, 1), mesh_wire_mm=round(wire_um / 1e3, 1),
           tap_delay_ps=[round(float(np.nanmin(cross)), 2), round(float(np.nanmax(cross)), 2)],
           tap_skew_ps=round(float(np.nanmax(cross) - np.nanmin(cross)), 2),
           seam_pairs=len(sk), seam_max_ps=round(max(sk), 2), seam_p99_ps=round(DC.pctl(sk, .99), 2),
           intra_pairs=len(ik), intra_max_ps=round(max(ik), 2), unresolved=int(np.isnan(cross).sum()))
json.dump(res, open(a.out, "w"), indent=1); print(json.dumps(res))
