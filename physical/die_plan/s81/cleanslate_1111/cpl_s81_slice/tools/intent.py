#!/usr/bin/env python3
"""CPL-S81-SLICE INTENT SHEET (COORD 02:1x intent rule) per type: dataflow chain from the bound netlist + LEF pin
directions + plan buses/stations, link roles, timing-critical pairs (plan stations + links beyond the 396.9-um
reach), an SVG of the layout with dataflow arrows, and a structure check that the delta follows the chain.
usage: intent.py PLAN OUTDIR TYPE...   (reads fin/<type>.json for the delta; writes OUTDIR/<type>.json/.svg)"""
import json
import math
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cpl  # noqa: E402
import common  # noqa: E402

REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "repo")
REACH = 396.9
_dirc = {}


def lef_dirs(lef):
    if lef in _dirc:
        return _dirc[lef]
    d = {}
    for p in (os.path.join(REPO, lef), os.path.join(REPO, "physical/die_plan/s81", lef)):
        if os.path.exists(p):
            txt = open(p, errors="ignore").read()
            for m in re.finditer(r"\n\s*PIN\s+(\S+)(.*?)\n\s*END\s+\1", txt, flags=re.S):
                dm = re.search(r"DIRECTION\s+(\w+)", m.group(2))
                if dm:
                    d[re.sub(r"\[.*$", "", m.group(1))] = dm.group(1).upper()
            break
    _dirc[lef] = d
    return d


def short(inst):
    return inst.replace("u_bound.", "").replace("u_c.", "").replace("u_u_", "")


def build(P, conns, n):
    M = common.model(P, conns, n)
    fin = json.load(open(os.path.join(os.environ.get("FIN", "fin"), "%s.json" % n)))
    pl0 = M.current()
    pl1 = list(pl0)
    for inst, v in (fin.get("delta") or {}).items():
        pl1[M.ix[inst]] = (v[0], v[1], v[2])
    dirs = [lef_dirs(h.get("lef", "")) for h in M.cores]
    cname = [short(h["inst"]) for h in M.cores]

    def node(b):
        if b[0] == "face":
            return "face:" + b[1]
        if b[0] == "core":
            return "core:" + cname[b[1]]
        if b[0] == "pt":
            return "macros@%d,%d" % (round(b[1][0]), round(b[1][1]))
        return "glue:" + b[1]
    E = defaultdict(lambda: dict(bits=0, links=[]))
    for l in M.links:
        i, port = l["a"]
        a = "core:" + cname[i]
        b = node(l["b"])
        dr = dirs[i].get(port or "", "")
        if l["b"][0] == "face":
            bd = M.buses[l["b"][1]].get("dir", "")
            src, dst = (b, a) if bd == "in" else (a, b)
        elif dr == "OUTPUT":
            src, dst = a, b
        elif dr == "INPUT":
            src, dst = b, a
        else:
            src, dst = (a, b) if a < b else (b, a)
        e = E[(src, dst)]
        e["bits"] += l["bits"]
        e["links"].append(l)
    # roles: per source port fanout
    fan = defaultdict(set)
    for (s, d), e in E.items():
        for l in e["links"]:
            fan[(s, l["a"][1])].add(d)
    edges = []
    for (s, d), e in sorted(E.items(), key=lambda kv: -kv[1]["bits"]):
        kinds = set(l["kind"] for l in e["links"])
        if "st" in kinds:
            role = "p2p (staged station)"
        elif e["bits"] <= 4:
            role = "serialisable (control/status)"
        elif any(len(fan[(s, l["a"][1])]) >= 2 for l in e["links"]):
            role = "broadcast"
        else:
            role = "p2p"

        def ln(pl):
            c = {}
            return sum(cpl.man(*M.link_pts(l, pl, c)) * l["bits"] for l in e["links"]) / max(1, sum(l["bits"] for l in e["links"]))
        edges.append(dict(src=s, dst=d, bits=e["bits"], role=role, len_before=round(ln(pl0)), len_after=round(ln(pl1))))
    # pass-through ft slots
    for f in M.ft:
        edges.append(dict(src="face:%s" % f.get("in_face"), dst="face:%s" % f.get("out_face"), bits=f.get("bits"),
                          role="pass-through (ft %s, %d stations)" % (f.get("name"), len(f.get("regs_um") or [])),
                          len_before=None, len_after=None))
    # pipeline layers: BFS from input faces over directed core edges
    adj = defaultdict(set)
    for e in edges:
        if e["len_before"] is not None:
            adj[e["src"]].add(e["dst"])
    lev = {}
    frontier = [k for k in adj if k.startswith("face:")]
    for k in frontier:
        lev[k] = 0
    while frontier:
        nxt = []
        for u in frontier:
            for v in adj[u]:
                if v not in lev:
                    lev[v] = lev[u] + 1
                    nxt.append(v)
        frontier = nxt
    chain = sorted(((lev.get("core:" + c, 99), c) for c in cname))
    # structure check: projection of cores on the in-face -> out-face axis vs pipeline level
    ins = [M.win_pt(b) for b, v in M.buses.items() if v.get("dir") == "in"]
    outs = [M.win_pt(b) for b, v in M.buses.items() if v.get("dir") == "out"]

    def cen(ps):
        return (sum(p[0] for p in ps) / len(ps), sum(p[1] for p in ps) / len(ps)) if ps else (M.W / 2, M.H / 2)
    ci, co = cen(ins), cen(outs)
    ax = (co[0] - ci[0], co[1] - ci[1])
    nrm = math.hypot(*ax) or 1.0

    def corr(pl):
        xs, ys = [], []
        for i in range(len(M.cores)):
            lv = lev.get("core:" + cname[i])
            if lv is None:
                continue
            r = M.rect(i, pl)
            c = ((r[0] + r[2]) / 2 - ci[0], (r[1] + r[3]) / 2 - ci[1])
            xs.append(lv)
            ys.append((c[0] * ax[0] + c[1] * ax[1]) / nrm)
        if len(set(xs)) < 2:
            return None
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        sxy = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
        sx = math.sqrt(sum((a - mx) ** 2 for a in xs))
        sy = math.sqrt(sum((b - my) ** 2 for b in ys))
        return round(sxy / (sx * sy), 3) if sx and sy else None
    # timing-critical: plan stations + links beyond reach
    crit = []
    for s in M.st:
        e = M.t["internal_stations"][s["si"]]
        crit.append(dict(kind="plan station", conn=e.get("conn"), launch=e.get("launch"), capture=e.get("capture"),
                         stages=s["n"], bits=s["bits"]))
    for e in edges:
        if e["len_before"] is not None and (e["len_after"] > REACH or e["len_before"] > REACH) and e["bits"] > 4:
            crit.append(dict(kind="link beyond 396.9-um reach", src=e["src"], dst=e["dst"], bits=e["bits"],
                             len_before=e["len_before"], len_after=e["len_after"]))
    worse = [e for e in edges if e["len_before"] is not None and e["bits"] >= 32 and e["len_after"] > 1.2 * e["len_before"] + 20]
    res = dict(type=n, bound_src=M.bound_src, chain=[dict(level=l, core=c) for l, c in chain], edges=edges,
               critical=crit, flow_axis=dict(in_centroid=ci, out_centroid=co),
               chain_order_corr_before=corr(pl0), chain_order_corr_after=corr(pl1),
               edges_longer_after=[(e["src"], e["dst"], e["bits"], e["len_before"], e["len_after"]) for e in worse],
               moved=len(fin.get("delta") or {}))
    return M, pl0, pl1, res, cname


