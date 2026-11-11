#!/usr/bin/env python3
"""CPL-HBM-2 INTENT SHEET (COORD 02:1x rule) for one partition type and one placement (base or event cores_after).
(1) dataflow chain: input face windows -> cores (pipeline order = BFS from the input faces over directed links)
    -> output face windows; link roles: broadcast (one face bus/core output reaching >= 3 cores), p2p,
    pass-through (ft slots), serialisable (<= 4 bits). Links from core_conns (HBM SU/SP: netlist cone walk) + plan
    internal_stations + ft_slots.
(2) timing-critical pairs: plan stations (registered links; hop length / reach) and direct links at >= 80 % of
    their core_place timing limit after the move.
(3) SVG: outline, face windows, cores in chain order with dataflow arrows (width ~ bits, colour = role).
usage: intent.py REPO PLAN TYPE OUT_PREFIX [EV.json]"""
import collections, json, math, sys
from pathlib import Path
repo, plan, tn, out = sys.argv[1:5]
evp = sys.argv[5] if len(sys.argv) > 5 else None
sys.path.insert(0, repo + "/tools/die_plan")
import core_place as CP, route_supply as RS
P = json.load(open(plan)); t = P["partition_types"][tn]
RS.REF_DIRS[:] = [str(Path(plan).parent)]
conns = RS.load_conns(Path(plan).parent, None, Path(plan).parent, [])
cfg = dict(gap=34.56, sweeps=0, topk=4, lam=4.0, reach=360.0, grid_um=21.6, grt_halving="full", fixed_re="", rs=dict(RS.DEFAULTS), timing="class")
M = CP.TypeModel(tn, t, Path(plan).parent, Path(repo), conns, cfg)
M.init_limits()
if evp:
    # set positions exactly (no legalisation: base slivers stay as the event left them)
    done = set()
    for inst, v in json.load(open(evp))["rows"][0]["cores_after"].items():
        i = M.idx[inst]; k = M.cid[i]
        if k in done:
            continue
        done.add(k)
        if len(M.CL[k]) == 1:
            M.cflip[k] = CP.comp(M.ori0[i], v["orient"])
        ox, oy = M.coff[i]
        M.cpos[k] = (CP.snap(v["origin_um"][0] - ox), CP.snap(v["origin_um"][1] - oy))
    for i in range(M.n):
        ev_o = json.load(open(evp))["rows"][0]["cores_after"][M.inst[i]]["origin_um"] if False else None
W, H = M.W, M.H
bus = {b["name"]: b for b in t.get("buses", [])}
# --- links per (src, dst) with direction
links = collections.defaultdict(float)
roles = {}
fan = collections.defaultdict(set)
for q, (a, b, w, kind) in enumerate(M.L):
    lab = M.Llab[q]
    if kind == "station":
        continue
    src = M.inst[a[0]]
    if kind == "core":
        dst = M.inst[b[0]]
        links[(src, dst)] += w
    else:
        bn = lab.split("->bus:")[-1] if "->bus:" in lab else lab.split("->")[-1]
        bb = bus.get(bn, {})
        if bb.get("dir") == "in":
            links[("in:" + bn, src)] += w; fan["in:" + bn].add(src)
        else:
            links[(src, "out:" + bn)] += w
# registered links (plan internal_stations): face window <-> core, drawn dashed with their register count
stl = collections.defaultdict(lambda: [0.0, 0])
for (si, q, nreg) in M.stations:
    st_ = t["internal_stations"][si]
    la, ca = str(st_.get("launch", "")), str(st_.get("capture", ""))
    def nm(x):
        if x.startswith("face bus "):
            b_ = x[9:]
            return ("in:" if bus.get(b_, {}).get("dir") == "in" else "out:") + b_
        return x.split(".")[0] if x.split(".")[0] in M.idx else None
    a_, c_ = nm(la), nm(ca)
    if a_ is None or c_ is None:
        continue
    # dataflow direction: in-bus -> core, core -> out-bus
    if a_.startswith("out:"):
        a_, c_ = c_, a_
    if c_.startswith("in:"):
        a_, c_ = c_, a_
    stl[(a_, c_)][0] += float(st_.get("bits", 1)); stl[(a_, c_)][1] = max(stl[(a_, c_)][1], nreg)
