#!/usr/bin/env python3
"""CLOCK-128-R5: the plan-fixed die clock as REGULAR nets with locked (FIXED) dbWire routes, so OpenRCX extracts it.

R4 drew every tree net (root, H-tree legs, nodes, leaves, stubs) as a special net of SBoxes: DRT never routes special
nets and RCX never extracts them, so the only RC was the tool's own geometry SPEF.  Here every net of
``mesh.json["fixed_wires"]`` (die_clock_128.fixed_wires: trunk + drops, on PG-aware M8/M9 tracks) becomes one FIXED
dbWire of the net, under the clock NDR (M8/M9 width 0.16):

  * the planned M8/M9 legs are drawn EXACTLY (same layer, centre line, extent; no moved leg, no moved repeater);
  * each cell pin gets a plan-computed pin-access stack below the leg end (rule-based, never measured): leg end ->
    VIA89/VIA78 ... VIA12 staircase with one min-area step per layer M8..M4, an M3 riser to the pin-access row and an
    M2 run to the pin's M1 bar (BUFx24 A at x 0.027, Y at x 1.593; distinct access rows so A and Y never share M2);
  * port endpoints (die input root, lattice leaf taps) join the BTerm on the pin layer;
  * the VSS shields stay special wires (unchanged), the shield-spacing obstructions are kept for GRT and listed so the
    route step can delete them before DRT (DRT sees the real wires instead).

OpenROAD treats a regular net that already carries a FIXED wire as routed: GRT skips it and DRT keeps it untouched
(measured on a 3-cell probe, CLOCK-128-R5), so the drawn geometry is what RCX extracts.  ``plan_check`` proves that
geometry equals the plan from the routed DEF (every planned M8/M9 leg present at its exact centre line and extent,
no other M8/M9 clock metal except the listed pin-access steps / port joins, every cell at its plan location).

Reusable: nothing here is QC- or lattice-specific; any build whose mesh.json carries fixed_wires (the full die tree
once the region plan lands) goes through the same emitter, route step and check.
"""
import math
import re
from collections import defaultdict

BUF_DEFAULT = "BUFx24_ASAP7_75t_R"
DBU = 1000                       # ASAP7 1x LEF database units per micron
# BUFx24_ASAP7_75t_R (asap7sc7p5t_28_R_1x_220121a.lef), R0, cell-local um: pin-access point on the pin's M1 bar.
# A: vertical bar x 0.018-0.036, y 0.027-0.243.  Y: vertical bar x 1.584-1.602, y 0.027-0.243.
# Access rows differ (A 0.090, Y 0.180) so the two M2 runs of one cell are 0.072 apart (M2 space 0.018).
# Every die_clock_128.STUB_SIZES cell: A bar x 0.018-0.036 (y >= 0.063-0.207), Y bar = the cell's right vertical bar.
PIN_ACCESS = {f"BUFx{k}_ASAP7_75t_R": {"A": (0.027, 0.090), "Y": (yx, 0.180)}
              for k, yx in (("4", 0.348), ("6f", 0.513), ("8", 0.621), ("12f", 0.945), ("16f", 1.161), ("24", 1.593))}
ROW_H = 0.27
# per-layer minimum step (um) along the preferred direction; each is >= the LEF AREA / default width
# (M8 NDR 0.16 wide, M7/M6 0.032: 0.0021875 -> 0.07, M5/M4 0.024: 0.002 -> 0.084, M3/M2 0.018: 0.000666 -> 0.037)
STEP = {"M8": 0.20, "M7": 0.08, "M6": 0.08, "M5": 0.096, "M4": 0.096, "M3": 0.05, "M2": 0.05}
LAYERS = ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9"]
VIA = {("M1", "M2"): "VIA12", ("M2", "M3"): "VIA23", ("M3", "M4"): "VIA34", ("M4", "M5"): "VIA45",
       ("M5", "M6"): "VIA56", ("M6", "M7"): "VIA67", ("M7", "M8"): "VIA78", ("M8", "M9"): "VIA89"}
HORIZ = {"M2", "M4", "M6", "M8"}


def via(a, b):
    return VIA[tuple(sorted((a, b), key=LAYERS.index))]


def q(v):
    """um -> dbu integer"""
    return int(round(v * DBU))


def pin_point(cells, c, pin, lib):
    v = cells[c]
    acc = PIN_ACCESS.get(lib)
    if acc is None:
        raise ValueError(f"clock_routed: no pin-access model for {lib} ({c})")
    lx, ly = acc[pin]
    o = v.get("orient", "R0")
    if o == "MX":
        ly = ROW_H - ly
    elif o != "R0":
        raise ValueError(f"clock_routed: orient {o} of {c} not modelled")
    return round(v["x"] + lx, 4), round(v["y"] + ly, 4)


def _toward(d, step, keep):
    """signed step on one axis: reach the target leaving `keep` for the next layer when far enough, else step away"""
    s = 1.0 if d >= 0 else -1.0
    if abs(d) >= step + keep:
        return d - s * keep
    return -s * step


def stair(top, ax, ay, px, py):
    """plan-computed pin access from a leg end (ax, ay) on layer `top` (M8 or M9) down to the M1 pin point (px, py).
    Returns [(layer, x, y)]: the vertex after each step, layer = the layer that step is drawn on; consecutive entries
    on different layers are joined by the via between them (at the earlier vertex)."""
    x, y = ax, ay
    out = [(top, x, y)]
    sx = 1.0 if px >= x else -1.0
    sy = 1.0 if py >= y else -1.0
    if top == "M9":
        out.append(("M8", x, y))
        x += sx * STEP["M8"]
        out.append(("M8", x, y))
    out.append(("M7", x, y))
    y += sy * STEP["M7"]
    out.append(("M7", x, y))
    out.append(("M6", x, y))
    x += sx * STEP["M6"]
    out.append(("M6", x, y))
    out.append(("M5", x, y))
    y += _toward(py - y, STEP["M5"], STEP["M3"])
    out.append(("M5", x, y))
    out.append(("M4", x, y))
    x += _toward(px - x, STEP["M4"], STEP["M2"])
    out.append(("M4", x, y))
    out.append(("M3", x, y))
    out.append(("M3", x, py))
    out.append(("M2", x, py))
    out.append(("M2", px, py))
    out.append(("M1", px, py))
    return [(L, round(a, 4), round(b, 4)) for L, a, b in out]


LAYER_ORDER = ("M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9")
_JD = [0]


