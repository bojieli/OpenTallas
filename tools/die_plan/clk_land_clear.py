#!/usr/bin/env python3
"""CLK-LAND-CLEAR (class C-CLK-LAND-OBS + C-SITE-IN-MACRO; plan flag `clk_land_clear: {"enable": 1}`, default off).

Generator step: every type's clock landings, reserved die clock sites and relay seats are re-sited clear of every hard macro
(adv_clk_land_obs.py is the matching report-only check).  Flag absent = no code path runs, P.types is raw["partition_types"].

  tap       clock.taps[].xy (core taps clk_c<k> included), added_taps[].xy, edge_clocks[].tap_um, clock.tap_um: a point inside the BODY
            of a macro whose metal reaches the via layer below the entry layer (the landing via stack crosses its OBS) moves by the
            smallest axis-aligned move to a point clear of every obstructing macro body + halo + CLEAR_UM (gen_phys.core_tap_pins only
            moves a tap up to ENTRY_CLEAR_MAX_UM = 2 um, so a deeper tap stayed buried: S81 lepw_mus_C clk_c11 23.3 um in capc5r).
  reserved  clock.reserved_sites_um die_clock_tree: a rect overlapping a macro body or halo moves (rect + every stack_um window, same
            size) by the smallest legal translation (clksite_resite candidate rule: clear of every macro + halo, every other
            reserved rect, planned register points, inside the outline); then clksite_pinclear moves any row whose obstruction
            still covers a face-pin corridor (needs gen_phys; P given).  HEAD hd_host_w BF50: 10 windows in SRAM bodies + 9 in halo.
  relay     relay_sites{name: xy}: body (0.5 um inset) or halo ring of any macro -> nearest point clear of every macro + halo, not
            within 0.5 um of another relay / the other relays' seats (no stacking is created).
Options (all optional): clear_um (2.0), land_clear_um (8.0, the landing-pin escape corridor of the clksite_pinclear pass), max_move_um (120), classes (["tap","reserved","relay"]), types (limit to these types).
A move over max_move_um (default 120 taps / relays, 80 reserved) is left and reported `new: null` in the ledger.

  clk_land_clear.py PLAN -o OUT.json --ledger L.json [--types T,..] [--clear-um 2.0] [--max-move-um 120] [--rt RT]
"""
import copy
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_clk_land_obs as A  # noqa: E402

ROW_UM, SITE_UM = 0.27, 0.054
CLEAR_UM = 2.0
MAX_MOVE_UM = 120.0
RES_MAX_MOVE_UM = 80.0
SEP_UM = 0.5
EPS = 1e-6
CLASSES = ("tap", "reserved", "relay")


def enabled(raw):
    v = (raw or {}).get("clk_land_clear")
    return bool(isinstance(v, dict) and v.get("enable"))


def _opts(raw):
    v = (raw or {}).get("clk_land_clear") or {}
    return dict(clear=float(v.get("clear_um", CLEAR_UM)), max_move=float(v.get("max_move_um", MAX_MOVE_UM)),
                classes=tuple(v.get("classes") or CLASSES), types=set(v.get("types") or ()),
                land_clear=float(v.get("land_clear_um", 8.0)))


def _up(v, step):
    return round(math.ceil(v / step - 1e-9) * step, 6)


def _dn(v, step):
    return round(math.floor(v / step + 1e-9) * step, 6)


def _inside(g, b):
    return b[0] < g[0] < b[2] and b[1] < g[1] < b[3]


def _legal(c, boxes, outline, occupied, margin_out):
    w, h = outline
    if not (margin_out <= c[0] <= w - margin_out and margin_out <= c[1] <= h - margin_out):
        return False
    if any(_inside(c, b) for b in boxes):
        return False
    return not any(abs(c[0] - o[0]) < SEP_UM and abs(c[1] - o[1]) < SEP_UM for o in occupied)


def clear_point(p, boxes, outline, occupied=(), max_move=MAX_MOVE_UM, margin_out=0.5):
    """nearest legal point (axis-aligned exit of a containing box, then slides along the edge) or None.  boxes: grown rects"""
    x, y = p
    cands = []
    front = [b for b in boxes if _inside(p, b)]
    seen = set()
    for _ in range(4):
        nxt = []
        for b in front:
            if b in seen:
                continue
            seen.add(b)
            ex = (_dn(b[0], SITE_UM) - SITE_UM, y, "x"), (_up(b[2], SITE_UM) + SITE_UM, y, "x"), \
                 (x, _dn(b[1], ROW_UM) - ROW_UM, "y"), (x, _up(b[3], ROW_UM) + ROW_UM, "y")
            for cx, cy, ax in ex:
                for k in range(0, 9):
                    for s in ((0,) if k == 0 else (k, -k)):
                        c = (round(cx + (s * 1.08 if ax == "y" else 0), 6), round(cy + (s * 1.08 if ax == "x" else 0), 6))
                        cands.append(c)
                        for b2 in boxes:
                            if _inside(c, b2) and b2 not in seen:
                                nxt.append(b2)
        front = nxt
    best = None
    for c in cands:
        d = abs(c[0] - x) + abs(c[1] - y)
        if d > max_move + EPS or not _legal(c, boxes, outline, occupied, margin_out):
            continue
        k = (round(d, 6), c)
        if best is None or k < best:
            best = k
    return None if best is None else best[1]


