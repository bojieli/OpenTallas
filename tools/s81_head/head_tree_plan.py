#!/usr/bin/env python3
"""HEAD-CORE-LAT-R4 (2026-10-26): plan-built in-core clock tree for the s81_head hard cores (elemA / elemB), 12.8a/b.

Structure (no TritonCTS, no pads/trims/early taps):
  centre entry (pushdown island root, 12.8a) -> L levels of buffered H-tree nodes -> leaf buffers -> sinks.
  The sink set is split by a PLANNED, COUNT-BALANCED recursive bisection of the actual placed clock pins (alternating
  the cut axis along the region's longer side, cut at the count median), so every node at one level drives the same
  number of sinks (the v4q defect was geometric quadrants about the centre: NW 2,953 vs ~8,500 sinks).
  Every node sits at the centroid of the sinks it serves (snapped out of macro halos); every leg is an L route
  (the bend that avoids the macros, x-first preferred) with a repeater at the bend and every <= SEG um, so every
  edge length is fixed by placed cells (su_kit_gate G4 rule) and the model's maze length = the leg length.
  Macro clock pins (ROMs) hang on the leaf input net nearest to them (mscts_h macro leaf stage).
  Optional fixed entry trunk (12.8c): N equal buffers at the entry (same cell chain per type), plan-computed.
Outputs the mscts_h spec (ot_ms_root/tree/leaves/macros, the format uf_phys/common.parse_spec read), the seg json
(seg_um per edge) and a QC-SU-format geo (adds PIN ck at the entry).  PLAN MODEL, UNCHECKED.
usage: head_tree_plan.py GEO OUTPREFIX --fanouts 4,4,4,4,2 [--entry X,Y] [--seg 60] [--trunk N] [--cell C] [--leafcell C]
"""
import argparse
import hashlib
import json
import sys

BUF = "BUFx24_ASAP7_75t_R"


def read_geo(p):
    sinks, macs, die = [], [], None
    for ln in open(p):
        f = ln.split()
        if not f:
            continue
        if f[0] == "SINK":
            sinks.append(dict(x=float(f[1]), y=float(f[2]), inst=f[4], pin=f[5]))
        elif f[0] == "MACRO":
            macs.append(dict(inst=f[1], rect=tuple(map(float, f[3:7])), pin=(float(f[8]), float(f[9])), line=ln.rstrip("\n")))
        elif f[0] == "DIE":
            die = tuple(map(float, f[1:5]))
    return sinks, macs, die


def inside(p, macs, halo):
    for m in macs:
        x0, y0, x1, y1 = m["rect"]
        if x0 - halo < p[0] < x1 + halo and y0 - halo < p[1] < y1 + halo:
            return m
    return None


def snap_out(p, macs, halo):
    m = inside(p, macs, halo)
    if not m:
        return p
    x0, y0, x1, y1 = m["rect"]
    c = [((x0 - halo - 0.01), p[1]), ((x1 + halo + 0.01), p[1]), (p[0], (y0 - halo - 0.01)), (p[0], (y1 + halo + 0.01))]
    c = [q for q in c if not inside(q, macs, halo)]
    return min(c, key=lambda q: abs(q[0] - p[0]) + abs(q[1] - p[1]))


def seg_hits(a, b, macs):
    """axis-parallel segment a->b crosses a macro interior (tree legs run M4/M5; ROM OBS treated as a wall: conservative)."""
    for m in macs:
        x0, y0, x1, y1 = m["rect"]
        if a[1] == b[1]:
            if y0 < a[1] < y1 and min(a[0], b[0]) < x1 and max(a[0], b[0]) > x0:
                return True
        else:
            if x0 < a[0] < x1 and min(a[1], b[1]) < y1 and max(a[1], b[1]) > y0:
                return True
    return False


