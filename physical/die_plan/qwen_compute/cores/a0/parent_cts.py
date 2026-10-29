#!/usr/bin/env python3
"""QC A0 PARENT kit CTS hook, python side (QC-A0-KITS-10; die-local, opt-in via the gen_core_kit_qc recipe key
"parent_trunk"; nothing else calls it).  The kit hook parent_cts.tcl (PRE_CTS, wraps clock_tree_synthesis) runs:

  1. sink dump (parent_cts.tcl)     -> sinks.txt: DIE / MACRO / SINK lines (register clock pins on the tile clock port
                                       net = UNGATED, on the u_icg GCLK net = GATED; hard child clock pins)
  2. `cluster sinks.txt cl.json cl.tcl` -> glue-register leaf clusters (DIE-QC-12 clusters.py rule: <= maxd um box,
                                       <= maxn regs, no macro overlap, small clusters merged); ungated and gated
                                       registers are clustered SEPARATELY and ungated clusters are flagged "ungated"
                                       (parent_trunk_dme.py plan --ungated-split); one root CKINVDCx16 site each
  3. TritonCTS on the cluster nets only (parent_cts.tcl)
  4. `clins arr.txt cl.json clins.json` -> per-cluster measured root->register insertion TT (max) / FF (min)
  5. tools/die_plan/parent_trunk_dme.py plan --ungated-split + tcl, parent_trunk_insert.tcl ICG_INST (parent_cts.tcl)

Pure python (no numpy): the same split / merge / legalise rules as results/die_qc12_1028/a0trunk/clusters.py.
"""
import json
import statistics as st
import sys


def read_sinks(path):
    """SINK <inst> <master> <pin> <x_dbu> <y_dbu> <ungated 0|1> <kid 0|1>; MACRO <inst> <master> x0 y0 x1 y1;
    DIE x0 y0 x1 y1 dbu"""
    regs, kids, macros, die = [], [], [], None
    for line in open(path):
        p = line.split()
        if not p:
            continue
        if p[0] == "DIE":
            u = float(p[5]); die = (int(p[3]) / u, int(p[4]) / u); dbu = u
    if die is None:
        raise ValueError("sinks file has no DIE line")
    for line in open(path):
        p = line.split()
        if not p:
            continue
        if p[0] == "SINK":
            x, y = int(p[4]) / dbu, int(p[5]) / dbu
            if p[7] == "1":
                kids.append(dict(inst=p[1], module=p[2], pin=[round(x, 3), round(y, 3)]))
            else:
                regs.append((p[1], x, y, p[6] == "1"))
        elif p[0] == "MACRO":
            macros.append([int(v) / dbu for v in p[3:7]])
    return die, regs, kids, macros


def _box(P, idx):
    xs = [P[i][0] for i in idx]; ys = [P[i][1] for i in idx]
    return min(xs), min(ys), max(xs), max(ys)


def _ov(lo, hi, macros):
    return any(min(hi[0], m[2]) - max(lo[0], m[0]) > 10 and min(hi[1], m[3]) - max(lo[1], m[1]) > 10 for m in macros)


def _median(v):
    return st.median(v)


def split_clusters(P, macros, maxd=200.0, maxn=1200):
    """recursive median split (longest box axis; a >5 um gap at a macro overlap), then small (<60) clusters merge into
    the nearest neighbour when the union stays <= maxd, <= maxn and macro-free (clusters.py rule)."""
    def split(idx):
        x0, y0, x1, y1 = _box(P, idx); ext = (x1 - x0, y1 - y0)
        ov = _ov((x0, y0), (x1, y1), macros)
        if max(ext) <= maxd and len(idx) <= maxn and not ov:
            return [idx]
        if max(ext) <= 20:
            return [idx]
        ax = 0 if ext[0] >= ext[1] else 1
        v = [P[i][ax] for i in idx]; med = _median(v)
        if ov:
            s = sorted(v); g = [s[k + 1] - s[k] for k in range(len(s) - 1)]
            if g:
                k = max(range(len(g)), key=lambda j: g[j])
                if g[k] > 5:
                    med = (s[k] + s[k + 1]) / 2
        a = [i for i in idx if P[i][ax] <= med]; b = [i for i in idx if P[i][ax] > med]
        if not a or not b:
            return [idx]
        return split(a) + split(b)

    if not P:
        return []
    cl = split(list(range(len(P))))

    def boxov(idx):
        x0, y0, x1, y1 = _box(P, idx)
        return max(x1 - x0, y1 - y0), _ov((x0, y0), (x1, y1), macros)

    def med(idx):
        return (_median([P[i][0] for i in idx]), _median([P[i][1] for i in idx]))

    changed = True
    while changed:
        changed = False
        cl.sort(key=lambda c: (len(c), c[0]))
        for i, a in enumerate(cl):
            if len(a) >= 60:
                break
            ca = med(a); best = None
            for j, b in enumerate(cl):
                if j == i:
                    continue
                u = a + b; ext, ov = boxov(u)
                if ext <= maxd and not ov and len(u) <= maxn:
                    mb = med(b); d = abs(mb[0] - ca[0]) + abs(mb[1] - ca[1])
                    if best is None or d < best[0]:
                        best = (d, j, u)
            if best:
                cl = [c for k, c in enumerate(cl) if k not in (i, best[1])] + [sorted(best[2])]
                changed = True
                break
    return cl


