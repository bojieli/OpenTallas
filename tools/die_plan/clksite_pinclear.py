#!/usr/bin/env python3
"""CLKSITE-PINCLEAR (KV-PLAN-R6 + FAM-KV-IOPC-R3 11-21; class from kit_pin_site_check.py main a137683011): a die_clock_tree
reserved row whose obstruction (route_layers over rect_um, stack_layers over each stack_um window = the die cell's via
stack) covers a face pin of the same layer leaves that pin no access: a guaranteed route short (kv3_io_cor_v1
ft11_i[2..7] = its 6 final DRC shorts; D26 / D27d2: 920 face pins on 42 KV types).

Rule (fixed, die-agnostic, one generator step on the event's own plan).  Every face pin has an ACCESS CORRIDOR on its
layer: its pin rect (gen_phys.type_pins position, PIN_LEN_UM x layer width, the rect io.tcl places) extended inward to
--clear-um from the face and --side-um (default 0.1, spacing) along the face on both sides.  A row whose obstruction covers a pin rect moves (rect + every stack window, same size) by the
SMALLEST axis-aligned translation, x on the 0.054-um site and y on the 0.27-um row, after which
  - no obstruction of the row overlaps any same-layer access corridor of the type (pins on every face, so a row between
    pins of opposite faces, or a row with several stack windows, is judged on all of them at once), and
  - clksite_resite._legal holds (inside the outline, off hard cores + CORE_HALO_UM, off every other reserved rect,
    CLEAR_UM from every planned register point).
Candidates are inward moves (perpendicular to the hit face; both axes for a corner row), slides along the face (fallback
when no inward site within reach is legal, e.g. a row between pins of opposite faces), then outward moves; within a kind
the shortest legal move wins (then the smaller dx, dy).  No move over --max-move-um: the row is left and the run exits 1.  The ledger gives old / new rect, move, kind and the die-frame centre per partition instance
(clksite_resite form: R0 centre, else origin + orient) for the die clock rebuild (the die node goes to the new site).
The re-check on the written plan counts pin-rect hits (the kit_pin_site_check class) and must find 0.

LANDING PINS (C-CLKSITE-LANDPIN, KV-INT-R2 11-26: kv3_phy_v1 fclk_out_cland_up[0] M7 x 861.8 with a die-clock-tree cluster 4 um west of
it -> GRT detour, DRT-0255 at the pin access point).  The landing-contract pins (clock.landing_contract.pins[]: fclk_*/cland_* of
every type, xy_um in the type frame, a few um inside the nearest face) are not type_pins() face pins, so the 2-um corridor never
saw them.  Each one now owns an ESCAPE CORRIDOR on its layer and the layer below (the via access): from the pin inward to
--land-clear-um (default 8) from the pin, out to the face, +-side-um across; a row whose obstruction overlaps one moves exactly like a
face-pin row (inward / slide / outward, joint legality against every corridor of the type).  --land-margin-um (default 2) is a stand-off added beyond the corridor end and on both sides; --land-clear-um 0 turns it off.

  clksite_pinclear.py PLAN -o OUT.json --ledger L.json [--types T,..] [--clear-um 2.0] [--land-clear-um 8.0] [--land-margin-um 2.0] [--side-um 0.1] [--max-move-um 20] [--rt RT]
"""
import argparse
import json
import math
import re
import sys
from pathlib import Path

EPS = 1e-9
LAND_CLEAR_UM = 8.0          # landing-pin escape corridor, from the pin inward
LAND_MARGIN_UM = 2.0         # stand-off added to the landing corridor (far end and both sides): router jog / via-enclosure room
LAND_PIN_LEN_UM = 0.432      # landing pin stub length (kv3_phy_v1 M7 0.08 x 0.432)


def load(rt):
    sys.path.insert(0, str(Path(rt) / "tools/die_plan"))
    import schema, gen_phys as G, clksite_resite as RS, clksite_points as CP
    return schema, G, RS, CP


def ov(a, b):
    return a[0] < b[2] - EPS and b[0] < a[2] - EPS and a[1] < b[3] - EPS and b[1] < a[3] - EPS