def l_route(a, b, macs):
    """bend points of an L (or Z through a free channel) route a->b avoiding macros; returns polyline points."""
    for bend in ((b[0], a[1]), (a[0], b[1])):
        if not seg_hits(a, bend, macs) and not seg_hits(bend, b, macs):
            return [a, bend, b]
    # Z route: try a horizontal channel y (vertical first) or vertical channel x
    best = None
    ys = sorted({a[1], b[1]} | {m["rect"][1] - 1.0 for m in macs} | {m["rect"][3] + 1.0 for m in macs})
    for y in ys:
        pts = [a, (a[0], y), (b[0], y), b]
        if not any(seg_hits(pts[i], pts[i + 1], macs) for i in range(3)):
            L = sum(abs(pts[i][0] - pts[i + 1][0]) + abs(pts[i][1] - pts[i + 1][1]) for i in range(3))
            if best is None or L < best[0]:
                best = (L, pts)
    xs = sorted({a[0], b[0]} | {m["rect"][0] - 1.0 for m in macs} | {m["rect"][2] + 1.0 for m in macs})
    for x in xs:
        pts = [a, (x, a[1]), (x, b[1]), b]
        if not any(seg_hits(pts[i], pts[i + 1], macs) for i in range(3)):
            L = sum(abs(pts[i][0] - pts[i + 1][0]) + abs(pts[i][1] - pts[i + 1][1]) for i in range(3))
            if best is None or L < best[0]:
                best = (L, pts)
    if best is None:
        raise SystemExit(f"NO_ROUTE {a}->{b}")
    return best[1]


def split(S, k):
    """count-balanced recursive bisection of sink list S into k parts (k power of 2), longer-side cut at the median."""
    parts = [S]
    while len(parts) < k:
        nxt = []
        for P in parts:
            xs = [s["x"] for s in P]
            ys = [s["y"] for s in P]
            ax = "x" if (max(xs) - min(xs)) >= (max(ys) - min(ys)) else "y"
            Q = sorted(P, key=lambda s: (s[ax], s["y" if ax == "x" else "x"]))
            h = len(Q) // 2
            nxt += [Q[:h], Q[h:]]
        parts = nxt
    return parts