def _emit_steps(L, pts, final_junction=False, split_down=False):
    """encoder calls for a vertex list (as from stair): via on a layer change, a point on a move.
    The clock NDR (0.16 um) applies on M8/M9 only: an encoder path keeps the rule it was opened with, so the path is
    split at every VIA78 -- above it a path under the NDR layer rule, below it a default-width path (a lower-layer
    path under the NDR gets zero width: DRT check_drc Min Area on every via pad, CLOCK-128-R5 first run).
    final_junction: the last op becomes `set jt [...]` (the trunk-tap junction) and is never followed by a split.
    split_down (CLOCK-128-R8, --stack-r8): every DOWNWARD via is a junction split (`set jdN [via]`, `newPath $jdN`).
    odb's own decoder places a shape after a downward via on the lower layer, but DRT's dbWire reader (check_drc)
    puts the next RECT / segment on the via's TOP layer; a path opened at the via junction is read on the right layer
    by both (CLOCK-128-R8 e8/e12: 23 -> 1 markers on one stack, port jog M9 shorts gone), geometry unchanged."""
    pts = [(l_, round(a, 4), round(b, 4)) for l_, a, b in pts]
    steps = list(zip(pts, pts[1:]))
    for k, ((l0, x0, y0), (l1, x1, y1)) in enumerate(steps):
        last = k == len(steps) - 1
        if l0 != l1:
            assert (x0, y0) == (x1, y1), (l0, l1, x0, y0, x1, y1)
            op = f"$e addTechVia [V {via(l0, l1)}]"
            if {l0, l1} == {"M7", "M8"} and not (last and final_junction):
                L.append(f"set jv [{op}]")
                L.append("$e newPath $jv FIXED" + (" [RL M8]" if l1 == "M8" else ""))
                continue
            if split_down and LAYER_ORDER.index(l1) < LAYER_ORDER.index(l0) and not (last and final_junction):
                _JD[0] += 1
                L.append(f"set jd{_JD[0]} [{op}]")
                L.append(f"$e newPath $jd{_JD[0]} FIXED" + (f" [RL {l1}]" if l1 in ("M8", "M9") else ""))
                continue
            L.append(op)
        elif (x0, y0) != (x1, y1):
            assert x0 == x1 or y0 == y1, ("non-Manhattan step", pts)
            L.append(f"$e addPoint {q(x1)} {q(y1)}")
    if final_junction:
        L[-1] = f"set jt [{L[-1]}]"


def net_plan(w, cells, ports, buf):
    """one fixed tree net -> dict(trunk=(layer, axis_val, lo, hi), drv=..., loads=[...]) with every endpoint resolved:
    cell pins -> ('cell', inst, pin, stair vertices) ; ports -> ('port', name, pin_layer, (x, y))"""
    horiz = w["horiz"]
    tl, bl = ("M8", "M9") if horiz else ("M9", "M8")
    segs = [tuple(s) for s in w["segs"]]
    trunk = [s for s in segs if s[0] == tl and ((s[2] == s[4]) if horiz else (s[1] == s[3]))]
    t0 = tuple(w["trunk_tap"])
    if len(trunk) > 1:
        raise ValueError(f"clock_routed: {w['name']}: {len(trunk)} trunk segments")
    if trunk:
        s = trunk[0]
        lo, hi = (min(s[1], s[3]), max(s[1], s[3])) if horiz else (min(s[2], s[4]), max(s[2], s[4]))
    else:
        lo = hi = t0[0] if horiz else t0[1]
    ax = 0 if horiz else 1

    def end(p, at, layer):
        if p.startswith("port:"):
            pt = ports[p[5:]]
            return ("port", p[5:], pt["layer"], tuple(pt["xy"]), at, layer)
        lib = cells[p].get("lib", buf)
        return ("cell", p, None, None, at, layer)
    drv = end(w["drv"], t0, tl)
    loads = []
    for ld, bx, by in w["branches"]:
        root = (bx, t0[1]) if horiz else (t0[0], by)
        if abs(root[0] - bx) + abs(root[1] - by) > 1e-6:
            loads.append(end(ld, (bx, by), bl) + (root,))
        else:
            loads.append(end(ld, (bx, by), tl) + (root,))
    return dict(name=w["name"], horiz=horiz, tl=tl, bl=bl, lo=lo, hi=hi, tap=t0, ax=ax, drv=drv, loads=loads)


def _port_join(L, layer_at, at, pin_layer, pxy, entering):
    """join a leg end `at` (on layer_at) to a port pin at pxy on pin_layer with straight top-layer moves.
    entering=True: path starts at the port (driver port) and ends at the leg end; else leg end -> port."""
    pts = []
    if entering:
        pts.append((pin_layer, pxy[0], pxy[1]))
        cur = pin_layer
        if pxy != at:
            # one straight move on the pin layer, then switch
            if not (pxy[0] == at[0] or pxy[1] == at[1]):
                raise ValueError(f"clock_routed: port {pxy} not axis-aligned with leg end {at}")
            pts.append((pin_layer, at[0], at[1]))
        if cur != layer_at:
            pts.append((layer_at, at[0], at[1]))
    else:
        pts.append((layer_at, at[0], at[1]))
        if layer_at != pin_layer:
            pts.append((pin_layer, at[0], at[1]))
        if pxy != at:
            if not (pxy[0] == at[0] or pxy[1] == at[1]):
                raise ValueError(f"clock_routed: port {pxy} not axis-aligned with leg end {at}")
            pts.append((pin_layer, pxy[0], pxy[1]))
    return pts


def _stack_pad():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import die_clock_128 as C128
    return C128.STACK_PAD


def stack_down(s):
    """vertices of one CLOCK-128-R7 pin stack (die_clock_128 stacks[] entry) from the M8 junction over the bar down to
    M1: VIA78 at the junction, the M7 riser along the bar column to the pin row, then VIA67..VIA12 straight down"""
    x, py = round(s["xy"][0], 4), round(s["xy"][1], 4)
    jy = round(s["riser_from"][1], 4)
    pts = [("M8", x, jy), ("M7", x, jy)]
    if jy != py:
        pts.append(("M7", x, py))
    return pts + [(L_, x, py) for L_ in ("M6", "M5", "M4", "M3", "M2", "M1")]


def stack_pad_layers(s):
    """{(x, y): set(layers)} of the min-area pads of one stack (M2..M6 at the pin row)"""
    return {(round(s["xy"][0], 4), round(s["xy"][1], 4)): {"M2", "M3", "M4", "M5", "M6"}}


def _emit_stack(L, pts, pads, final_junction=False, split_down=False):
    """_emit_steps + one centred min-area pad (dbWireEncoder addRect) after every via that lands on a pad layer at a
    stack point.  pads: {(x, y): set(layers)}."""
    P = _stack_pad()
    tmp = []
    _emit_steps(tmp, pts, final_junction=final_junction, split_down=split_down)
    # re-walk the vertices to know where each via op lands
    vs = [(l_, round(a, 4), round(b, 4)) for l_, a, b in pts]
    lands = [(l1, (x1, y1)) for (l0, x0, y0), (l1, x1, y1) in zip(vs, vs[1:]) if l0 != l1]
    k = 0
    for s in tmp:
        L.append(s)
        if "addTechVia" in s:
            l1, xy = lands[k]
            k += 1
            if l1 in pads.get(xy, ()) and not s.startswith("set jt"):
                hx, hy = P[l1]
                L.append(f"$e addRect {-q(hx)} {-q(hy)} {q(hx)} {q(hy)}")
    # a pad emitted between 'set jv [VIA78]' and its 'newPath $jv' belongs after the new path is opened
    # move pads that were emitted between 'set jv [VIA78]' and its 'newPath $jv' after the newPath
    i = 0
    while i < len(L) - 2:
        if ((L[i].startswith("set jv [") and L[i + 2].startswith("$e newPath $jv"))
                or (L[i].startswith("set jd") and L[i + 2].startswith("$e newPath $jd"))) \
                and L[i + 1].startswith("$e addRect"):
            L[i + 1], L[i + 2] = L[i + 2], L[i + 1]
            i += 3
        else:
            i += 1


