#!/usr/bin/env python3
"""boundary_reg.py -- BOUNDARY-REG-50 (COORD 19:25 FABLE-RC-KV item 3, CBC both-side boundary rule, spec L712 FP-BOUNDARY-49).

Every OUT pin of a type gets one planned register (station) within RADIUS_UM (50 um, Manhattan) on the type's own side.
A bus pin carries its face register by construction (taps.planned_sinks R2: one face register per bus pin), so the
pins that miss are feed-through out pins: an ft slot's last station sits a full hop (~300 um) before its `<slot>_o`
pins and only the neighbour's station 0 is near the seam.  KV R6: 53 types / 67,231 ft out bits (precheck BOUNDARY-REG).

Two entry points, one rule:
  findings(raw, plan_path, tree=None, **kw)  plan_advisory check BOUNDARY-REG-50; WARN lines (report only), FAIL lines only
                                             with OT_BREG_BLOCK=1 (for plan_gate_pre once the counts are stable).
  plan  PLAN --out OPS.json [--types a,b]     apply_ops ops ({"row":..., "ops":[...]}, replace with old checks) that give
                                             each missing slot an out-face station: per-bit sites next to each `_o` pin
                                             (inset FACE_INSET_UM, stacked inward, snapped to the 0.216 x 0.27 grid,
                                             outside hard cores + 5 um, off every other slot's sites), station point =
                                             the group centre.  MOVE the slot's last station there when the hop from
                                             the station before it stays <= reach_um (no cycle added); else ADD one
                                             station (stations + 1, one cycle; plan changes pre-approved, REPRICE prices
                                             it).  A slot it cannot seat is listed, never half-written.

Reading = precheck.py BOUNDARY-REG (CBC r713): a pin is covered when ANY planned register (taps.planned_sinks) lies within
the radius; the planner seats the slot's own station at its out face.

Station model (taps.planned_sinks / ft_bit_sites.validate_slot / adv_bitsite_seat): ft_slots[i].regs_um has `stations`
points (station 0 at the in pin); bit_sites_um has stations-1 groups (stations with explicit_stage0) of width+1 cell
lower-left sites (payload bits 0..width-1, then the epoch site); group j belongs to regs_um[j + off], off = 1 (0 with
explicit_stage0).  A slot without bit_sites_um is judged at its station point.
"""
import argparse
import collections
import json
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

CHECK = "BOUNDARY-REG-50"
TAG = "ADV-" + CHECK                # plan_advisory line tag
RADIUS_UM = 50.0
FACE_INSET_UM = 2.0
GRID_X, GRID_Y = 0.216, 0.27
CORE_HALO_UM = 5.0
REACH_UM = 405.0
MAX_LINES = 60


def _snap(v, g):
    return round(round(v / g) * g, 4)


def _up(v, g):
    return round(math.ceil(v / g - 1e-9) * g, 4)