for (s, d), w in links.items():
    if s.startswith("in:") and len(fan[s]) >= 3:
        roles[(s, d)] = "broadcast"
    elif w <= 4:
        roles[(s, d)] = "serialisable"
    else:
        roles[(s, d)] = "p2p"
# --- chain order: BFS from input faces
order, seen = [], set()
lvl = {}
front = sorted({d for (s, d) in links if s.startswith("in:")})
for c in front:
    lvl[c] = 1
while front:
    nxt = []
    for c in front:
        if c in seen:
            continue
        seen.add(c); order.append(c)
        for (s, d) in links:
            if s == c and not d.startswith("out:") and d not in seen:
                lvl.setdefault(d, lvl[c] + 1); nxt.append(d)
    front = nxt
for i in M.inst:
    if i not in seen:
        order.append(i); lvl.setdefault(i, 0)
# --- critical
crit = []
for (si, q, nreg) in M.stations:
    s = t["internal_stations"][si]
    ln = M.llen(q)
    hop = ln / (nreg + 1)
    crit.append(dict(kind="station", link="%s -> %s" % (s.get("launch"), s.get("capture")), bits=s.get("bits"),
                     regs=nreg, len_um=round(ln, 1), hop_um=round(hop, 1), hop_over_reach=round(hop / 360.0, 2)))
for q, (a, b, w, kind) in enumerate(M.L):
    if kind != "station" and M.llen(q) >= 0.8 * M.maxlen[q]:
        crit.append(dict(kind=kind, link=M.Llab[q], bits=w, len_um=round(M.llen(q), 1), limit_um=round(M.maxlen[q], 1),
                         ratio=round(M.llen(q) / M.maxlen[q], 2)))
crit.sort(key=lambda c: -(c.get("hop_over_reach") or c.get("ratio") or 0))
ft = [dict(name=f["name"], bits=f.get("width"), path="%s%s -> %s%s" % (f["in_face"], f.get("in_window_um"), f["out_face"], f.get("out_window_um")),
           stations=f.get("stations"), role="pass-through") for f in t.get("ft_slots", [])]
sheet = dict(type=tn, plan=plan, placement=evp or "base", outline_um=[W, H],
             chain=[dict(core=c, stage=lvl.get(c), module=M.C[M.idx[c]]["module"] if c in M.idx else None,
                         origin_um=[round(v, 2) for v in M.core_origin(M.idx[c])], orient=M.core_orient(M.idx[c]))
                    for c in order if c in M.idx],
             links=sorted([dict(src=s, dst=d, bits=round(w), role=roles[(s, d)]) for (s, d), w in links.items()] +
                          [dict(src=s, dst=d, bits=round(v[0]), role="registered p2p (%d regs)" % v[1]) for (s, d), v in stl.items()],
                          key=lambda x: -x["bits"]),
             pass_through=ft, critical=crit[:40])
Path(out + ".json").write_text(json.dumps(sheet, indent=1))
# --- SVG
S = 900.0 / max(W, H); pad = 60
X = lambda x: pad + x * S; Y = lambda y: pad + (H - y) * S
col = dict(broadcast="#d62728", p2p="#1f77b4", serialisable="#7f7f7f")
o = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" font-family="sans-serif" font-size="10">' % (W * S + 2 * pad + 260, H * S + 2 * pad),
     '<defs>%s</defs>' % "".join('<marker id="a%s" markerUnits="userSpaceOnUse" markerWidth="10" markerHeight="10" refX="9" refY="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="%s"/></marker>' % (k, v) for k, v in col.items()),
     '<rect x="0" y="0" width="100%" height="100%" fill="white"/>',
     '<text x="%d" y="20" font-size="14">%s INTENT (%s): dataflow chain, arrows = links (width ~ bits; red broadcast, blue p2p, grey serialisable), green = ft pass-through, brown dashed = registered station links (bits, regs)</text>' % (pad, tn, "after" if (evp or "/plan_" in plan) else "base"),
     '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="none" stroke="black"/>' % (X(0), Y(H), W * S, H * S)]