def centroid(P):
    return (sum(s["x"] for s in P) / len(P), sum(s["y"] for s in P) / len(P))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("geo")
    ap.add_argument("out")
    ap.add_argument("--fanouts", required=True)
    ap.add_argument("--entry", default=None)
    ap.add_argument("--seg", type=float, default=60.0)
    ap.add_argument("--halo", type=float, default=2.16)
    ap.add_argument("--trunk", type=int, default=0)
    ap.add_argument("--bend", type=int, default=0)
    ap.add_argument("--balance", type=int, default=0)
    ap.add_argument("--sector", type=int, default=0)
    ap.add_argument("--sector_phase", type=float, default=0.0)
    ap.add_argument("--l1_radius", type=float, default=0.0)
    ap.add_argument("--cell", default=BUF)
    ap.add_argument("--repcell", default=BUF)
    ap.add_argument("--leafcell", default=BUF)
    a = ap.parse_args()
    sinks, macs, die = read_geo(a.geo)
    fos = [int(x) for x in a.fanouts.split(",")]
    entry = tuple(map(float, a.entry.split(","))) if a.entry else ((die[0] + die[2]) / 2, (die[1] + die[3]) / 2)
    tree, leaves, seg = [], [], {}
    cnt = [0]

    def leg(par, pxy, cxy, name, cell):
        """repeater chain par -> child along an L route; returns the last driver name (child's parent)."""
        pts = l_route(pxy, cxy, macs)
        cur, cxy0, k = par, pxy, 0
        for i in range(len(pts) - 1):
            p, q = pts[i], pts[i + 1]
            L = abs(p[0] - q[0]) + abs(p[1] - q[1])
            if L < 1e-6:
                continue
            n = int(L // a.seg)
            for j in range(1, n + 1):
                t = j * a.seg / L
                if j * a.seg >= L - 1e-6:
                    break
                r = (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)
                rn = f"{name}_r{k}"
                tree.append((rn, cur, r, a.repcell))
                seg[rn] = abs(r[0] - cxy0[0]) + abs(r[1] - cxy0[1])
                cur, cxy0, k = rn, r, k + 1
            if i < len(pts) - 2 and (len(pts) > 3 or a.bend):   # Z-route bends (detours) always get a repeater; L bends only with --bend
                rn = f"{name}_r{k}"
                tree.append((rn, cur, q, a.repcell))
                seg[rn] = abs(q[0] - cxy0[0]) + abs(q[1] - cxy0[1])
                cur, cxy0, k = rn, q, k + 1
        return cur, cxy0

    root = "root"
    rxy = entry
    for t in range(a.trunk):     # 12.8c fixed entry trunk: equal cells at the entry, 4.32 um apart
        tn = f"T{t}"
        txy = (entry[0], entry[1] + 0.0)
        tree.append((tn, root, txy, a.cell))
        seg[tn] = 1.0
        root, rxy = tn, txy

    # 1) planned partition (count-balanced recursive bisection), 2) node sites, 3) legs top-down
    def part(P, lvl, name):
        if lvl == len(fos):
            return dict(name=name[:-1], sinks=P, kids=[])
        return dict(name=name[:-1] if lvl else "", sinks=P,
                    kids=[part(Q, lvl + 1, f"{name}{i}_") for i, Q in enumerate(split(P, fos[lvl]))])
    T = part(sinks, 0, "N")
    if a.sector:   # top level: count-balanced ANGULAR sectors about the entry (equal loads), L1 sites at one common L1 radius
        import math
        k = fos[0]
        Q = sorted(sinks, key=lambda s: (math.atan2(s["y"] - entry[1], s["x"] - entry[0]) - a.sector_phase) % (2 * math.pi))
        n = len(Q)
        T["kids"] = [dict(T["kids"][i], sinks=Q[i * n // k:(i + 1) * n // k]) for i in range(k)]
        for i, kd in enumerate(T["kids"]):     # re-partition each sector's sinks below the top level
            sub = part(kd["sinks"], 1, kd["name"] + "_")
            kd["kids"] = sub["kids"]

    def site(nd):
        """bottom-up: leaf at its sink centroid; with --balance a parent at the L1 additive-weight 1-centre of its
        children (minimises the max of leg + downstream path length = DME-style tapping point), else at the centroid."""
        if not nd["kids"]:
            nd["xy"] = snap_out(centroid(nd["sinks"]), macs, a.halo)
            nd["ell"] = 0.0
            return
        for k in nd["kids"]:
            site(k)
        c = centroid(nd["sinks"])
        if a.balance:
            U = [(k["xy"][0] + k["xy"][1], k["xy"][0] - k["xy"][1], k["ell"]) for k in nd["kids"]]
            lo_u, hi_u = min(u - l for u, _, l in U), max(u + l for u, _, l in U)
            lo_v, hi_v = min(v - l for _, v, l in U), max(v + l for _, v, l in U)
            R = max(hi_u - lo_u, hi_v - lo_v) / 2
            cu, cv = c[0] + c[1], c[0] - c[1]
            # feasible u-interval [hi_u - R, lo_u + R], v likewise: pick the point closest to the centroid
            u = min(max(cu, hi_u - R), lo_u + R)
            v = min(max(cv, hi_v - R), lo_v + R)
            c = ((u + v) / 2, (u - v) / 2)
        nd["xy"] = snap_out(c, macs, a.halo)
        nd["ell"] = max(abs(nd["xy"][0] - k["xy"][0]) + abs(nd["xy"][1] - k["xy"][1]) + k["ell"] for k in nd["kids"])
    site(T)
    if a.sector:
        R = a.l1_radius or min(abs(kd["xy"][0] - entry[0]) + abs(kd["xy"][1] - entry[1]) for kd in T["kids"])
        for kd in T["kids"]:
            dx, dy = kd["xy"][0] - entry[0], kd["xy"][1] - entry[1]
            d = abs(dx) + abs(dy)
            kd["xy"] = snap_out((entry[0] + dx * R / d, entry[1] + dy * R / d), macs, a.halo)
        print("L1", [(kd["name"], [round(c, 1) for c in kd["xy"]], len(kd["sinks"]), round(abs(kd["xy"][0] - entry[0]) + abs(kd["xy"][1] - entry[1]), 1)) for kd in T["kids"]])

    def build(nd, par, pxy):
        for k in nd["kids"]:
            cn, cxy = k["name"], k["xy"]
            drv, dxy = leg(par, pxy, cxy, cn, a.repcell)
            seg[cn] = abs(cxy[0] - dxy[0]) + abs(cxy[1] - dxy[1])
            if not k["kids"]:
                leaves.append((cn, drv, cxy, k["sinks"], a.leafcell))
            else:
                tree.append((cn, drv, cxy, a.cell))
                build(k, cn, cxy)
    build(T, root, rxy)
    # macros: leaf whose centre is nearest the macro clock pin
    mac = []
    for m in macs:
        lf = min(leaves, key=lambda L: abs(L[2][0] - m["pin"][0]) + abs(L[2][1] - m["pin"][1]))
        mxy = snap_out((m["pin"][0] - 3.0, m["pin"][1]), macs, a.halo)
        mac.append((m["inst"], lf[0], mxy))

    def esc(s):
        return s.replace("[", "\\[").replace("]", "\\]") if "\\[" not in s else s
    w = open(a.out + ".tcl", "w")
    w.write("# HEAD-CORE-LAT-R4 plan-built in-core tree (head_tree_plan.py): " + " ".join(sys.argv[1:]) + "\n")
    w.write("set ot_ms_port clk\n")
    w.write("set ot_ms_root {%.3f %.3f}\nset ot_h_entry_n 0\nset ot_h_fixed {\n {ot_ms_root BUFx24_ASAP7_75t_R %.3f %.3f}\n}\n" % (entry + entry))
    w.write("set ot_ms_tree {\n")
    for n, p, xy, c in tree:
        w.write(" {%s %s %.3f %.3f %s}\n" % (n, p, xy[0], xy[1], c))
    w.write("}\nset ot_ms_leaves {\n")
    for n, p, xy, Q, c in leaves:
        regs = " ".join("{{%s} {%s}}" % (esc(s["inst"]), s["pin"]) for s in Q)
        w.write(" {%s %s {%.3f %.3f} {%s} %s}\n" % (n, p, xy[0], xy[1], regs, c))
    w.write("}\nset ot_ms_macros {\n")
    for inst, lf, xy in mac:
        w.write(" {{%s} %s {%.3f %.3f}}\n" % (inst, lf, xy[0], xy[1]))
    w.write("}\n")
    w.close()
    json.dump(dict(seg_um=seg), open(a.out + ".seg.json", "w"))
    g = open(a.out + ".geo", "w")
    for ln in open(a.geo):
        f = ln.split()
        if f and f[0] == "SINK":
            g.write("SINK %s %s %s %s %s\n" % (f[1], f[2], f[3], esc(f[4]), f[5]))
        elif f and f[0] in ("DIE", "CORE", "MACRO"):
            g.write(ln)
    g.write("PIN ck %.3f %.3f\n" % entry)
    g.close()
    sz = [len(L[3]) for L in leaves]
    summ = dict(argv=sys.argv, geo_sha256=hashlib.sha256(open(a.geo, "rb").read()).hexdigest(), entry=entry,
                n_sinks=len(sinks), n_leaves=len(leaves), leaf_sinks=[min(sz), max(sz)], n_tree=len(tree),
                n_rep=sum(1 for t in tree if "_r" in t[0]), macros=mac)
    json.dump(summ, open(a.out + ".plan.json", "w"), indent=1)
    print("PLAN", json.dumps({k: summ[k] for k in ("n_sinks", "n_leaves", "leaf_sinks", "n_tree", "n_rep")}))


if __name__ == "__main__":
    main()