def _stack_net_tcl(L, w, ports, rec):
    """one pin-stack wire (die_clock_128._fixed_wires_stack) -> encoder Tcl appended to L"""
    nm = w["name"]
    horiz = w["horiz"]
    r8 = w.get("enc") == "r8"
    tl, bl = ("M8", "M9") if horiz else ("M9", "M8")
    t0 = tuple(w["trunk_tap"])
    st = {(s["cell"], s["pin"]): s for s in w["stacks"]}
    pads = defaultdict(set)
    for s in w["stacks"]:
        for k, v in stack_pad_layers(s).items():
            pads[k] |= v
    rec["nets"] += 1
    L.append(f"set w [rnet {nm}]")
    L.append("$e begin $w")
    # 1. driver -> trunk tap (junction $jt)
    if w["drv"].startswith("port:"):
        pn = w["drv"][5:]
        pt = ports[pn]
        pts = _port_join(L, tl, t0, pt["layer"], tuple(pt["xy"]), entering=True)
        L.append(f"$e newPath [LY {pt['layer']}] FIXED [RL {pt['layer']}]")
        L.append(f"$e addPoint {q(pts[0][1])} {q(pts[0][2])}")
        L.append(f"$e addBTerm [BT {pn}]")
        rec["port_joins"] += 1
        _emit_steps(L, pts, final_junction=True, split_down=r8)
        for (l0, x0, y0), (l1, x1, y1) in zip(pts, pts[1:]):
            if l0 == l1 and l0 in ("M8", "M9") and (x0, y0) != (x1, y1):
                rec["extra_top"].append((nm, l0, x0, y0, x1, y1))
    else:
        s = st[(w["drv"], "Y")]
        pts = stack_down(s)[::-1]                  # M1 .. M8 at the bar, junction row
        if not horiz:                              # M8 jog to the M9 trunk
            pts += [("M8", t0[0], t0[1]), ("M9", t0[0], t0[1])]
        L.append("$e newPath [LY M1] FIXED")
        L.append(f"$e addPoint {q(pts[0][1])} {q(pts[0][2])}")
        L.append(f"$e addITerm [IT {w['drv']} Y]")
        rec["pin_stairs"] += 1
        _emit_stack(L, pts, pads, final_junction=True, split_down=r8)
    # 2. trunk
    ax = 0 if horiz else 1
    tapv = round(t0[ax], 4)
    trunk = [g for g in w["segs"] if g[0] == tl and ((g[2] == g[4] == t0[1]) if horiz else (g[1] == g[3] == t0[0]))]
    if trunk:
        g = trunk[0]
        lo, hi = (min(g[1], g[3]), max(g[1], g[3])) if horiz else (min(g[2], g[4]), max(g[2], g[4]))
    else:
        lo = hi = tapv
    roots = sorted({round(bx if horiz else by, 4) for _, bx, by in w["branches"]})
    jn = {tapv: "$jt"}
    jline = {}      # trunk value -> index in L of its `set j.. [$e addPoint ..]` (R8 port-on-trunk BTerm anchor)

    def tp(v):
        return (v, t0[1]) if horiz else (t0[0], v)
    for side, stop in (("lo", lo), ("hi", hi)):
        vals = sorted([v for v in roots if (v < tapv - 1e-6 if side == "lo" else v > tapv + 1e-6)], reverse=(side == "lo"))
        if abs(stop - tapv) < 1e-6:
            continue
        if (vals[-1] if vals else None) != round(stop, 4):
            vals.append(round(stop, 4))
        L.append(f"$e newPath $jt FIXED [RL {tl}]")
        for k, v in enumerate(vals):
            x_, y_ = tp(v)
            L.append(f"set j{side}{k} [$e addPoint {q(x_)} {q(y_)}]")
            jn[v] = f"$j{side}{k}"
            jline[v] = len(L) - 1
    # 3. loads
    anchors = []
    for ld, bx, by in w["branches"]:
        v = round(bx if horiz else by, 4)
        root = tp(v)
        if v not in jn:
            raise ValueError(f"clock_routed: {nm}: drop root {root} not on the trunk")
        if r8 and ld.startswith("port:") and v in jline and \
                max(abs(a - b) for a, b in zip(ports[ld[5:]]["xy"], root)) < 1e-6 and \
                abs(root[0] - bx) + abs(root[1] - by) < 1e-6:
            anchors.append((jline[v], ld[5:]))      # R8: the port sits on the trunk point itself
            rec["port_joins"] += 1
            continue
        L.append(f"$e newPath {jn[v]} FIXED [RL {tl}]")
        pts = [(tl, root[0], root[1])]
        if ld.startswith("port:"):
            pn = ld[5:]
            pt = ports[pn]
            lay = tl
            if abs(root[0] - bx) + abs(root[1] - by) > 1e-6:
                pts += [(bl, root[0], root[1]), (bl, bx, by)]
                lay = bl
            pj = _port_join(L, lay, (bx, by), pt["layer"], tuple(pt["xy"]), entering=False)
            pts += pj[1:]
            _emit_steps(L, pts, split_down=r8)
            L.append(f"$e addBTerm [BT {pn}]")
            for (l0, x0, y0), (l1, x1, y1) in zip(pj, pj[1:]):
                if l0 == l1 and l0 in ("M8", "M9") and (x0, y0) != (x1, y1):
                    rec["extra_top"].append((nm, l0, x0, y0, x1, y1))
            rec["port_joins"] += 1
            continue
        s = st[(ld, "A")]
        if not horiz:                              # M9 trunk -> M8 drop to the bar
            pts += [("M8", root[0], root[1])]
        pts += stack_down(s)[1:] if (pts[-1][0], pts[-1][1], pts[-1][2]) == stack_down(s)[0] else stack_down(s)
        _emit_stack(L, pts, pads, split_down=r8)
        L.append(f"$e addITerm [IT {ld} A]")
        rec["pin_stairs"] += 1
    for i, pn in sorted(anchors, reverse=True):    # R8 ports on trunk points: BTerm right after that point
        L.insert(i + 1, f"$e addBTerm [BT {pn}]")
    L.append("$e end")


def stack_shapes(w):
    """pad rectangles (M2..M8) of a pin-stack wire, for the cross-net census: (net, layer, x0, y0, x1, y1)"""
    P = _stack_pad()
    out = []
    for s in w["stacks"]:
        for (x, y), lays in stack_pad_layers(s).items():
            for L_ in sorted(lays):
                hx, hy = P[L_]
                out.append((w["name"], L_, x - hx, y - hy, x + hx, y + hy))
        x, py, jy = s["xy"][0], s["xy"][1], s["riser_from"][1]
        h = WIDTH["M7"] / 2                          # M7 riser on the bar column
        out.append((w["name"], "M7", x - h, min(py, jy) - h, x + h, max(py, jy) + h))
    return out