COL = {"broadcast": "#d62728", "p2p": "#1f77b4", "p2p (staged station)": "#9467bd", "serialisable (control/status)": "#7f7f7f"}


def svg(M, pl, res, cname, out, title):
    S = 900.0 / max(M.W, M.H)
    W, H = M.W * S + 40, M.H * S + 80

    def X(x):
        return 20 + x * S

    def Y(y):
        return 60 + (M.H - y) * S
    o = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" font-family="sans-serif" font-size="10">' % (W, H),
         '<defs><marker id="ar" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L7,3 L0,6 z" fill="context-stroke"/></marker></defs>',
         '<rect width="100%" height="100%" fill="white"/>',
         '<text x="20" y="18" font-size="13">%s</text>' % title,
         '<text x="20" y="34">dataflow arrows: red broadcast, blue p2p, purple staged station, grey control; width ~ bits; number = pipeline level from input faces</text>',
         '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="none" stroke="black"/>' % (X(0), Y(M.H), M.W * S, M.H * S)]
    for f in M.fixed:
        o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#e0e0e0" stroke="#bbb" stroke-width="0.3"/>' % (
            X(f[0]), Y(f[3]), (f[2] - f[0]) * S, (f[3] - f[1]) * S))
    for b, v in M.buses.items():
        p = M.win_pt(b)
        c = "#2ca02c" if v.get("dir") == "in" else "#ff7f0e"
        o.append('<circle cx="%.1f" cy="%.1f" r="4" fill="%s"/><text x="%.1f" y="%.1f" fill="%s">%s %s %db</text>' % (
            X(p[0]), Y(p[1]), c, X(p[0]) + 5, Y(p[1]) - 3, c, b, v.get("dir"), v.get("width", 1)))
    lev = {c["core"]: c["level"] for c in res["chain"]}
    cen = {}
    for i in range(len(M.cores)):
        r = M.rect(i, pl)
        cen["core:" + cname[i]] = ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)
        o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#cfe2ff" stroke="#1f3b73"/>' % (
            X(r[0]), Y(r[3]), (r[2] - r[0]) * S, (r[3] - r[1]) * S))
        o.append('<text x="%.1f" y="%.1f">%s [L%s] %s</text>' % (X(r[0]) + 2, Y(r[3]) + 11, cname[i], lev.get(cname[i], "?"), pl[i][2]))
    for b in M.buses:
        cen["face:" + b] = M.win_pt(b)
    top = [e for e in res["edges"] if e["len_before"] is not None][:40]
    mx = max([e["bits"] for e in top] + [1])
    for e in top:
        a, b = cen.get(e["src"]), cen.get(e["dst"])
        if not a or not b:
            continue
        w = 0.6 + 5.0 * e["bits"] / mx
        o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="%.1f" opacity="0.7" marker-end="url(#ar)"/>' % (
            X(a[0]), Y(a[1]), X(b[0]), Y(b[1]), COL.get(e["role"], "#1f77b4"), w))
    o.append("</svg>")
    open(out, "w").write("\n".join(o))


def main():
    P, conns = cpl.load(sys.argv[1])
    od = sys.argv[2]
    os.makedirs(od, exist_ok=True)
    for n in sys.argv[3:]:
        M, pl0, pl1, res, cname = build(P, conns, n)
        json.dump(res, open(os.path.join(od, n + ".json"), "w"), indent=1)
        svg(M, pl1, res, cname, os.path.join(od, n + "_after.svg"), n + " AFTER (delta) dataflow")
        svg(M, pl0, res, cname, os.path.join(od, n + "_before.svg"), n + " BEFORE (plan 99f40d35) dataflow")
        print(n, "chain", [(c["level"], c["core"]) for c in res["chain"]][:12], "corr", res["chain_order_corr_before"],
              "->", res["chain_order_corr_after"], "crit", len(res["critical"]), "longer", res["edges_longer_after"][:4], flush=True)


if __name__ == "__main__":
    main()