def legal(x, y, W, H, macros, ring=6.0):
    """nearest point outside every macro (+1 um), inside the core ring"""
    def inmac(x, y, h=1.0):
        return any(m[0] - h < x < m[2] + h and m[1] - h < y < m[3] + h for m in macros)
    x = min(max(x, ring), W - ring); y = min(max(y, ring), H - ring)
    if not inmac(x, y):
        return x, y
    best = None
    for m in macros:
        if m[0] - 1 < x < m[2] + 1 and m[1] - 1 < y < m[3] + 1:
            for c in ((m[0] - 1.5, y), (m[2] + 1.5, y), (x, m[1] - 1.5), (x, m[3] + 1.5)):
                if ring <= c[0] <= W - ring and ring <= c[1] <= H - ring and not inmac(*c):
                    d = abs(c[0] - x) + abs(c[1] - y)
                    if best is None or d < best[0]:
                        best = (d, c)
    if best is None:
        raise ValueError("no legal cluster root site near (%.3f, %.3f)" % (x, y))
    return best[1]


def cluster(sinks_path, maxd=200.0, maxn=1200, prefix="a0cl"):
    (W, H), regs, kids, macros = read_sinks(sinks_path)
    out = []
    for flag in (False, True):            # gated first, then ungated; never mixed in one cluster
        sel = [r for r in regs if r[3] == flag]
        P = [(r[1], r[2]) for r in sel]
        for idx in split_clusters(P, macros, maxd, maxn):
            mx = _median([P[i][0] for i in idx]); my = _median([P[i][1] for i in idx])
            rx, ry = legal(mx, my, W, H, macros)
            x0, y0, x1, y1 = _box(P, idx)
            c = dict(name="%s%d%s" % (prefix, len(out), "u" if flag else ""), n=len(idx),
                     root=[round(rx, 3), round(ry, 3)], box=[round(v, 2) for v in (x0, y0, x1, y1)],
                     regs=[sel[i][0] for i in idx])
            if flag:
                c["ungated"] = True
            out.append(c)
    return dict(W=W, H=H, macros=macros, kids=kids, clusters=out)


def cl_tcl(G):
    """Tcl list for parent_cts.tcl: lappend PT_CL [list name x y ungated {regs}]"""
    lines = ["set PT_CL {}"]
    for c in G["clusters"]:
        lines.append("lappend PT_CL [list %s %.3f %.3f %d {%s}]" % (
            c["name"], c["root"][0], c["root"][1], 1 if c.get("ungated") else 0,
            " ".join("{%s}" % r for r in c["regs"])))
    return "\n".join(lines) + "\n"


def clins(arr_path, G):
    """arrival lines `S <pin> <cluster> <max_rise> <min_rise>` (register clock pins) and `T <root>/A <max_fall> <min_fall>`
    (the root is an inverter: the register rise follows the root A fall); insertion = register rise arrival - its cluster
    root A fall arrival; TT = max (slow corner), FF = min (fast corner)."""
    T, S = {}, {}
    names = {c["name"] for c in G["clusters"]}
    for line in open(arr_path):
        p = line.split()
        if not p:
            continue
        if p[0] == "T":
            T[p[1]] = (float(p[2]), float(p[3]))
        elif p[0] == "S" and p[2] in names:
            S.setdefault(p[2], []).append((float(p[3]), float(p[4])))
    out = {}
    for c in G["clusters"]:
        nm = c["name"]
        if nm not in S or (nm + "_root/A") not in T:
            raise ValueError("cluster %s: no measured arrivals (root or registers)" % nm)
        if len(S[nm]) != c["n"]:
            raise ValueError("cluster %s: %d measured register pins != %d planned" % (nm, len(S[nm]), c["n"]))
        a_tt, a_ff = T[nm + "_root/A"]
        rec = {}
        for k, C, a in ((0, "TT", a_tt), (1, "FF", a_ff)):
            ins = [v[k] - a for v in S[nm]]
            rec[C] = dict(n=len(ins), mean=round(st.mean(ins), 1), min=round(min(ins), 1), max=round(max(ins), 1))
        out[nm] = rec
    return out


def main(argv):
    if len(argv) >= 4 and argv[0] == "cluster":
        maxd = float(argv[4]) if len(argv) > 4 else 200.0
        maxn = int(argv[5]) if len(argv) > 5 else 1200
        G = cluster(argv[1], maxd, maxn)
        if not any(c.get("ungated") for c in G["clusters"]):
            raise SystemExit("parent_cts cluster: no ungated register on the tile clock port net")
        if not any(not c.get("ungated") for c in G["clusters"]) and not G["kids"]:
            raise SystemExit("parent_cts cluster: no gated sink")
        json.dump(G, open(argv[2], "w"))
        open(argv[3], "w").write(cl_tcl(G))
        print("parent_cts cluster: %d clusters (%d ungated), %d regs, %d kids" % (
            len(G["clusters"]), sum(1 for c in G["clusters"] if c.get("ungated")),
            sum(c["n"] for c in G["clusters"]), len(G["kids"])))
        return 0
    if len(argv) == 4 and argv[0] == "clins":
        G = json.load(open(argv[2]))
        out = clins(argv[1], G)
        json.dump(out, open(argv[3], "w"), indent=0)
        print("parent_cts clins: %d clusters, TT mean %.1f-%.1f" % (
            len(out), min(v["TT"]["mean"] for v in out.values()), max(v["TT"]["mean"] for v in out.values())))
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