def routed_tcl(wires, cells, ports, buf, ndr_name):
    """Tcl that turns every fixed tree net into a regular CLOCK net with one FIXED dbWire under NDR `ndr_name`.
    Needs $blk, $tech and the NDR already created.  Returns (lines, record) where record lists every pin-access
    step drawn on M8/M9 (the only M8/M9 metal that is not a planned leg) for plan_check."""
    L = ["proc V {n} { global tech; set v [$tech findVia $n]; if {$v == \"NULL\"} { error \"via $n missing\" }; return $v }",
         "proc LY {n} { global tech; return [$tech findLayer $n] }",
         f"set ot_ndr [$blk findNonDefaultRule {ndr_name}]",
         "if {$ot_ndr == \"NULL\"} { error \"clock NDR missing\" }",
         "proc RL {n} { global ot_ndr; return [$ot_ndr getLayerRule [LY $n]] }",
         "proc rnet {nm} { global blk ot_ndr; set n [$blk findNet $nm]; if {$n == \"NULL\"} { error \"missing clock net $nm\" }; "
         "if {[$n isSpecial]} { $n clearSpecial }; foreach it [$n getITerms] { $it clearSpecial }; $n setSigType CLOCK; "
         "$n setNonDefaultRule $ot_ndr; set w [$n getWire]; if {$w != \"NULL\"} { odb::dbWire_destroy $w }; "
         "return [odb::dbWire_create $n] }",
         "proc IT {i p} { global blk; set t [[$blk findInst $i] findITerm $p]; if {$t == \"NULL\"} { error \"no iterm $i/$p\" }; return $t }",
         "proc BT {p} { global blk; set t [$blk findBTerm $p]; if {$t == \"NULL\"} { error \"no bterm $p\" }; return $t }",
         "set e [odb::dbWireEncoder]"]
    rec = dict(nets=0, pin_stairs=0, port_joins=0, extra_top=[])

    def cell_pts(inst, pin, at, layer):
        px, py = pin_point(cells, inst, pin, cells[inst].get("lib", buf))
        return stair(layer, at[0], at[1], px, py)

    def note_top(name, pts):
        for (l0, x0, y0), (l1, x1, y1) in zip(pts, pts[1:]):
            if l0 == l1 and l0 in ("M8", "M9") and (x0, y0) != (x1, y1):
                rec["extra_top"].append((name, l0, x0, y0, x1, y1))
    for w in wires:
        if w.get("pin_stack"):       # CLOCK-128-R7: straight pin stacks (die_clock_128._fixed_wires_stack)
            _stack_net_tcl(L, w, ports, rec)
            continue
        N = net_plan(w, cells, ports, buf)
        nm = N["name"]
        rec["nets"] += 1
        L.append(f"set w [rnet {nm}]")
        L.append("$e begin $w")
        tl, t0, horiz = N["tl"], N["tap"], N["horiz"]
        # 1. driver -> trunk tap
        kind, ident, pl, pxy, at, lay = N["drv"]
        if kind == "cell":
            pts = cell_pts(ident, "Y", at, lay)[::-1]
            L.append("$e newPath [LY M1] FIXED")
            L.append(f"$e addPoint {q(pts[0][1])} {q(pts[0][2])}")
            L.append(f"$e addITerm [IT {ident} Y]")
            rec["pin_stairs"] += 1
        else:
            pts = _port_join(L, lay, at, pl, pxy, entering=True)
            L.append(f"$e newPath [LY {pl}] FIXED [RL {pl}]")
            L.append(f"$e addPoint {q(pts[0][1])} {q(pts[0][2])}")
            L.append(f"$e addBTerm [BT {ident}]")
            rec["port_joins"] += 1
        _emit_steps(L, pts, final_junction=True)     # junction at the trunk tap = last driver step (or the start)
        note_top(nm, pts)
        # 2. trunk: tap -> lo end and tap -> hi end, a junction at every drop root
        tapv = t0[0] if horiz else t0[1]
        roots = sorted({round(ld[6][0] if horiz else ld[6][1], 4) for ld in N["loads"]})
        jn = {round(tapv, 4): "$jt"}

        def tp(v):
            return (v, t0[1]) if horiz else (t0[0], v)
        for side, stop in (("lo", N["lo"]), ("hi", N["hi"])):
            vals = [v for v in roots if (v < tapv - 1e-6 if side == "lo" else v > tapv + 1e-6)]
            vals = sorted(vals, reverse=(side == "lo"))
            if abs(stop - tapv) < 1e-6:
                continue
            if (vals[-1] if vals else None) != round(stop, 4):
                vals.append(round(stop, 4))
            L.append(f"$e newPath $jt FIXED [RL {tl}]")
            for k, v in enumerate(vals):
                x_, y_ = tp(v)
                L.append(f"set j{side}{k} [$e addPoint {q(x_)} {q(y_)}]")
                jn[v] = f"$j{side}{k}"
        # 3. drops / loads
        for kind, ident, pl, pxy, at, lay, root in N["loads"]:
            v = round(root[0] if horiz else root[1], 4)
            if v not in jn:
                raise ValueError(f"clock_routed: {nm}: drop root {root} not on the trunk")
            L.append(f"$e newPath {jn[v]} FIXED [RL {tl}]")
            pts = [(tl, root[0], root[1])]
            if lay != tl:
                pts += [(lay, root[0], root[1]), (lay, at[0], at[1])]
            if kind == "cell":
                st = cell_pts(ident, "A", at, lay)
                pts += st[1:]
                _emit_steps(L, pts)
                L.append(f"$e addITerm [IT {ident} A]")
                note_top(nm, st)
                rec["pin_stairs"] += 1
            else:
                pj = _port_join(L, lay, at, pl, pxy, entering=False)
                pts += pj[1:]
                _emit_steps(L, pts)
                L.append(f"$e addBTerm [BT {ident}]")
                note_top(nm, pj)
                rec["port_joins"] += 1
        L.append("$e end")
    L.append(f"puts \"OT_ROUTED_CLOCK nets {rec['nets']} pin_stairs {rec['pin_stairs']} port_joins {rec['port_joins']}\"")
    return L, rec


# ----------------------------------------------------------------------------------------------- shape model + checks
def via_rects():
    """ASAP7 1x default via enclosures (um, centred) per layer, from asap7_tech_1x_201209.lef"""
    return {"VIA12": {"M1": (0.009, 0.011), "M2": (0.014, 0.009)},
            "VIA23": {"M2": (0.014, 0.009), "M3": (0.009, 0.014)},
            "VIA34": {"M3": (0.009, 0.020), "M4": (0.020, 0.012)},
            "VIA45": {"M4": (0.020, 0.012), "M5": (0.012, 0.020)},
            "VIA56": {"M5": (0.012, 0.020), "M6": (0.020, 0.016)},
            "VIA67": {"M6": (0.020, 0.016), "M7": (0.016, 0.020)},
            "VIA78": {"M7": (0.016, 0.027), "M8": (0.027, 0.020)},
            "VIA89": {"M8": (0.020, 0.020), "M9": (0.020, 0.020)}}


WIDTH = {"M1": 0.018, "M2": 0.018, "M3": 0.018, "M4": 0.024, "M5": 0.024, "M6": 0.032, "M7": 0.032,
         "M8": 0.16, "M9": 0.16}
SPACE = {"M1": 0.018, "M2": 0.018, "M3": 0.018, "M4": 0.024, "M5": 0.024, "M6": 0.032, "M7": 0.032,
         "M8": 0.08, "M9": 0.08}


