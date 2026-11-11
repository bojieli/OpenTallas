#!/usr/bin/env python3
"""HBM-CHANNELS 11-11: intent sheets (COORD 02:1x INTENT RULE) for the SU-CHAN core moves of q_su11/q_su11pv1/q_su01/q_su01pv1.
  intent_sheet.py BASE_PLAN EVENT_PLAN CORE_CONNS OUT_DIR   -> OUT/<type>.svg, OUT/intent_su_chan.json"""
import json, re, sys, collections
from pathlib import Path
A = json.load(open(sys.argv[1]))["partition_types"]; B = json.load(open(sys.argv[2]))["partition_types"]
CC = json.load(open(sys.argv[3])); OUT = Path(sys.argv[4]); OUT.mkdir(parents=True, exist_ok=True)
TYPES = ["q_su11", "q_su11__physical_v1", "q_su01", "q_su01__physical_v1"]
LBL = {"L5090_o", "L5091_o", "L5093_o", "L5094_o"}
COL = {"exp_l": "#4c78a8", "exp_s": "#f58518", "plain": "#54a24b", "other": "#9d9d9d"}


def role(inst):
    if re.search(r"lane_exp\w*__l$", inst): return "exp_l"
    if re.search(r"lane_exp\w*__s$", inst): return "exp_s"
    if "lanes_plain" in inst: return "plain"
    return "other"


def lane_of(inst): return re.sub(r"__\w+$", "", inst)


def face_xy(face, lo, hi, w, h):
    m = (lo + hi) / 2
    return {"S": (m, 0), "N": (m, h), "W": (0, m), "E": (w, m)}[face]


def svg(tn):
    ta, tb = A[tn], B[tn]; w, h = tb["outline_um"]; s = 0.42; pad = 40
    W, H = w * s + 2 * pad + 60, h * s + 2 * pad + 80
    X = lambda x: pad + x * s; Y = lambda y: pad + (h - y) * s
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" viewBox="0 0 {W:.0f} {H:.0f}" font-family="sans-serif" font-size="9">',
         '<defs><marker id="a" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#333"/></marker>'
         '<marker id="r" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#c0392b"/></marker></defs>',
         f'<rect x="0" y="0" width="{W:.0f}" height="{H:.0f}" fill="#ffffff"/>',
         f'<rect x="{X(0):.1f}" y="{Y(h):.1f}" width="{w*s:.1f}" height="{h*s:.1f}" fill="#fafafa" stroke="#000"/>']
    old = {c["inst"]: c for c in ta["hard_cores"]}
    for c in tb["hard_cores"]:
        oc = old[c["inst"]]; (x0, y0), (cw, ch) = oc["origin_um"], oc["outline_um"]
        o.append(f'<rect x="{X(x0):.1f}" y="{Y(y0+ch):.1f}" width="{cw*s:.1f}" height="{ch*s:.1f}" fill="none" stroke="#bbb" stroke-dasharray="3,2"/>')
    cen = {}
    for c in tb["hard_cores"]:
        (x0, y0), (cw, ch) = c["origin_um"], c["outline_um"]; r = role(c["inst"])
        cen[c["inst"]] = (x0 + cw / 2, y0 + ch / 2)
        o.append(f'<rect x="{X(x0):.1f}" y="{Y(y0+ch):.1f}" width="{cw*s:.1f}" height="{ch*s:.1f}" fill="{COL[r]}" fill-opacity="0.55" stroke="{COL[r]}"/>')
        lab = re.sub(r"^u_su_Q\d_", "", c["inst"]).replace("lane_", "").replace("lanes_", "")
        o.append(f'<text x="{X(x0)+2:.1f}" y="{Y(y0+ch)+10:.1f}">{lab}</text>')
    cc = CC.get(tn, {})
    # same-lane l<->s point-to-point (data: sx_*/y_*), drawn once per pair
    done = set()
    for core, ports in cc.items():
        for port, refs in ports.items():
            if re.search(r"rst|clk", port): continue
            for ref in refs:
                k, _, n = ref.partition(":"); n = n.split(".")[0]
                if k != "core" or n not in cen or core not in cen: continue
                key = tuple(sorted((core, n)))
                if key in done: continue
                done.add(key)
                (x1, y1), (x2, y2) = cen[core], cen[n]
                same = lane_of(core) == lane_of(n)
                col, wd = ("#333", 1.6) if same else ("#54a24b", 0.8)
                if role(core) == "plain" and role(n) == "plain" and abs(x1 - x2) > 1: continue   # plain groups: draw stacks only
                o.append(f'<line x1="{X(x1):.1f}" y1="{Y(y1):.1f}" x2="{X(x2):.1f}" y2="{Y(y2):.1f}" stroke="{col}" stroke-width="{wd}" marker-end="url(#a)"/>')
    # ft pass-through chains (station regs) and internal-station chains to the face
    for sl in tb.get("ft_slots", []):
        pts = sl.get("regs_um", [])
        if len(pts) > 1:
            d = " ".join(f"{X(x):.1f},{Y(y):.1f}" for x, y in pts)
            o.append(f'<polyline points="{d}" fill="none" stroke="#c0392b" stroke-width="1.2" marker-end="url(#r)"/>')
            o.append(f'<text x="{X(pts[-1][0])+3:.1f}" y="{Y(pts[-1][1]):.1f}" fill="#c0392b">{sl["name"]} ({sl.get("stations")} st)</text>')
    for e in tb.get("internal_stations", []):
        if not str(e.get("conn", "")).startswith("bus:"): continue
        pts = [e["from_um"]] + e["regs_um"] + [e["to_um"]]
        if e["conn"].endswith("_o"): pts = pts[::-1]     # dataflow: leaf core -> stations -> output face bus
        d = " ".join(f"{X(x):.1f},{Y(y):.1f}" for x, y in pts)
        o.append(f'<polyline points="{d}" fill="none" stroke="#8e44ad" stroke-width="1.0" stroke-dasharray="4,2" marker-end="url(#a)"/>')
    many = len(tb["buses"]) > 12
    for b in tb["buses"]:
        lo, hi = b.get("window_um", [0, 0]); x, y = face_xy(b["face"], lo, hi, w, h)
        dx, dy = {"S": (0, -1), "N": (0, 1), "W": (-1, 0), "E": (1, 0)}[b["face"]]
        if b["dir"] == "in": x1, y1, x2, y2 = x + dx * 60, y + dy * 60, x, y
        else: x1, y1, x2, y2 = x, y, x + dx * 60, y + dy * 60
        o.append(f'<line x1="{X(x1):.1f}" y1="{Y(y1):.1f}" x2="{X(x2):.1f}" y2="{Y(y2):.1f}" stroke="#1f77b4" stroke-width="2" marker-end="url(#a)"/>')
        if not many or b["name"] in LBL:
            o.append(f'<text x="{X(x2)+2:.1f}" y="{Y(y2)-2:.1f}" fill="#1f77b4">{b["name"]} {b["width"]}b</text>')
    for i, t in enumerate([f"{tn}: SU-CHAN layout. Filled = new origin_um, grey dashed = base 29333b2b. Blue = face buses (arrow = in/out" + ("; only event lanes labelled" if many else "") + ").",
                           "Black = same-lane exp_l -> exp_s point-to-point data (sx_*/ci_sfu/y_*, returns not drawn); plain p0->p3 = chained plain-lane stack.",
                           "Red = pass-through ft chains (station regs, in-face -> out-face); purple dashed = internal-station chains leaf -> output face bus (to hub)."]):
        o.append(f'<text x="{pad}" y="{H-50+i*14:.0f}" font-size="11">{t}</text>')
    o.append("</svg>")
    (OUT / f"{tn}.svg").write_text("\n".join(o))


