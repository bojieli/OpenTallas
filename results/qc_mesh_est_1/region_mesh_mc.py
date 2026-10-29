#!/usr/bin/env python3
"""QC-MESH-EST-1 (estimate only): per-region clock mesh skew, linear RC transient with the QC-CLK-MESH-2 ngspice-fitted
Thevenin BUFx24 (thev_r2.json: R 303/230 ohm + 51.2, d_int 34/27.2 ps, tr 20/18 ps, dVt -0.226/-0.134 ps/mV) and the
CLOCK-128-R6 shielded 4W M8/M9 RC (2.115/2.228 ohm/um, 0.188/0.194 fF/um), 54-um segments, tap load 2.3 fF.
Pre-mesh tree = balanced H-tree from the region root to the drivers (equal length by construction); MC: hierarchical
per-edge sigma (AOCV class A sigma_stage x sqrt(stages)), driver Vt N(0,10 mV) n/p, wire N(1,5 %) per segment,
0.21 %/mm gradient tilt on the pre-mesh insertion (worst axis), plus a deterministic routed-residual spread on the
driver arrivals (uniform +-Rr/2, Rr given).  usage: region_mesh_mc.py CONFIG.json OUT.json"""
import json, math, random, sys
import numpy as np
import scipy.linalg as sl

THEV = {"TT": dict(R=303.0, tr=20.0, dint=34.0, dvt=-0.226, vdd=0.70, sig_stage=2.0743, stage_ps=103.2),
        "FF": dict(R=230.0, tr=18.0, dint=27.2, dvt=-0.134, vdd=0.77, sig_stage=1.5694, stage_ps=85.9)}
RC = {"M8": (2.115, 0.188), "M9": (2.228, 0.194)}      # ohm/um, fF/um (R6 4W shielded)
SEG, CTAP, RX = 54.0, 2.3, 51.2


NDRF = {"4w": (1.0, 1.0), "8w": (0.5, 1.6 / 1.3 * 1.13), "16w": (0.25, 2.3 / 1.3 * 1.13)}


def build(cfg, wire_f):
    rf, cf = NDRF[cfg.get("ndr", "4w")]
    xs, ys = cfg["vx"], cfg["hy"]
    x0, x1 = cfg.get("hx_span", [min(xs), max(xs)])
    y0, y1 = cfg.get("vy_span", [min(ys), max(ys)])
    pts_h = {y: set(xs) | {x0, x1} for y in ys}
    pts_v = {x: set(ys) | {y0, y1} for x in xs}
    stubs = []
    for t in cfg["taps"]:
        tx, ty = t["xy"]
        if ty in pts_h and x0 <= tx <= x1:
            pts_h[ty].add(tx); t["key"] = ("P", tx, ty)
        elif tx in pts_v and y0 <= ty <= y1:
            pts_v[tx].add(ty); t["key"] = ("P", tx, ty)
        else:   # stub from the nearest strap point (Manhattan, straight perpendicular)
            dv = min(((abs(tx - x), x) for x in xs if y0 <= ty <= y1), default=(1e9, None))
            dh = min(((abs(ty - y), y) for y in ys if x0 <= tx <= x1), default=(1e9, None))
            if dv[0] <= dh[0]:
                pts_v[dv[1]].add(ty); stubs.append((("P", dv[1], ty), ("T", tx, ty), dv[0], "M8"))
            else:
                pts_h[dh[1]].add(tx); stubs.append((("P", tx, dh[1]), ("T", tx, ty), dh[0], "M9"))
            t["key"] = ("T", tx, ty)
    nid = {}
    def node(k):
        return nid.setdefault(k, len(nid))
    R, C = [], {}
    def wire(ka, kb, L, layer):
        r, c = RC[layer]
        r, c = r * rf, c * cf
        n = max(1, math.ceil(L / SEG - 1e-9))
        prev = node(ka)
        for q in range(1, n + 1):
            cur = node(kb) if q == n else node((ka, kb, q))
            f = wire_f()
            R.append((prev, cur, r * L / n * f))
            for z in (prev, cur):
                C[z] = C.get(z, 0.0) + c * L / n / 2 * f
            prev = cur
    for y, p in pts_h.items():
        p = sorted(p)
        for u, w in zip(p, p[1:]):
            wire(("P", u, y), ("P", w, y), w - u, "M8")
    for x, p in pts_v.items():
        p = sorted(p)
        for u, w in zip(p, p[1:]):
            wire(("P", x, u), ("P", x, w), w - u, "M9")
    for a, b, L, lay in stubs:
        if L > 0:
            wire(a, b, L, lay)
    for t in cfg["taps"]:
        k = node(t["key"]); C[k] = C.get(k, 0.0) + CTAP
    return nid, R, C, [nid[t["key"]] for t in cfg["taps"]]


def htree_paths(cfg):
    """driver -> list of (edge_id, stages) from the region root, balanced H-tree over the driver set (recursive halving)."""
    root = cfg["root"]
    drv = [tuple(d) for d in cfg["drivers"]]
    paths = {d: [] for d in drv}
    eid = [0]
    def rec(group, at, axis):
        if len(group) == 1:
            return
        key = (lambda d: d[0]) if axis == 0 else (lambda d: d[1])
        vals = sorted(set(key(d) for d in group))
        if len(vals) == 1:
            rec(group, at, 1 - axis); return
        mid = (vals[0] + vals[-1]) / 2.0
        for half in ([d for d in group if key(d) < mid], [d for d in group if key(d) >= mid]):
            cx = sum(d[0] for d in half) / len(half); cy = sum(d[1] for d in half) / len(half)
            c = (cx, cy) if len(half) > 1 else half[0]
            L = abs(c[0] - at[0]) + abs(c[1] - at[1])
            eid[0] += 1
            st = max(1, math.ceil(L / 450.0 - 1e-9))
            for d in half:
                paths[d].append((eid[0], st, L))
            rec(half, c, 1 - axis)
    rec(drv, root, cfg.get("first_axis", 1))
    return paths