def parse_def_routes(text, names):
    """routed DEF -> {net: [(layer, x0, y0, x1, y1, width_um) | ('VIA', name, x, y)]} for the given nets (um).
    Handles '( x y )', '( * y )', '( x * )', 'VIA' and NEW; ignores extension values."""
    names = set(names)
    m = re.search(r"^NETS \d+ ;(.*?)^END NETS", text, re.S | re.M)
    out = {}
    if not m:
        return out
    for blk in m.group(1).split(";"):
        b = blk.strip()
        if not b.startswith("-"):
            continue
        tok = b.split()
        nm = tok[1]
        if nm not in names:
            continue
        items = []
        i = b.find("+ FIXED")
        if i < 0:
            out[nm] = items
            continue
        body = b[i + len("+ FIXED"):]
        body = re.split(r"\+ (?!FIXED)", body)[0]
        for path in re.split(r"\bNEW\b", body):
            t = path.replace("(", " ( ").replace(")", " ) ").split()
            if not t:
                continue
            layer = t[0]
            k = 1
            cur = None
            while k < len(t):
                if t[k] == "(":
                    xs, ys = t[k + 1], t[k + 2]
                    j = k + 3
                    while t[j] != ")":
                        j += 1
                    x = cur[0] if xs == "*" else int(xs) / DBU
                    y = cur[1] if ys == "*" else int(ys) / DBU
                    if cur is not None and (x, y) != cur:
                        items.append((layer, cur[0], cur[1], x, y))
                    cur = (x, y)
                    k = j + 1
                elif t[k] == "TAPER":           # no argument: default rule for this path (lower-layer stairs)
                    k += 1
                elif t[k] in ("TAPERRULE", "MASK", "STYLE", "RECT"):
                    k += 2 if t[k] != "RECT" else 1
                    if t[k - 1] == "RECT":
                        while k < len(t) and t[k] != ")":
                            k += 1
                        k += 1
                elif re.match(r"VIA\d+", t[k]) or t[k].startswith("VIA"):
                    items.append(("VIA", t[k], cur[0], cur[1]))
                    a, b_ = f"M{t[k][3]}", f"M{t[k][4]}"
                    layer = b_ if layer == a else a
                    k += 1
                else:
                    k += 1
        out[nm] = items
    return out


def _norm(s):
    L, x0, y0, x1, y1 = s
    return (L, round(min(x0, x1), 3), round(min(y0, y1), 3), round(max(x0, x1), 3), round(max(y0, y1), 3))


def _merge(segs):
    """merge collinear touching/overlapping same-layer segments (DEF splits a leg at every junction)"""
    by = defaultdict(list)
    for s in map(_norm, segs):
        L, x0, y0, x1, y1 = s
        key = (L, "h", y0) if y0 == y1 else (L, "v", x0)
        by[key].append((x0, x1) if y0 == y1 else (y0, y1))
    out = []
    for (L, d, c), iv in by.items():
        iv.sort()
        a, b = iv[0]
        for u, v in iv[1:]:
            if u <= b + 1e-6:
                b = max(b, v)
            else:
                out.append((L, d, c, a, b))
                a, b = u, v
        out.append((L, d, c, a, b))
    return out


def plan_check(def_text, wires, rec, cells):
    """geometry == plan: per net, the merged M8/M9 metal of the routed DEF must equal the merged planned legs plus the
    recorded pin-access M8 steps / port joins (nothing moved, nothing extra); every clock cell at its plan location."""
    names = [w["name"] for w in wires]
    got = parse_def_routes(def_text, names)
    extra = defaultdict(list)
    for nm, L_, x0, y0, x1, y1 in rec["extra_top"]:
        extra[nm].append((L_, x0, y0, x1, y1))
    bad, n_leg, n_ok = [], 0, 0
    for w in wires:
        nm = w["name"]
        top = [s[:5] for s in got.get(nm, []) if s[0] in ("M8", "M9")]
        want = _merge([tuple(s) for s in w["segs"]] + extra[nm])
        have = _merge(top)
        n_leg += len(w["segs"])
        if sorted(want) != sorted(have):
            bad.append(dict(net=nm, want=sorted(want), have=sorted(have)))
        else:
            n_ok += 1
        if nm not in got:
            bad.append(dict(net=nm, missing=True))
    comp = {}
    m = re.search(r"^COMPONENTS \d+ ;(.*?)^END COMPONENTS", def_text, re.S | re.M)
    if m:
        for c in m.group(1).split(";"):
            t = c.split()
            if len(t) >= 2 and t[0] == "-" and t[1] in cells:
                mm = re.search(r"\+ (FIXED|PLACED|FIRM) \( (-?\d+) (-?\d+) \) (\S+)", c)
                if mm:
                    comp[t[1]] = (int(mm.group(2)) / DBU, int(mm.group(3)) / DBU, mm.group(4))
    moved = []
    for c, v in cells.items():
        g = comp.get(c)
        if g is None or abs(g[0] - v["x"]) > 0.0005 or abs(g[1] - v["y"]) > 0.0005:
            moved.append(dict(cell=c, plan=[v["x"], v["y"]], db=list(g) if g else None))
    return dict(nets=len(wires), nets_equal=n_ok, plan_leg_segments=n_leg,
                pin_access_top_steps=len(rec["extra_top"]), mismatches=bad[:50], n_mismatch=len(bad),
                cells=len(cells), cells_found=len(comp), cells_moved=moved[:50], n_moved=len(moved),
                equal=bool(not bad and not moved and len(comp) == len(cells)))


def stair_shapes(wires, cells, ports, buf):
    """every pin-access rectangle (lower layers, wires + via enclosures) per net, for a cross-net spacing census"""
    vr = via_rects()
    out = []
    for w in wires:
        if w.get("pin_stack"):
            out += stack_shapes(w)
            continue
        N = net_plan(w, cells, ports, buf)
        ends = []
        if N["drv"][0] == "cell":
            ends.append(stair(N["drv"][5], N["drv"][4][0], N["drv"][4][1],
                              *pin_point(cells, N["drv"][1], "Y", cells[N["drv"][1]].get("lib", buf))))
        for ld in N["loads"]:
            if ld[0] == "cell":
                ends.append(stair(ld[5], ld[4][0], ld[4][1], *pin_point(cells, ld[1], "A", cells[ld[1]].get("lib", buf))))
        for pts in ends:
            for (l0, x0, y0), (l1, x1, y1) in zip(pts, pts[1:]):
                if l0 != l1:
                    for L_, (hx, hy) in vr[via(l0, l1)].items():
                        out.append((N["name"], L_, x0 - hx, y0 - hy, x0 + hx, y0 + hy))
                elif (x0, y0) != (x1, y1) and l0 not in ("M8", "M9"):
                    h = WIDTH[l0] / 2
                    out.append((N["name"], l0, min(x0, x1) - h, min(y0, y1) - h, max(x0, x1) + h, max(y0, y1) + h))
    return out


def stair_census(shapes, limit=100):
    """cross-net shorts / spacing violations among pin-access shapes (same layer, edge distance < SPACE)"""
    by = defaultdict(list)
    for s in shapes:
        by[s[1]].append(s)
    shorts, spacing = [], []
    for L_, ss in by.items():
        ss.sort(key=lambda r: r[2])
        sp = SPACE[L_]
        for i, a in enumerate(ss):
            for b in ss[i + 1:]:
                if b[2] > a[4] + sp:
                    break
                if a[0] == b[0]:
                    continue
                dx = max(0.0, max(a[2], b[2]) - min(a[4], b[4]))
                dy = max(0.0, max(a[3], b[3]) - min(a[5], b[5]))
                if dx == 0 and dy == 0:
                    shorts.append((L_, a[0], b[0], round(a[2], 3), round(a[3], 3)))
                elif math.hypot(dx, dy) < sp - 1e-9:
                    spacing.append((L_, a[0], b[0], round(a[2], 3), round(a[3], 3)))
    return dict(shapes=len(shapes), shorts=len(shorts), spacing=len(spacing), short_list=shorts[:limit],
                spacing_list=spacing[:limit])