def pin_rect(G, ln, x, y, f):
    lw = G.LAYER_W.get(ln, 0.04); L = G.PIN_LEN_UM
    if f in "EW":
        cx = x - L / 2 if f == "E" else x + L / 2
        return (cx - L / 2, y - lw / 2, cx + L / 2, y + lw / 2)
    cy = y - L / 2 if f == "N" else y + L / 2
    return (x - lw / 2, cy - L / 2, x + lw / 2, cy + L / 2)


def corridor(r, f, w, h, clear, side=0.0):
    """pin rect r on face f extended inward to `clear` um from that face and `side` um on both sides along the face"""
    if f == "E":
        return (min(r[0], w - clear), r[1] - side, r[2], r[3] + side)
    if f == "W":
        return (r[0], r[1] - side, max(r[2], clear), r[3] + side)
    if f == "N":
        return (r[0] - side, min(r[1], h - clear), r[2] + side, r[3])
    return (r[0] - side, r[1], r[2] + side, max(r[3], clear))


def type_pin_index(G, P, tn, w, h, clear, side=0.0):
    """[(name, layer, face, pin rect, corridor)] of every face pin of type tn"""
    out = []
    for bus, bit, ln, x, y, f in G.type_pins(P, tn):
        r = pin_rect(G, ln, x, y, f)
        out.append((f"{bus}[{bit}]", ln, f, r, corridor(r, f, w, h, clear, side)))
    return out


def _lower(ln):
    m = re.fullmatch(r"M(\d+)", ln or "")
    return f"M{int(m.group(1)) - 1}" if m and int(m.group(1)) > 1 else None


def landing_pin_index(G, t, w, h, land_clear, side=0.0, margin=LAND_MARGIN_UM):
    """[(name, layer, face, corridor, corridor)] of every landing-contract pin of type dict t: the corridor (pin -> land_clear um
    inward + margin -> out to the face, +-(side + margin) across) on the pin layer and the layer below, which is the rect a row
    obstruction must not touch (the pin rect itself is inside it).  The margin (kv3_phy_v1 review: a window ending 0.06 um from the
    bare 8-um corridor left the router no jog room) makes the stand-off real, not an abutment."""
    out = []
    if land_clear <= 0:
        return out
    for p in ((t.get("clock") or {}).get("landing_contract") or {}).get("pins") or []:
        xy, ln = p.get("xy_um"), p.get("layer")
        if not (isinstance(xy, (list, tuple)) and len(xy) == 2 and ln):
            continue
        x, y = float(xy[0]), float(xy[1])
        f = min(("E", w - x), ("W", x), ("N", h - y), ("S", y), key=lambda fd: fd[1])[0]
        lw = G.LAYER_W.get(ln, 0.04) / 2; hl = LAND_PIN_LEN_UM / 2
        r = (x - lw, y - hl, x + lw, y + hl)
        L, sd = land_clear + margin, side + margin
        c = {"E": (x - L, r[1] - sd, w, r[3] + sd), "W": (0.0, r[1] - sd, x + L, r[3] + sd),
             "N": (r[0] - sd, y - L, r[2] + sd, h), "S": (r[0] - sd, 0.0, r[2] + sd, y + L)}[f]
        for l2 in (ln, _lower(ln)):
            if l2:
                out.append((str(p.get("name")), l2, f, c, c))
    return out


def row_obs(G, tn, r):
    """[(layer, rect)] of one die_clock_tree row: route layers over the rect, stack layers over each stack window"""
    out = [(ln, tuple(r["rect_um"])) for ln in G.route_layer_names(r.get("route_layers") or "M1-M7")]
    if r.get("stack_um"):
        out += [(ln, s) for ln in G.route_layer_names(r["stack_layers"]) for s in G.stack_rects(tn, r)]
    return out


def _shift(rc, dx, dy):
    return (rc[0] + dx, rc[1] + dy, rc[2] + dx, rc[3] + dy)


def pin_hits(obs, pins, use_corridor=False):
    """[(pin, layer, face)] whose pin rect (or access corridor) a same-layer obstruction of `obs` overlaps"""
    by = {}
    for ln, s in obs:
        by.setdefault(ln, []).append(s)
    hs = []
    for n, ln, f, r, c in pins:
        q = c if use_corridor else r
        if any(ov(q, s) for s in by.get(ln, ())):
            hs.append((n, ln, f))
    return hs