def solve(cfg, corner, seed, Rr):
    th = THEV[corner]
    rnd = random.Random(seed * 7919 + (0 if corner == "TT" else 1))
    mc = seed > 0
    nid, R, C, tk = build(json.loads(json.dumps(cfg)), (lambda: rnd.gauss(1.0, 0.05)) if mc else (lambda: 1.0))
    n = len(nid)
    G = np.zeros((n, n))
    for a, b, r in R:
        g = 1.0 / r
        G[a, a] += g; G[b, b] += g; G[a, b] -= g; G[b, a] -= g
    Cv = np.array([C.get(i, 0.0) for i in range(n)]) * 1e-15
    paths = htree_paths(cfg)
    edge_off = {}
    drv = []
    rr = random.Random(12345)        # deterministic residual pattern (same for all MC samples)
    stmax = max(sum(s for _, s, _ in p) for p in paths.values())
    ins_pre = stmax * th["stage_ps"]
    span = max(1.0, max(d[1] for d in cfg["drivers"]) - min(d[1] for d in cfg["drivers"]))
    for d in cfg["drivers"]:
        d = tuple(d)
        off = 0.0
        for e, st, L in paths[d]:
            if mc and e not in edge_off:
                edge_off[e] = rnd.gauss(0.0, th["sig_stage"] * math.sqrt(st))
            off += edge_off.get(e, 0.0)
        res = rr.uniform(-Rr / 2, Rr / 2) if Rr else 0.0
        grad = 0.0021 * (d[1] - min(dd[1] for dd in cfg["drivers"])) / 1000.0 * ins_pre if mc else 0.0
        dv = (rnd.gauss(0, 10.0) + rnd.gauss(0, 10.0)) / 2 if mc else 0.0
        k = nid[("P", d[0], d[1])]
        drv.append((k, off + res + grad + th["dint"] + th["dvt"] * dv))
    rth = th["R"] + RX
    gd = np.zeros(n)
    for k, _ in drv:
        gd[k] += 1.0 / rth
    dt = 0.5
    A = G + np.diag(gd) + np.diag(Cv / (dt * 1e-12))
    lu = sl.lu_factor(A)
    t50 = np.array([t for _, t in drv]); dk = np.array([k for k, _ in drv])
    tidx = np.array(tk)
    vdd, tr = th["vdd"], th["tr"]
    v = np.zeros(n); prev = np.zeros(len(tidx)); cross = np.full(len(tidx), np.nan)
    t = min(t50) - tr
    tend = max(t50) + 600.0
    v[:] = 0.0
    while t < tend:
        t += dt
        vs = np.clip((t - (t50 - tr / 2)) / tr, 0, 1) * vdd
        rhs = Cv / (dt * 1e-12) * v
        np.add.at(rhs, dk, vs / rth)
        v = sl.lu_solve(lu, rhs)
        cur = v[tidx]
        hit = np.isnan(cross) & (cur >= vdd / 2) & (prev < vdd / 2)
        if hit.any():
            f = (vdd / 2 - prev[hit]) / np.maximum(cur[hit] - prev[hit], 1e-12)
            cross[hit] = t - dt + f * dt
        prev = cur
        if not np.isnan(cross).any():
            break
    meshC = sum(C.values())
    return cross, dict(nodes=n, mesh_C_pF=round(meshC / 1000, 3), drivers=len(drv), pre_stages=stmax, ins_pre_ps=round(ins_pre, 1))


def main():
    cfg = json.load(open(sys.argv[1]))
    out = dict(config=cfg["name"], status="UNCHECKED estimate (linear RC + fitted Thevenin)", corners={})
    names = [t["name"] for t in cfg["taps"]]
    glue = [i for i, t in enumerate(cfg["taps"]) if t.get("kind", "glue") == "glue"]
    for corner in ("TT", "FF"):
        res = {}
        for Rr in cfg.get("residuals", [0.0, 30.0]):
            nom, meta = solve(cfg, corner, 0, Rr)
            S = np.array([solve(cfg, corner, s, Rr)[0] for s in range(1, cfg.get("samples", 60) + 1)])
            g = np.array(glue)
            d_nom = nom[g][:, None] - nom[g][None, :]
            D = S[:, g][:, :, None] - S[:, g][:, None, :]
            mu, sd = D.mean(0), D.std(0)
            pair = np.abs(mu) + 3 * sd
            res[str(Rr)] = dict(meta, insertion_tap_ps=[round(float(nom.min()), 1), round(float(nom.max()), 1)],
                                ins_root_to_tap_ps=round(meta["ins_pre_ps"] + float(np.median(nom)), 1),
                                skew_nominal_ps=round(float(nom[g].max() - nom[g].min()), 2),
                                skew_mc_worst_ps=round(float((S[:, g].max(1) - S[:, g].min(1)).max()), 2),
                                sigma_tap_ps=round(float(S[:, g].std(0).max()), 2),
                                pair_mu_3sigma_max_ps=round(float(pair.max()), 2),
                                pair_3sigma_only_max_ps=round(float((3 * sd).max()), 2),
                                nominal_pair_max_ps=round(float(np.abs(d_nom).max()), 2))
        out["corners"][corner] = res
        print(corner, json.dumps(res))
    json.dump(out, open(sys.argv[2], "w"), indent=1)


if __name__ == "__main__":
    main()