def shield_only_tcl(combo_lines):
    """die_clock_128.combo_tcl output -> the same VSS shields + shield-spacing obstructions WITHOUT the special clock
    metal: fwnet no longer makes the net special, fw no longer draws the clock SBox, and every obstruction fw creates
    is remembered in ::ot_clk_obs so the route step can remove it before DRT (GRT still sees it)."""
    out, nf, nw = [], 0, 0
    for s in combo_lines:
        if s.startswith("proc fwnet "):
            s = "proc fwnet {nm} { return {} }"
            nf += 1
        elif s.startswith("proc fw "):
            n0 = s.count("odb::dbSBox_create $sw $l ")
            s = re.sub(r"odb::dbSBox_create \$sw \$l \[um \[expr \{\$x0-\$hw\}\]\] \[um \[expr \{\$y0-\$hw\}\]\] "
                       r"\[um \[expr \{\$x[01]\+\$hw\}\]\] \[um \[expr \{\$y[01]\+\$hw\}\]\] STRIPE; ", "", s)
            if n0 != 2 or "odb::dbSBox_create $sw $l " in s:
                raise ValueError("clock_routed: unexpected fw proc shape (clock SBox not found twice)")
            k = s.count("odb::dbObstruction_create $blk $l ")
            s = re.sub(r"odb::dbObstruction_create (\$blk \$l \[um [^;]*?\]\]) \}",
                       r"lappend ::ot_clk_obs [odb::dbObstruction_create \1] }", s)
            if s.count("lappend ::ot_clk_obs") != k or k != 2:
                raise ValueError("clock_routed: unexpected fw proc shape (obstructions)")
            nw += 1
        out.append(s)
    if nf != 1 or nw != 1:
        raise ValueError("clock_routed: combo_tcl procs not found")
    return ["set ::ot_clk_obs {}"] + out


# ------------------------------------------------------------------------------------------------------ route step
ROUTE_TCL = r"""# GENERATED by clock_routed.py route (CLOCK-128-R5): OpenRCX on the plan-fixed die clock (regular nets with FIXED
# dbWire).  Input = combo_TT.odb (combo --routed-clock: GRT done, clock obstructions removed).  No detailed_route:
# every clock net is fully pre-routed and FIXED, DRT would not touch it (probe), and a whole-die DR pass OOMs on the
# kit gcells (INFRA-R5 root cause); DRC of the drawn geometry = drc.tcl (DRT's own checker, drt::check_drc).
set t0 [clock seconds]
read_db /out/combo_TT.odb
set blk [ord::get_db_block]
set nn 0; set nw 0; set nsp 0
foreach n [$blk getNets] { if {[$n getSigType] eq "CLOCK"} { incr nn; if {[$n getWire] != "NULL"} { incr nw }; if {[$n isSpecial]} { incr nsp } } }
puts "OT_CLOCK_NETS $nn with_wire $nw special $nsp"
puts "OT_OBS [llength [$blk getObstructions]]"
write_def /out/routed.def
@RCX@
write_spef /out/rcx.spef
write_db /out/routed.odb
puts "OT_T total [expr {[clock seconds]-$t0}] s"
puts OT_DONE
"""

DRC_TCL = r"""# GENERATED by clock_routed.py route: DRT design-rule check (drt::check_drc) of the drawn clock geometry, die box
set t0 [clock seconds]
read_db /out/routed.odb
set blk [ord::get_db_block]; set tech [ord::get_db_tech]
foreach l {M1 M2 M3} { set tg [$blk findTrackGrid [$tech findLayer $l]]; if {$tg != "NULL"} { odb::dbTrackGrid_destroy $tg } }
make_tracks M1 -x_offset 0.009 -x_pitch 0.036 -y_offset 0.009 -y_pitch 0.036
foreach yo {0.045 0.081 0.117 0.153 0.189 0.225 0.270} { make_tracks M2 -x_offset 0.009 -x_pitch 0.036 -y_offset $yo -y_pitch 0.270 }
make_tracks M3 -x_offset 0.009 -x_pitch 0.036 -y_offset 0.009 -y_pitch 0.036
set fh [open /out/drc_boxes.txt r]; set k 0
foreach ln [split [string trim [read $fh]] "\n"] {
  lassign $ln x0 y0 x1 y1
  drt::check_drc -box [list $x0 $y0 $x1 $y1] -output_file /out/drc/box_$k.rpt; incr k
}
close $fh
puts "OT_DRC_BOXES $k"
puts "OT_T drc [expr {[clock seconds]-$t0}] s"
puts OT_DONE
"""

STA_TCL = r"""# GENERATED by clock_routed.py route: tree arrivals on the routed clock, one corner x one SPEF basis
foreach f [glob $::env(LIBDIR)/*RVT_$::env(CORNER)_nldm*.lib*] { read_liberty $f }
read_db /out/routed.odb
read_spef /out/$::env(BASIS).spef
foreach c [get_cells -quiet ckm_d_*] { set_disable_timing $c }
create_clock -name vclk -period 833.000
set_driving_cell -lib_cell BUFx24_ASAP7_75t_R -pin Y [get_ports root]
set_input_delay 0 -clock vclk [get_ports root]
set_load 3.0 [get_ports t_*]
# build the timing graph before get_property (a bare read_db + get_property arrival segfaults in Graph::pinVertices)
report_checks -path_delay min_max -format end
set fh [open /out/tree_$::env(CORNER)_$::env(BASIS).txt w]
foreach c [get_cells -quiet ckm_d_*] { set p [get_pins [get_full_name $c]/A]; puts $fh "D [get_full_name $c] [get_property $p arrival_max_rise] [get_property $p arrival_min_rise] [get_property $p slew_max_rise]" }
foreach c [get_cells {ckm_n* ckm_r* ckm_t*}] { set p [get_pins [get_full_name $c]/Y]; puts $fh "N [get_full_name $c] [get_property $p arrival_max_rise] [get_property $p arrival_min_rise] [get_property $p slew_max_rise]" }
close $fh
report_check_types -max_slew -max_capacitance -violators
puts OT_DONE
"""


def drc_boxes(wires, cells, ports, buf, pad=1.0, cell_pad=2.0):
    """check_drc boxes (dbu): one per clock cell (pin-access stairs, drop ends, driver taps) and one per planned leg"""
    out = []
    for c, v in sorted(cells.items()):
        out.append((v["x"] - cell_pad, v["y"] - cell_pad, v["x"] + 1.62 + cell_pad, v["y"] + 0.27 + cell_pad))
    for w in wires:
        for L_, x0, y0, x1, y1 in w["segs"]:
            out.append((min(x0, x1) - pad, min(y0, y1) - pad, max(x0, x1) + pad, max(y0, y1) + pad))
        for p in [w["drv"]] + list(w["loads"]):
            if p.startswith("port:"):
                x, y = ports[p[5:]]["xy"]
                out.append((x - cell_pad, y - cell_pad, x + cell_pad, y + cell_pad))
    return "\n".join(f"{q(a)} {q(b)} {q(c)} {q(d_)}" for a, b, c, d_ in out) + "\n"


STOCK_RULES = "/OpenROAD-flow-scripts/flow/platforms/asap7/rcx_patterns.rules"