def candidates(faces, max_move, site, row):
    """(travel, rank, dx, dy) axis-aligned moves within max_move; rank 0 inward, 1 slide along a hit face, 2 outward"""
    inward = {"E": (-1, 0), "W": (1, 0), "N": (0, -1), "S": (0, 1)}
    want = {inward[f] for f in faces}
    slide = set()
    for f in faces:
        slide |= {(0, 1), (0, -1)} if f in "EW" else {(1, 0), (-1, 0)}
    out = []
    for ux, uy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        rank = 0 if (ux, uy) in want else (1 if (ux, uy) in slide else 2)
        step = site if ux else row
        for k in range(1, int(math.floor(max_move / step + 1e-6)) + 1):
            dx, dy = round(ux * k * step, 6), round(uy * k * step, 6)
            out.append((round(abs(dx) + abs(dy), 6), rank, abs(dx), abs(dy), dx, dy))
    # a corner row (hit pins on an E/W face AND an N/S face) also tries the diagonal inward moves
    vx = [u for u in want if u[0]]; vy = [u for u in want if u[1]]
    if len(vx) == 1 and len(vy) == 1:
        ux, uy = vx[0][0], vy[0][1]
        for i in range(1, int(math.floor(max_move / site + 1e-6)) + 1):
            for j in range(1, int(math.floor((max_move - i * site) / row + 1e-6)) + 1):
                dx, dy = round(ux * i * site, 6), round(uy * j * row, 6)
                out.append((round(abs(dx) + abs(dy), 6), 0, abs(dx), abs(dy), dx, dy))
    out.sort(key=lambda c: (c[1], c[0], c[2], c[3], c[4], c[5]))     # inward first, then slide, then outward; shortest within each
    return [(t, r, dx, dy) for t, r, _, _, dx, dy in out]


def resolve_row(G, RS, tn, t, e, others, cores, pts, pins, clear, max_move):
    """-> (dx, dy, rank) of the shortest legal corridor-clear move of row e, or None"""
    obs = row_obs(G, tn, e)
    faces = sorted({f for _, _, f in pin_hits(obs, pins)})
    for _, rank, dx, dy in candidates(faces, max_move, RS.SITE_UM, RS.ROW_UM):
        rc = _shift(tuple(e["rect_um"]), dx, dy)
        if not RS._legal(rc, t, cores, others, pts):
            continue
        if pin_hits([(ln, _shift(s, dx, dy)) for ln, s in obs], pins, use_corridor=True):
            continue
        return dx, dy, rank
    return None


def shift_row(r, dx, dy):
    r["rect_um"] = [round(v, 6) for v in _shift(r["rect_um"], dx, dy)]
    if r.get("stack_um"):
        r["stack_um"] = [[round(v, 6) for v in _shift(s, dx, dy)] for s in r["stack_um"]]


def _parts(raw):
    pr = raw.get("partitions") or {}
    return pr.items() if isinstance(pr, dict) else [(v.get("name"), v) for v in pr]


def run(P, raw, G, RS, CP, types=None, clear=2.0, max_move=20.0, side=0.1, land_clear=LAND_CLEAR_UM, land_margin=LAND_MARGIN_UM):
    led = []
    parts_all = list(_parts(raw))
    for tn in sorted(raw["partition_types"]):
        if types and tn not in types:
            continue
        t = raw["partition_types"][tn]
        rs = (t.get("clock") or {}).get("reserved_sites_um") or []
        if not any(e.get("kind") == "die_clock_tree" for e in rs):
            continue
        w, h = t["outline_um"]
        pins = type_pin_index(G, P, tn, w, h, clear, side) + landing_pin_index(G, t, w, h, land_clear, side, land_margin)
        cores = [RS._grow(c, CP.CORE_HALO_UM) for c in CP._cores(t)]
        pts = [c[i] for _, c, i, _ in CP.points(t)]
        pts = [p for p in pts if isinstance(p, (list, tuple)) and len(p) == 2]
        parts = [(n, v.get("origin_um"), str(v.get("orient", "R0"))) for n, v in parts_all if v.get("type") == tn]
        for k, e in enumerate(rs):
            if e.get("kind") != "die_clock_tree":
                continue
            hs = pin_hits(row_obs(G, tn, e), pins)
            if not hs:
                continue
            old = list(e["rect_um"])
            faces = sorted({f for _, _, f in hs})
            others = [tuple(o["rect_um"]) for j, o in enumerate(rs) if j != k]
            mv = resolve_row(G, RS, tn, t, e, others, cores, pts, pins, clear, max_move)
            if mv is None:
                led.append(dict(type=tn, index=k, old=old, new=None, faces=faces, pins=sorted({n for n, _, _ in hs}),
                                why=f"no legal corridor-clear site within {max_move} um"))
                continue
            dx, dy, rank = mv
            shift_row(e, dx, dy)
            n = e["rect_um"]
            led.append(dict(type=tn, index=k, old=old, new=n, faces=faces, move_um=[dx, dy],
                            kind=("inward", "slide", "outward")[rank], pins_cleared=sorted({p for p, _, _ in hs}),
                            die_centre_um={p: ([round(o[0] + (n[0] + n[2]) / 2, 4), round(o[1] + (n[1] + n[3]) / 2, 4)]
                                               if orient == "R0" else dict(origin_um=o, orient=orient)) for p, o, orient in parts}))
    return led