for f in t.get("ft_slots", []):
    a = RS.face_point(W, H, f["in_face"], f.get("in_window_um")); b = RS.face_point(W, H, f["out_face"], f.get("out_window_um"))
    o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#2ca02c" stroke-dasharray="4,3" stroke-width="%.1f" opacity="0.6"/>' % (X(a[0]), Y(a[1]), X(b[0]), Y(b[1]), 1 + math.log10(1 + f.get("width", 1))))
for b in t.get("buses", []):
    if not b.get("face") or not b.get("window_um"):
        continue
    w0, w1 = b["window_um"]; f = b["face"]
    if f in "NS":
        y = H if f == "N" else 0
        o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="5"/>' % (X(w0), Y(y), X(w1), Y(y), "#9467bd" if b.get("dir") == "in" else "#ff7f0e"))
        o.append('<text x="%.1f" y="%.1f" font-size="8">%s %s</text>' % (X(w0), Y(y) + (12 if f == "S" else -4), b["name"], b.get("width")))
    else:
        x = W if f == "E" else 0
        o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="5"/>' % (X(x), Y(w0), X(x), Y(w1), "#9467bd" if b.get("dir") == "in" else "#ff7f0e"))
        o.append('<text x="%.1f" y="%.1f" font-size="8">%s %s</text>' % (X(x) + (4 if f == "E" else -60), Y(w0), b["name"], b.get("width")))
cen = {}
for i in range(M.n):
    x, y = M.core_origin(i); w, h = M.dim[i]
    cen[M.inst[i]] = (x + w / 2, y + h / 2)
    o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#aec7e8" stroke="black" opacity="0.8"/>' % (X(x), Y(y + h), w * S, h * S))
    o.append('<text x="%.1f" y="%.1f" font-size="8">%s [s%s]</text>' % (X(x) + 2, Y(y + h) + 10, M.inst[i].replace("u_su_", "")[-26:], lvl.get(M.inst[i])))
def ep(n):
    if n.startswith(("in:", "out:")):
        b = bus.get(n.split(":", 1)[1], {})
        return RS.face_point(W, H, b.get("face", "S"), b.get("window_um")) if b.get("face") else None
    return cen.get(n)
for (s, d), w in sorted(links.items(), key=lambda x: x[1]):
    a, b = ep(s), ep(d)
    if not a or not b or w < 1:
        continue
    r = roles[(s, d)]
    o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="%.2f" opacity="0.55" marker-end="url(#a%s)"/>' % (X(a[0]), Y(a[1]), X(b[0]), Y(b[1]), col[r], 0.5 + 2.2 * math.log10(1 + w), r))
for (s, d), v in stl.items():
    a, b = ep(s), ep(d)
    if not a or not b:
        continue
    o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#8c564b" stroke-dasharray="6,3" stroke-width="%.2f" opacity="0.7" marker-end="url(#ap2p)"/>' % (X(a[0]), Y(a[1]), X(b[0]), Y(b[1]), 0.5 + 2.2 * math.log10(1 + v[0])))
    o.append('<text x="%.1f" y="%.1f" font-size="8" fill="#8c564b">%s %db %dr</text>' % (X((a[0] + b[0]) / 2), Y((a[1] + b[1]) / 2), (d if s.startswith("in:") or s in M.idx and d.startswith("out:") and False else (s if s.startswith("in:") else d)).split(":")[-1], v[0], v[1]))
ty = 40
for c in crit[:14]:
    o.append('<text x="%.1f" y="%d" font-size="9">%s %s %s</text>' % (W * S + pad + 10, ty, c["kind"], c["link"][:40], c.get("hop_over_reach") or c.get("ratio")))
    ty += 13
o.append("</svg>")
Path(out + ".svg").write_text("\n".join(o))
print(tn, "cores", M.n, "links", len(links), "stations", len(M.stations), "ft", len(ft), "crit", len(crit))