rows = {}
for tn in TYPES:
    svg(tn)
    ta, tb = A[tn], B[tn]
    old = {c["inst"]: c for c in ta["hard_cores"]}
    # structure invariants: row/column order, l/s abutment
    def order(T, key):
        return [c["inst"] for c in sorted(T["hard_cores"], key=key)]
    same_order_x = order(ta, lambda c: (round(c["origin_um"][1]), c["origin_um"][0])) == order(tb, lambda c: (round(old[c["inst"]]["origin_um"][1]), c["origin_um"][0]))
    rowsets_a = collections.defaultdict(set); rowsets_b = collections.defaultdict(set)
    for c in ta["hard_cores"]: rowsets_a[round(c["origin_um"][1], 2)].add(c["inst"])
    for c in tb["hard_cores"]: rowsets_b[round(c["origin_um"][1], 2)].add(c["inst"])
    same_rows = sorted(map(sorted, rowsets_a.values())) == sorted(map(sorted, rowsets_b.values()))
    abut = []
    for c in tb["hard_cores"]:
        if role(c["inst"]) != "exp_l": continue
        sname = c["inst"][:-1] + "s"; sc = next((x for x in tb["hard_cores"] if x["inst"] == sname), None)
        sa = next((x for x in ta["hard_cores"] if x["inst"] == sname), None); ca = old[c["inst"]]
        if sc is None: continue
        def gap(P, Q):
            if P["origin_um"][0] < Q["origin_um"][0]: return round(Q["origin_um"][0] - P["origin_um"][0] - P["outline_um"][0], 3)
            return round(P["origin_um"][0] - Q["origin_um"][0] - Q["outline_um"][0], 3)
        abut.append(dict(lane=lane_of(c["inst"]), gap_base=gap(ca, sa), gap_new=gap(c, sc), same_row=c["origin_um"][1] == sc["origin_um"][1]))
    rows[tn] = dict(svg=f"{tn}.svg", cores=len(tb["hard_cores"]), row_membership_kept=same_rows, left_to_right_order_kept=same_order_x,
                    exp_l_s_pairs=abut, buses=[(b["name"], b["dir"], b["face"], b["width"]) for b in tb["buses"]],
                    ft_pass_through=[(s["name"], s.get("in_face"), s.get("out_face"), s.get("width"), s.get("stations")) for s in tb.get("ft_slots", [])],
                    ist_bus_chains=[(e["conn"], len(e["regs_um"])) for e in tb.get("internal_stations", []) if str(e.get("conn", "")).startswith("bus:")])
json.dump(rows, open(OUT / "intent_su_chan.json", "w"), indent=1)
for k, v in rows.items():
    print(k, "rows kept", v["row_membership_kept"], "order kept", v["left_to_right_order_kept"],
          "l/s gaps base->new", sorted({(p["gap_base"], p["gap_new"]) for p in v["exp_l_s_pairs"]}))