def _grown_all(ms, extra=0.0):
    return [(x0 - halo - extra, y0 - halo - extra, x1 + halo + extra, y1 + halo + extra) for x0, y0, x1, y1, halo, _n, _o, _v in ms]


def _tap_ledger(tn, t, top, roots, o, led):
    ms = A.macros(t, top, roots)
    obsm = [m for m in ms if m[6]]
    if not obsm:
        return
    boxes = _grown_all(obsm, o["clear"])
    occ = [g for c, _l, g, _s in A.landings(t) if c == "tap"]
    for cls, lab, g, setter in A.landings(t):
        if cls != "tap" or A.hit("tap", g, ms, lab) is None:
            continue
        occ.remove(g)
        n = clear_point(g, boxes, t["outline_um"], occ, o["max_move"])
        macro = A.hit("tap", g, ms, lab)[0]
        if n is None:
            occ.append(g)
            led.append(dict(type=tn, cls="tap", label=lab, old=list(g), new=None, macro=macro, why=f"no legal point within {o['max_move']} um"))
            continue
        setter(n)
        occ.append(n)
        led.append(dict(type=tn, cls="tap", label=lab, old=list(g), new=list(n), macro=macro, move_um=round(abs(n[0] - g[0]) + abs(n[1] - g[1]), 4)))


def _relay_ledger(tn, t, top, roots, o, led):
    ms = A.macros(t, top, roots)
    if not ms:
        return
    rel = t.get("relay_sites")
    if not isinstance(rel, dict):
        return
    boxes = _grown_all(ms, 0.5)
    occ = [(float(p[0]), float(p[1])) for p in rel.values() if A._xy(p)]
    for n, p in sorted(rel.items(), key=lambda kv: str(kv[0])):
        if not A._xy(p):
            continue
        g = (float(p[0]), float(p[1]))
        h = A.hit("relay", g, ms)
        if h is None:
            continue
        occ.remove(g)
        c = clear_point(g, boxes, t["outline_um"], occ, o["max_move"])
        if c is None:
            occ.append(g)
            led.append(dict(type=tn, cls="relay", label=f"relay_sites[{n}]", old=list(g), new=None, macro=h[0], why=f"no legal point within {o['max_move']} um"))
            continue
        rel[n] = [c[0], c[1]] + list(p[2:])
        occ.append(c)
        led.append(dict(type=tn, cls="relay", label=f"relay_sites[{n}]", old=list(g), new=list(c), macro=h[0], where=h[1],
                        move_um=round(abs(c[0] - g[0]) + abs(c[1] - g[1]), 4)))


def _reserved_ledger(tn, t, top, roots, o, led):
    import clksite_points as CP
    import clksite_resite as RS
    ck = t.get("clock") or {}
    rs = ck.get("reserved_sites_um") or []
    ms = A.macros(t, top, roots)
    if not rs or not ms:
        return
    gcores = _grown_all(ms)
    pts = [c[i] for _, c, i, _ in CP.points(t)]
    pts = [p for p in pts if isinstance(p, (list, tuple)) and len(p) == 2]
    for k, e in enumerate(rs):
        if e.get("kind") != "die_clock_tree" or A.hit("reserved", tuple(e["rect_um"]), ms) is None:
            continue
        r = tuple(e["rect_um"])
        hit = A.hit("reserved", r, ms)
        others = [tuple(q["rect_um"]) for j, q in enumerate(rs) if j != k]
        blk = [m for m in ms if r[0] < m[2] + m[4] and m[0] - m[4] < r[2] and r[1] < m[3] + m[4] and m[1] - m[4] < r[3]]
        best = None
        for m in blk or ms[:1]:
            core = (m[0], m[1], m[2], m[3])
            for _, d, n in sorted(RS._candidates(r, core, m[4], o["max_move"])):
                while True:
                    mv = abs(n[0] - r[0]) + abs(n[1] - r[1])
                    if mv > min(o["max_move"], RES_MAX_MOVE_UM) + 1e-9:
                        break
                    if RS._legal(n, t, gcores, others, pts):
                        if best is None or mv < best[0] - 1e-9:
                            best = (mv, d, n)
                        break
                    n = RS._step(d, n)
        row = dict(type=tn, cls="reserved", label=f"clock.reserved_sites_um[{k}]", old=list(r), macro=hit[0], where=hit[1])
        if best is None:
            row.update(new=None, why=f"no legal site within {min(o['max_move'], RES_MAX_MOVE_UM)} um")
        else:
            mv, d, n = best
            dx, dy = round(n[0] - r[0], 6), round(n[1] - r[1], 6)
            e["rect_um"] = [round(v, 6) for v in n]
            if e.get("stack_um"):
                e["stack_um"] = [[round(v, 6) for v in (s[0] + dx, s[1] + dy, s[2] + dx, s[3] + dy)] for s in e["stack_um"]]
            row.update(new=e["rect_um"], dir=d, move_um=round(mv, 4))
        led.append(row)