def rcx_tcl(rules="stock", rules_text=None):
    """the extraction lines of route.tcl.  stock (default, R5 behaviour): the platform rules, which carry ONE M8/M9
    width (0.04) and give a 0.16-um clock NDR wire the 0.04-um R and C (CLOCK-128-R6 probe, CHECKED).  ndr
    (CLOCK-128-R6, opt-in): the width-characterised rules (rcx_width_rules.py: 0.16-um M8/M9 entries, field-solver
    width ratios on the rules' own calibration, rules copied into the run dir as /out/rcx_ndr.rules) + OpenRCX -lef_res
    with every routing layer's RPERSQ set to the rules' own sheet resistance (r_table x table width), so R scales as
    1/w and default-width wires extract exactly as with the stock rules."""
    if rules == "stock":
        return f"extract_parasitics -ext_model_file {STOCK_RULES}"
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import rcx_width_rules as RW
    L = ["# CLOCK-128-R6 width-aware extraction: RPERSQ (ohm/sq) = rules r(w0) x w0 per layer, R = RPERSQ x L / w",
         "set ot_tech [ord::get_db_tech]"]
    for lay, rsq in sorted(RW.rpersq(rules_text).items()):
        L.append(f"[$ot_tech findLayer {lay}] setResistance {rsq:.6g}")
    L.append("extract_parasitics -ext_model_file /out/rcx_ndr.rules -lef_res")
    return "\n".join(L)


def write_route(d, kit, image="openroad/orfs:latest", mem=64, rcx_rules="stock"):
    import json
    from pathlib import Path
    d, kit = Path(d), Path(kit)
    M = json.loads((d / "mesh.json").read_text())
    cells = json.loads((d / "place.json").read_text())
    ports = {t["port"]: dict(layer=t.get("layer", M["meta"].get("tap_layer", "M7")), xy=t["xy"]) for t in M["taps"]}
    ports["root"] = dict(layer="M9", xy=list(M["meta"]["root_um"]))
    rules_text = None
    if rcx_rules != "stock":
        rules_text = Path(rcx_rules).read_text()
        (d / "rcx_ndr.rules").write_text(rules_text)
    rt = ROUTE_TCL
    if any(w.get("enc") == "r8" for w in M["fixed_wires"]):
        # CLOCK-128-R8: OpenRCX rewrites every dbWire (junction/RC ids) and drops the encoder RECT pads, so the drawn
        # geometry is saved BEFORE extraction (routed.odb = what DRC checks and what ships); the post-RCX db is
        # routed_rcx.odb (CLOCK-128-R8 e5: w0 52 ops without RECT vs 98 drawn)
        rt = rt.replace("write_def /out/routed.def\n", "write_def /out/routed.def\nwrite_db /out/routed.odb\n", 1)
        rt = rt.replace("write_spef /out/rcx.spef\nwrite_db /out/routed.odb\n",
                        "write_spef /out/rcx.spef\nwrite_db /out/routed_rcx.odb\n", 1)
        assert rt.count("write_db /out/routed.odb") == 1 and "routed_rcx.odb" in rt
    (d / "route.tcl").write_text(rt.replace("@RCX@", rcx_tcl("stock" if rcx_rules == "stock" else "ndr",
                                                             rules_text)))
    (d / "rcx_basis.json").write_text(json.dumps(dict(rules="stock" if rcx_rules == "stock" else str(rcx_rules))))
    (d / "sta.tcl").write_text(STA_TCL)
    (d / "drc.tcl").write_text(DRC_TCL)
    (d / "drc_boxes.txt").write_text(drc_boxes(M["fixed_wires"], cells, ports, BUF_DEFAULT))
    (d / "run_route.sh").write_text(f"""#!/bin/bash
# GENERATED by clock_routed.py route: (1) DRT + RCX on combo_TT.odb, (2) STA per corner x {{native, rcx}} SPEF
set -u
D=$(cd $(dirname $0) && pwd); K={kit.resolve()}
run() {{ m=${{5:-${{MEM:-{mem}}}}}; docker run --rm --name ckr5-$(basename $D)-$1-$$ --cpus=16 --memory=${{m}}g --memory-swap=${{m}}g \\
  -e CORNER=${{2:-TT}} -e BASIS=${{3:-rcx}} -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM \\
  -v $K:/work:ro -v $(readlink -f $K/abstracts):/work/abstracts:ro -v $D:/out {image} \\
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1 && /usr/bin/time -v openroad -no_init -threads 16 -exit /out/$4 > /out/$1.log 2>&1; rc=\\$?; echo EXIT \\$rc >> /out/$1.log; chown -R $(id -u):$(id -g) /out; exit \\$rc"; }}
# combo --routed-clock (TT): kit + fixed clock nets, GRT, R4-basis native arrivals, clock obstructions removed
[ -s $D/combo_TT.odb ] || CORNERS=TT MEM=${{COMBO_MEM:-48}} bash $D/run_combo.sh || exit $?
[ -s $D/rcx.spef ] || run route TT rcx route.tcl || exit $?
cp -f $D/native_TT.spef $D/native.spef
rc=0
mkdir -p $D/drc
run drc TT rcx drc.tcl ${{DRC_MEM:-48}} &
for c in TT FF; do for b in native rcx; do run sta_${{c}}_$b $c $b sta.tcl ${{STA_MEM:-16}} & done; done
for j in $(jobs -p); do wait $j || rc=$?; done
exit $rc
""")
    (d / "run_route.sh").chmod(0o755)


def read_tree(path):
    out = {}
    for ln in open(path):
        t = ln.split()
        if len(t) == 5:
            out[t[1]] = (float(t[2]), float(t[3]), float(t[4]))
    return out


def spef_rc(path, names):
    """per-net total C (fF, *D_NET header) and total R (kohm, sum of *RES) of a SPEF, by net name"""
    names = set(names)
    nm_map, out, cur = {}, {}, None
    sec = None
    cu, ru = 1.0, 1.0            # -> fF, kohm (RCX writes PF / OHM, the native writer FF / KOHM)
    CU = {"FF": 1.0, "PF": 1e3, "NF": 1e6}
    RU = {"OHM": 1e-3, "KOHM": 1.0}
    with open(path) as f:
        for ln in f:
            s = ln.strip()
            if s.startswith("*C_UNIT"):
                t = s.split(); cu = float(t[1]) * CU[t[2].upper()]
                continue
            if s.startswith("*R_UNIT"):
                t = s.split(); ru = float(t[1]) * RU[t[2].upper()]
                continue
            if s.startswith("*NAME_MAP"):
                sec = "map"
                continue
            if sec == "map":
                if s.startswith("*") and len(s.split()) == 2 and not s.startswith("*D_NET"):
                    k, v = s.split()
                    nm_map[k] = v
                    continue
                if s.startswith("*PORTS") or s.startswith("*D_NET"):
                    sec = None
            if s.startswith("*D_NET"):
                t = s.split()
                nm = nm_map.get(t[1], t[1]).replace("\\", "")
                cur = nm if nm in names else None
                if cur:
                    out[cur] = dict(c_ff=round(float(t[2]) * cu, 6), r_kohm=0.0, conn=0)
                sec = None
            elif cur and s.startswith("*RES"):
                sec = "res"
            elif cur and s.startswith("*CONN"):
                sec = "conn"
            elif cur and s.startswith("*CAP"):
                sec = "cap"
            elif cur and s.startswith("*END"):
                cur, sec = None, None
            elif cur and sec == "res" and s:
                out[cur]["r_kohm"] += float(s.split()[3]) * ru
            elif cur and sec == "conn" and s.startswith(("*I", "*P")):
                out[cur]["conn"] += 1
    return out