def _md(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _core_boxes(t, halo=CORE_HALO_UM):
    out = []
    for c in t.get("hard_cores") or []:
        if c.get("origin_um") and c.get("outline_um"):
            x, y = c["origin_um"]
            w, h = c["outline_um"]
            out.append((x - halo, y - halo, x + w + halo, y + h + halo))
    return out


def out_pins(P, tn):
    """{slot name: [(bit, x, y, face)]} type-frame `<slot>_o` pins of every ft slot of type tn (gen_phys.type_pins)."""
    import gen_phys as G
    t = P.types[tn]
    slots = {s["name"] for s in t.get("ft_slots") or []}
    out = collections.defaultdict(list)
    for name, bit, _ln, x, y, face in G.type_pins(P, tn):
        if name.endswith("_o") and name[:-2] in slots:
            out[name[:-2]].append((int(bit), float(x), float(y), face))
    for v in out.values():
        v.sort()
    return out


def planned_regs(P, tn):
    """[(x, y)] every FIRM-planned register site of type tn (taps.planned_sinks: face registers, ft stations, per-bit
    station rows, soft banks) -- the precheck BOUNDARY-REG reading (CBC r713), with each ft station at its exact per-bit
    cell centres where the slot plans bit_sites_um (what face_flops.tcl places; precheck's station point is the
    bundle centre, so a wide out-face bundle reads as uncovered at its ends)."""
    import taps as T
    return [(float(x), float(y)) for x, y, _k in T.planned_sinks(P, tn, bit_sites=True)]


def _near(regs, radius):
    cell = max(radius, 1.0)
    grid = collections.defaultdict(list)
    for x, y in regs:
        grid[(int(x // cell), int(y // cell))].append((x, y))

    def best(x, y):
        gx, gy = int(x // cell), int(y // cell)
        b = None
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                for q in grid.get((gx + i, gy + j), ()):
                    d = abs(q[0] - x) + abs(q[1] - y)
                    b = d if b is None or d < b else b
        return b
    return best


def slot_misses(t, pins, regs, radius=RADIUS_UM):
    """[(slot index, slot name, missing bits, bits, worst um or None)] ft slots with out pins that have no planned
    register within radius (Manhattan)."""
    best = _near(regs, radius)
    out = []
    for i, s in enumerate(t.get("ft_slots") or []):
        op = pins.get(s["name"])
        if not op:
            continue
        miss, worst = 0, 0.0
        for _bit, x, y, _f in op:
            d = best(x, y)
            if d is None or d > radius:
                miss += 1
                worst = max(worst, d if d is not None else 2 * radius)
        if miss:
            out.append((i, s["name"], miss, len(op), worst))
    return out


def _plan(raw, plan_path):
    import schema as S
    return S.Plan(raw, Path(plan_path))


def findings(raw, plan_path=None, tree=None, radius=RADIUS_UM, **kw):
    lvl = "FAIL" if os.environ.get("OT_BREG_BLOCK") == "1" else "WARN"
    try:
        P = _plan(raw, plan_path)
    except Exception as e:  # noqa: BLE001 an advisory never breaks the gate
        return [f"WARN {TAG} not checked: plan load {type(e).__name__}: {str(e)[:120]}"]
    out, ntypes, nbits, nslots = [], 0, 0, 0
    for tn in sorted(P.types):
        t = P.types[tn]
        if t.get("hard"):
            continue
        try:
            m = slot_misses(t, out_pins(P, tn), planned_regs(P, tn), radius)
        except Exception as e:  # noqa: BLE001 a malformed type never stops the others
            out.append(f"WARN {TAG} {tn}: not checked ({type(e).__name__}: {str(e)[:100]})")
            continue
        if not m:
            continue
        ntypes += 1
        b = sum(x[2] for x in m)
        nbits += b
        nslots += len(m)
        worst = sorted(m, key=lambda x: -x[2])[:4]
        out.append(f"{lvl} {TAG} {tn}: {b} ft out bit(s) on {len(m)} slot(s) have no station within {radius:.0f} um of their pin "
                   f"({', '.join(f'{n}_o {k}/{w}b' + (f' >{d:.0f}um' if d < 2 * radius else ' none near') for _i, n, k, w, d in worst)}); "
                   "fix: boundary_reg.py plan (out-face station, MOVE last or ADD one)")
    out.append(f"WARN {TAG} summary {ntypes} type(s), {nslots} ft slot(s), {nbits} out bit(s) without a station within "
               f"{radius:.0f} um (bus pins carry face registers by construction)")
    return out


def _seat(pins, width, cell, blocked, taken, t, radius):
    """per-bit cell lower-left sites (width payload + 1 epoch) next to the out pins, or (None, why)."""
    W, H = t["outline_um"]
    cw, ch = cell
    face = pins[0][3]
    if any(p[3] != face for p in pins):
        return None, "out pins on more than one face"
    ew = face in "EW"
    sa = _up(ch if ew else cw, GRID_Y if ew else GRID_X)          # along-face pitch
    sd = _up(cw if ew else ch, GRID_X if ew else GRID_Y)          # inward pitch
    gd = GRID_X if ew else GRID_Y
    used = set(taken)
    sites = {}

    def ok(x, y):
        if x < 0 or y < 0 or x + cw > W or y + ch > H:
            return False
        if any(a < x + cw and x < c and b < y + ch and y < d for a, b, c, d in blocked):
            return False
        return (round(x / GRID_X), round(y / GRID_Y)) not in used

    def place(px, py, key):
        for r in range(0, int(radius / sd) + 1):
            depth = FACE_INSET_UM + r * sd
            for k in range(0, int(radius / sa) + 1):
                for sgn in ((0,) if k == 0 else (1, -1)):
                    along = sgn * k * sa
                    if ew:
                        x = _snap((W - depth - cw) if face == "E" else depth, gd)
                        y = _snap(py + along - ch / 2, GRID_Y)
                    else:
                        x = _snap(px + along - cw / 2, GRID_X)
                        y = _snap((H - depth - ch) if face == "N" else depth, gd)
                    if _md((x + cw / 2, y + ch / 2), (px, py)) > radius - 1.0:
                        continue
                    if ok(x, y):
                        used.add((round(x / GRID_X), round(y / GRID_Y)))
                        sites[key] = [x, y]
                        return True
        return False

    by = {b: (x, y) for b, x, y, _f in pins}
    # the slot's out pins are its width payload bits plus the epoch bit (bit `width`), each next to its own pin; a pin
    # table without the epoch pin seats the epoch site at the bundle centre
    if sorted(by) not in (list(range(width)), list(range(width + 1))):
        return None, f"out pins {len(by)} do not cover bits 0..{width - 1} (+ epoch {width})"
    for b in sorted(by):
        if not place(*by[b], b):
            return None, f"bit {b}: no free legal site within {radius:.0f} um of its pin"
    if width not in sites:
        cx = sum(v[0] for v in by.values()) / len(by)
        cy = sum(v[1] for v in by.values()) / len(by)
        if not place(cx, cy, width):
            return None, "epoch site: no free legal site"
    return [sites[k] for k in range(width + 1)], ""


def plan_ops(raw, plan_path, types=None, radius=RADIUS_UM, reach=None):
    """-> (ops, report rows) for every missing slot of the selected types."""
    P = _plan(raw, plan_path)
    reach = reach or float((raw.get("die") or {}).get("reach_um") or REACH_UM)
    ops, rep = [], []
    for tn in sorted(P.types):
        if types and tn not in types:
            continue
        t = P.types[tn]
        if t.get("hard"):
            continue
        pins = out_pins(P, tn)
        miss = slot_misses(t, pins, planned_regs(P, tn), radius)
        if not miss:
            continue
        blocked = _core_boxes(t)
        taken = set()
        for s in t.get("ft_slots") or []:
            for g in s.get("bit_sites_um") or []:
                for x, y in g:
                    taken.add((round(x / GRID_X), round(y / GRID_Y)))
        for i, name, k, w, d in miss:
            s = t["ft_slots"][i]
            base = f"/partition_types/{tn}/ft_slots/{i}"
            regs = [list(r) for r in s.get("regs_um") or []]
            n = int(s.get("stations", 1))
            bs = s.get("bit_sites_um")
            if regs and len(regs) != n:
                rep.append((tn, name, "SKIP", f"regs_um {len(regs)} != stations {n}"))
                continue
            if bs is None:
                cell = s.get("bit_site_cell_um") or [GRID_X * 5, GRID_Y]
                grp, why = _seat(pins[name], int(s.get("width", 1)), cell, blocked, taken, t, radius)
                if grp is None:
                    rep.append((tn, name, "SKIP", why))
                    continue
                cen = [_snap(sum(q[0] + cell[0] / 2 for q in grp) / len(grp), GRID_X),
                       _snap(sum(q[1] + cell[1] / 2 for q in grp) / len(grp), GRID_Y)]
                if any(_md(cen, (x, y)) > radius for _b, x, y, _f in pins[name]):
                    rep.append((tn, name, "SKIP", "no bit sites and the pin span does not fit one station point"))
                    continue
                grp = None
            else:
                cell = s["bit_site_cell_um"]
                grp, why = _seat(pins[name], int(s.get("width", 1)), cell, blocked, taken, t, radius)
                if grp is None:
                    rep.append((tn, name, "SKIP", why))
                    continue
                cen = [_snap(sum(q[0] + cell[0] / 2 for q in grp) / len(grp), GRID_X),
                       _snap(sum(q[1] + cell[1] / 2 for q in grp) / len(grp), GRID_Y)]
            move = len(regs) >= 2 and _md(regs[-2], cen) <= reach
            new_regs = regs[:-1] + [cen] if move else regs + [cen]
            ops.append(dict(op="replace", path=base + "/regs_um", old=s.get("regs_um"), value=new_regs))
            if not move:
                ops.append(dict(op="replace", path=base + "/stations", old=s.get("stations", 1), value=n + 1))
            if grp is not None:
                new_bs = [list(map(list, g)) for g in bs]
                if move and new_bs:
                    new_bs[-1] = grp
                else:
                    new_bs.append(grp)
                ops.append(dict(op="replace", path=base + "/bit_sites_um", old=bs, value=new_bs))
                for x, y in grp:
                    taken.add((round(x / GRID_X), round(y / GRID_Y)))
            hop = _md(regs[-1], cen) if regs and not move else (_md(regs[-2], cen) if move else 0.0)
            rep.append((tn, name, "MOVE" if move else "ADD", f"{k}/{w}b worst {d:.0f}um -> station {cen} hop {hop:.0f}um"
                        + (" (> reach: LEG405)" if hop > reach else "")))
    return ops, rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("report")
    r.add_argument("plan")
    r.add_argument("--radius", type=float, default=RADIUS_UM)
    p = sub.add_parser("plan")
    p.add_argument("plan")
    p.add_argument("--out", required=True)
    p.add_argument("--types", default="")
    p.add_argument("--radius", type=float, default=RADIUS_UM)
    p.add_argument("--row", default="BOUNDARY-REG-50")
    a = ap.parse_args(argv)
    raw = json.load(open(a.plan))
    if a.cmd == "report":
        for x in findings(raw, a.plan, radius=a.radius):
            print(x)
        return 0
    types = {x for x in a.types.split(",") if x} or None
    ops, rep = plan_ops(raw, a.plan, types, a.radius)
    json.dump(dict(row=a.row, ops=ops), open(a.out, "w"), indent=1)
    c = collections.Counter(x[2] for x in rep)
    for x in rep:
        print("BREG", *x)
    print(f"BREG-PLAN {len(ops)} op(s); {dict(c)}; out {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