def recheck(P, raw, G, types=None, land_clear=LAND_CLEAR_UM, side=0.1, land_margin=LAND_MARGIN_UM):
    """pin-rect hits (the kit_pin_site_check class) and landing-pin escape-corridor hits left on the plan -> {type: n}"""
    left = {}
    for tn in sorted(raw["partition_types"]):
        if types and tn not in types:
            continue
        t = raw["partition_types"][tn]
        rows = [e for e in (t.get("clock") or {}).get("reserved_sites_um") or [] if e.get("kind") == "die_clock_tree"]
        if not rows:
            continue
        w, h = t["outline_um"]
        pins = type_pin_index(G, P, tn, w, h, 0.0) + landing_pin_index(G, t, w, h, land_clear, side, land_margin)
        n = sum(len(pin_hits(row_obs(G, tn, e), pins)) for e in rows)
        if n:
            left[tn] = n
    return left


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan"); ap.add_argument("-o", required=True); ap.add_argument("--ledger", required=True)
    ap.add_argument("--types"); ap.add_argument("--clear-um", type=float, default=2.0)
    ap.add_argument("--land-clear-um", type=float, default=LAND_CLEAR_UM, help="landing-pin escape corridor length (0 = off)")
    ap.add_argument("--land-margin-um", type=float, default=LAND_MARGIN_UM, help="stand-off added to the landing corridor (far end, both sides)")
    ap.add_argument("--max-move-um", type=float, default=20.0)
    ap.add_argument("--side-um", type=float, default=0.1, help="corridor margin along the face on each side of a pin (spacing)")
    ap.add_argument("--rt", default=str(Path(__file__).resolve().parents[2]))
    a = ap.parse_args(argv)
    schema, G, RS, CP = load(a.rt)
    path = Path(a.plan); raw = json.load(open(path))
    types = set(a.types.split(",")) if a.types else None
    P = schema.Plan(raw, path.parent / "die_plan.json")
    led = run(P, raw, G, RS, CP, types, a.clear_um, a.max_move_um, a.side_um, a.land_clear_um, a.land_margin_um)
    P2 = schema.Plan(json.loads(json.dumps(raw)), path.parent / "die_plan.json")
    left = recheck(P2, raw, G, types, a.land_clear_um, a.side_um, a.land_margin_um)
    stuck = [x for x in led if x["new"] is None]
    json.dump(raw, open(a.o, "w"), indent=1, ensure_ascii=False)
    mv = [abs(x["move_um"][0]) + abs(x["move_um"][1]) for x in led if x["new"]]
    summ = dict(rows_moved=len(led) - len(stuck), not_moved=len(stuck), types=len({x["type"] for x in led}),
                max_moved_um=round(max(mv, default=0.0), 4), hits_left=sum(left.values()),
                kinds={k: sum(1 for x in led if x.get("kind") == k) for k in ("inward", "slide", "outward")})
    json.dump(dict(clear_um=a.clear_um, land_clear_um=a.land_clear_um, land_margin_um=a.land_margin_um, side_um=a.side_um, max_move_um=a.max_move_um, hits_left_by_type=left, rows=led, **summ),
              open(a.ledger, "w"), indent=1)
    print(json.dumps(summ))
    return 1 if stuck or left else 0


if __name__ == "__main__":
    sys.exit(main())