def report(d):
    """route_report.json: RCX per-net RC (non-zero proof), plan == geometry check, DRT DRC count, and the
    native-SPEF vs RCX latency / spread table per corner (late + early) at the 16 lattice leaves (ckm_n4_*)"""
    import json
    from pathlib import Path
    d = Path(d)
    M = json.loads((d / "mesh.json").read_text())
    cells = json.loads((d / "place.json").read_text())
    rec = json.loads((d / "clock_routed.json").read_text())
    wires = M["fixed_wires"]
    names = [w["name"] for w in wires]
    want_conn = {w["name"]: 1 + len(w["loads"]) for w in wires}
    rc = spef_rc(d / "rcx.spef", names)
    nat = spef_rc(d / "native_TT.spef", names)
    zero = [n for n in names if n not in rc or rc[n]["c_ff"] <= 0 or rc[n]["r_kohm"] <= 0]
    open_ = [n for n in names if n in rc and rc[n]["conn"] != want_conn[n]]
    chk = plan_check((d / "routed.def").read_text(), wires, rec, cells)
    drc, kinds, nbox = 0, defaultdict(int), 0
    uniq = {}       # CLOCK-128-R7: overlapping check boxes report one marker several times
    for p in sorted((d / "drc").glob("box_*.rpt")):
        nbox += 1
        txt = p.read_text()
        for m in re.finditer(r"violation type: (.*)\n(?:.*\n)*?\s*bbox = .* on Layer (\S+)", txt):
            kinds[f"{m.group(1).strip()} @ {m.group(2)}"] += 1
        for m in re.finditer(r"violation type: (.*)\n\s*srcs: (.*)\n\s*bbox = (.*) on Layer (\S+)", txt):
            uniq[(m.group(1).strip(), m.group(4), m.group(3).strip(), " ".join(sorted(m.group(2).split())))] = 1
        drc += txt.count("violation type")
    ukinds = defaultdict(int)
    for k in uniq:
        ukinds[f"{k[0]} @ {k[1]}"] += 1
    tab = {}
    for c in ("TT", "FF"):
        for b in ("native", "rcx"):
            f = d / f"tree_{c}_{b}.txt"
            if not f.exists():
                continue
            T = read_tree(f)
            lv = {k: v for k, v in T.items() if k.startswith("ckm_n4_")}
            late = [v[0] for v in lv.values()]
            early = [v[1] for v in lv.values()]
            tab[f"{c}_{b}"] = dict(leaves=len(lv), late_min=round(min(late), 2), late_max=round(max(late), 2),
                                   late_spread=round(max(late) - min(late), 2), early_min=round(min(early), 2),
                                   early_max=round(max(early), 2), early_spread=round(max(early) - min(early), 2),
                                   slew_max=round(max(v[2] for v in T.values()), 2),
                                   per_leaf={k: [round(v[0], 2), round(v[1], 2)] for k, v in sorted(lv.items())})
    delta = {}
    for c in ("TT", "FF"):
        a, b = tab.get(f"{c}_native"), tab.get(f"{c}_rcx")
        if a and b:
            dl = [b["per_leaf"][k][0] - a["per_leaf"][k][0] for k in a["per_leaf"]]
            de = [b["per_leaf"][k][1] - a["per_leaf"][k][1] for k in a["per_leaf"]]
            delta[c] = dict(late_mean=round(sum(dl) / len(dl), 2), late_min=round(min(dl), 2), late_max=round(max(dl), 2),
                            early_mean=round(sum(de) / len(de), 2))
    # R per um of planned M8/M9 leg length (ohm/um): the ASAP7 rcx_patterns.rules M8/M9 RESOVER table has ONE width
    # entry (0.04 um, 8.45 / 8.90 ohm/um); a value near it on a 0.16-um NDR leg means RCX did not width-scale R
    leg_um = {w["name"]: sum(abs(g[3] - g[1]) + abs(g[4] - g[2]) for g in w["segs"]) for w in wires}
    rpu = sorted(1e3 * rc[n]["r_kohm"] / leg_um[n] for n in names if n in rc and leg_um[n] > 50)
    npu = sorted(1e3 * nat[n]["r_kohm"] / leg_um[n] for n in names if n in nat and leg_um[n] > 50)
    tot = lambda D: (round(sum(v["c_ff"] for v in D.values()), 1), round(sum(v["r_kohm"] for v in D.values()), 2))
    ratio_c = sorted(rc[n]["c_ff"] / nat[n]["c_ff"] for n in names if n in rc and n in nat and nat[n]["c_ff"] > 0)
    ratio_r = sorted(rc[n]["r_kohm"] / nat[n]["r_kohm"] for n in names if n in rc and n in nat and nat[n]["r_kohm"] > 0)
    med = lambda v: v[len(v) // 2] if v else None
    out = dict(
        rcx=dict(nets=len(names), extracted=len(rc), zero_rc=zero, pins_not_on_net=open_,
                 sum_c_ff_rcx=tot(rc)[0], sum_r_kohm_rcx=tot(rc)[1], sum_c_ff_native=tot(nat)[0],
                 sum_r_kohm_native=tot(nat)[1], per_net_c_ratio_med=med(ratio_c), per_net_r_ratio_med=med(ratio_r),
                 c_ratio_min=ratio_c[0] if ratio_c else None, c_ratio_max=ratio_c[-1] if ratio_c else None,
                 r_ratio_min=ratio_r[0] if ratio_r else None, r_ratio_max=ratio_r[-1] if ratio_r else None,
                 r_ohm_per_leg_um_med_rcx=med(rpu), r_ohm_per_leg_um_med_native=med(npu), nets_over_50um=len(rpu)),
        plan_check={k: v for k, v in chk.items()}, drt_check_drc=dict(boxes_checked=nbox, total=drc, by_kind=dict(kinds), unique=len(uniq),
                                                               unique_by_kind=dict(ukinds),
                                                               unique_examples=[list(k) for k in list(uniq)[:40]]),
        latency={k: {kk: vv for kk, vv in v.items() if kk != "per_leaf"} for k, v in tab.items()},
        per_leaf={k: v["per_leaf"] for k, v in tab.items()}, rcx_minus_native=delta,
        per_net_rc={n: dict(rcx=rc.get(n), native=nat.get(n)) for n in names},
        rcx_basis=json.loads((d / "rcx_basis.json").read_text()) if (d / "rcx_basis.json").exists() else dict(rules="stock"))
    (d / "route_report.json").write_text(json.dumps(out, indent=1) + "\n")
    return out


def main(argv=None):
    import argparse
    import json
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("route", help="write route.tcl / sta.tcl / run_route.sh into a combo --routed-clock build dir")
    r.add_argument("dir")
    r.add_argument("--kit", required=True)
    r.add_argument("--mem", type=int, default=64)
    r.add_argument("--rcx-rules", default="stock",
                   help="stock (default) or a width-characterised rules file (rcx_width_rules.py write), extracted "
                        "with -lef_res and per-layer RPERSQ from the same rules (CLOCK-128-R6)")
    p = sub.add_parser("report", help="route_report.json from the routed build dir")
    p.add_argument("dir")
    a = ap.parse_args(argv)
    if a.cmd == "route":
        write_route(a.dir, a.kit, mem=a.mem, rcx_rules=a.rcx_rules)
        print("route written", a.dir)
    else:
        o = report(a.dir)
        print(json.dumps(dict(rcx={k: v for k, v in o["rcx"].items() if k not in ("zero_rc", "pins_not_on_net")} |
                              dict(zero_rc=len(o["rcx"]["zero_rc"]), pins_not_on_net=len(o["rcx"]["pins_not_on_net"])),
                              plan_equal=o["plan_check"]["equal"], drc=o["drt_check_drc"], latency=o["latency"],
                              delta=o["rcx_minus_native"]), indent=1))
        return 0 if o["plan_check"]["equal"] and not o["rcx"]["zero_rc"] else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