def apply(types, raw, plan_path=None, P=None, root=None, only=None):
    """re-site the landings of `types` (dict name -> type, replaced in place by private copies where a value changes) -> ledger rows.
    P (schema.Plan over `types`) enables the clksite_pinclear pass after the reserved-site re-site."""
    o = _opts(raw)
    top, roots = A.entry_top(raw), A._roots(plan_path, root)
    led = []
    only = (set(only) if only else set()) | o["types"] or None      # flag option "types": [..] limits the step to those types
    for tn in sorted(types):
        if only and tn not in only:
            continue
        t0 = types[tn]
        if not isinstance(t0, dict) or not t0.get("outline_um"):
            continue
        hs = A.classify(t0, top, roots)
        has_res = P is not None and any(e.get("kind") == "die_clock_tree" for e in ((t0.get("clock") or {}).get("reserved_sites_um") or []))
        if not hs and not has_res:
            continue
        t = types[tn] = copy.deepcopy(t0)
        if "tap" in o["classes"]:
            _tap_ledger(tn, t, top, roots, o, led)
        if "reserved" in o["classes"]:
            _reserved_ledger(tn, t, top, roots, o, led)
        if "relay" in o["classes"]:
            _relay_ledger(tn, t, top, roots, o, led)
        if not any(r["type"] == tn and r["new"] is not None for r in led) and t == t0:
            types[tn] = t0                              # nothing changed: keep the shared object
    if P is not None and "reserved" in o["classes"]:
        led += _pinclear(types, raw, P, only, o["land_clear"])
    return led


def _pinclear(types, raw, P, only, land_clear=8.0):
    import gen_phys as G
    import clksite_pinclear as PC
    import clksite_points as CP
    import clksite_resite as RS
    todo = {tn for tn, t in types.items() if (not only or tn in only)
            and any(e.get("kind") == "die_clock_tree" for e in ((t.get("clock") or {}).get("reserved_sites_um") or []))}
    for tn in todo:                                      # private copy before an in-place row shift
        types[tn] = copy.deepcopy(types[tn])
    fake = {"partition_types": types, "partitions": raw.get("partitions")}
    led = PC.run(P, fake, G, RS, CP, todo or None, 2.0, 20.0, 0.1, land_clear)
    for r in led:
        r["cls"] = "reserved-pinclear"
    return led


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan"); ap.add_argument("-o", required=True); ap.add_argument("--ledger", required=True)
    ap.add_argument("--types"); ap.add_argument("--clear-um", type=float, default=CLEAR_UM)
    ap.add_argument("--max-move-um", type=float, default=MAX_MOVE_UM)
    ap.add_argument("--rt", default=str(Path(__file__).resolve().parents[2]))
    ap.add_argument("--no-pinclear", action="store_true")
    a = ap.parse_args(argv)
    raw = json.loads(Path(a.plan).read_text())
    raw["clk_land_clear"] = {"enable": 1, "clear_um": a.clear_um, "max_move_um": a.max_move_um}
    only = set(a.types.split(",")) if a.types else None
    P = None
    if not a.no_pinclear:
        import schema
        flagless = {k: v for k, v in raw.items() if k != "clk_land_clear"}
        flagless["partition_types"] = raw["partition_types"]
        P = schema.Plan(flagless, Path(a.plan).parent / "die_plan.json")
        types = dict(raw["partition_types"])       # rows are written to the plan's own types; P.types (landing pins separated at load) only prices pins
    else:
        types = raw["partition_types"]
    led = apply(types, raw, a.plan, P=P, only=only)
    raw["partition_types"] = dict(types)
    raw.pop("clk_land_clear", None)
    json.dump(raw, open(a.o, "w"), indent=1, ensure_ascii=False)
    stuck = [x for x in led if x.get("new") is None]
    summ = dict(moved=len(led) - len(stuck), not_moved=len(stuck), by_cls={c: sum(1 for x in led if x["cls"] == c and x.get("new")) for c in sorted({x["cls"] for x in led})})
    json.dump(dict(summary=summ, rows=led), open(a.ledger, "w"), indent=1)
    print(json.dumps(summ))
    return 1 if stuck else 0


if __name__ == "__main__":
    sys.exit(main())
