"""adv_firm_fixed_seat.py -- PRECHECK advisory ADV-FIRM-FIXED-SEAT (CLASS-OWNERS-R3 R3-FIRMSEAT, class C-FIXEDSITE-FIRM-OVERLAP;
REPORT ONLY, never a gate).

Class found on QC TT (QC-R3-TT 11-27, r3c probe2c): the kit places the FIRM reset relays (reset_tree.tcl rtr_place, tag rrl:*) and
the landing cells (landing_placement.tcl cland_put*, tag cland:*) BEFORE place_fixed_sites.tcl seeds the fixed seats of
place_regions kind "fixed" (face_flops.tcl order).  seed() records FIRM cells as reserved with check=0 and only checks the fixed
seats against each other, so a fixed seat the plan puts under a FIRM relay / reader is silently overlapped: 12 overlaps on 10 seats
(u_rrl_4/5/62/82/82_g, u_srl_5/6, cland reader-start kok vs u_1298..1301, u_16778, u_hr.u_18210/18231/18327).  The flow-order fix
(reserve fixed seats first) is QC-R3-TT's; this module is the static check that finds the same overlap before place.

Model (plan only; same inputs the generators emit)
  FIXED seats (rects, um, type frame)
    fixed_site  place_regions[kind=fixed].fixed_sites[].reserve_rect_um   (exact: what place_fixed_sites.tcl reserves) = THE CLASS
    core        hard_cores[] origin_um + outline_um                        (macro / core seats, placed first by the flow)
    station     ft_slots[] / internal_stations[] regs_um + bit_sites_um points, footprint DFFHQNx1 (1.08 x 0.27)
  FIRM cells (lower-left = the plan point snapped to the 0.054 x 0.27 site grid, footprint FIRM_W_UM x 0.27)
    every single-cell FIRM plan point adv_site_collide.type_items reads (landing reader / writer START stages, status stages and
    anchors, local resets, raw exports, collector sources, reset taps, reset_tree_anchor relays, relay_sites) EXCEPT the station
    registers themselves, plus the solved reset-tree relays reset_tree.for_type(T["relays"], T["relay_seats"] override), which
    rtr_place seats FIRM (the rrl:pad / rrl:tap rows of the TT evidence).
  A hit is a strictly positive rectangle overlap.  FIRM_W_UM 2.16 is the calibrated footprint: the TT evidence relay / reader
  cells reach 1.84-2.16 um (relay flop + its driver pair, or SDFF + reset gate; the reset pair allocator reserves a joint
  footprint), a bare DFFHQNx1 (1.08) misses 6 of the 12 placed hits.

Only fixed_site is the class.  core / station hits are reported as counts and a few examples for the cross-die census (design
overlaps exist there: a collector sits on its station register by design).  Fix: move the fixed seat (or the FIRM site) >= one
footprint apart in the plan, or reserve the fixed seats before reset_tree / landing placement (flow-order fix).

findings(raw, plan_path, tree=None, **kw) -> WARN lines, never raises.  kw: types= (names), solved= {type: reset tree} (callers that
hold the solve; tests), budget_s= (default 100 s of reset-tree solving), solve_all= (solve every type, not only fixed_site ones;
env OT_ADV_FIRMSEAT_SOLVE=all).  Library: overlaps(t, relays=None) -> list of hit dicts.
"""
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
CHECK = "ADV-FIRM-FIXED-SEAT"
ROW_H_UM = 0.27
SITE_W_UM = 0.054
FIRM_W_UM = 2.16              # calibrated on QC TT r3c probe2c (relay flop + driver pair, SDFF + reset gate)
DFF_W_UM = 1.08               # DFFHQNx1 (retained PDK LEF): the station register footprint
EPS = 1e-6
MAX_LINES = 25
KINDS = ("fixed_site", "core", "station")
CLASS_KIND = "fixed_site"
SEAT_KINDS_FIRM_SKIP = ("station", "station_bits")
# designed overlaps outside the class (counted, never listed): a collector local source sits ON its ft-slot station register
# (QC coll_ft*, KV kv3_pv_*), bus-bit relay_sites rows (relay_sites keyed ...[N]) are the bit registers of their station / core
BY_DESIGN = (("station", "collector"), ("station", "relay_bit"), ("core", "relay_bit"))


def _xy(p):
    try:
        if isinstance(p[0], bool) or isinstance(p[1], bool):
            return None
        return float(p[0]), float(p[1])
    except (TypeError, ValueError, IndexError, KeyError):
        return None


def _snap(x, y):
    return round(x / SITE_W_UM) * SITE_W_UM, round(y / ROW_H_UM) * ROW_H_UM


def firm_rect(x, y, w=FIRM_W_UM):
    sx, sy = _snap(x, y)
    return (sx, sy, sx + w, sy + ROW_H_UM)


def _ov(a, b):
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    return w * h if w > EPS and h > EPS else 0.0


def fixed_seats(t):
    """[(kind, name, (x0, y0, x1, y1))] of every fixed seat of one partition type."""
    out = []
    for r in t.get("place_regions") or []:
        if not isinstance(r, dict) or r.get("kind") != "fixed":
            continue
        for s in r.get("fixed_sites") or []:
            try:
                x0, y0, x1, y1 = (float(v) for v in s["reserve_rect_um"])
            except (KeyError, TypeError, ValueError):
                continue
            out.append(("fixed_site", f"{r.get('name', '?')}:{s.get('instance', '?')}", (x0, y0, x1, y1)))
    for c in t.get("hard_cores") or []:
        try:
            ox, oy = c["origin_um"]
            w, h = c["outline_um"]
            out.append(("core", str(c.get("inst", "?")), (float(ox), float(oy), float(ox) + float(w), float(oy) + float(h))))
        except (KeyError, TypeError, ValueError):
            continue
    for grp, key in (("ft_slots", "name"), ("internal_stations", "conn")):
        for s in t.get(grp) or []:
            if not isinstance(s, dict):
                continue
            pts = list(s.get("regs_um") or []) + list(s.get("bit_sites_um") or [])
            for j, p in enumerate(pts):
                q = _xy(p)
                if q:
                    sx, sy = _snap(*q)
                    out.append(("station", f"{grp}[{s.get(key)}][{j}]", (sx, sy, sx + DFF_W_UM, sy + ROW_H_UM)))
    return out


def firm_cells(t, relays=None):
    """[(kind, name, rect)] of the FIRM cells: plan points (adv_site_collide.type_items) + solved reset relays."""
    import adv_site_collide as SC
    out = []
    for kind, name, x, y in SC.type_items(t):
        if kind in SEAT_KINDS_FIRM_SKIP:
            continue
        out.append((kind, name, firm_rect(x, y)))
    for r in relays or ():
        xy = _xy(r.get("xy")) if isinstance(r, dict) else None
        if xy:
            out.append((f"rrl:{r.get('kind', '?')}{r.get('depth', '')}", str(r.get("name", "?")), firm_rect(*xy)))
    return out


def overlaps(t, relays=None):
    """[{seat_kind, seat, seat_rect, firm_kind, firm, firm_rect, area}] FIRM cell x fixed seat overlaps of one type."""
    seats = fixed_seats(t)
    if not seats:
        return []
    cells = firm_cells(t, relays)
    rows = {}
    for s in seats:
        for ry in range(int((s[2][1] - EPS) // ROW_H_UM), int((s[2][3] - EPS) // ROW_H_UM) + 1):
            rows.setdefault(ry, []).append(s)
    hits, seen = [], set()
    for fk, fn, fr in cells:
        for ry in range(int((fr[1] - EPS) // ROW_H_UM), int((fr[3] - EPS) // ROW_H_UM) + 1):
            for sk, sn, sr in rows.get(ry, ()):
                a = _ov(fr, sr)
                if a and (fn, sn) not in seen:
                    seen.add((fn, sn))
                    hits.append(dict(seat_kind=sk, seat=sn, seat_rect=sr, firm_kind=fk, firm=fn, firm_rect=fr, area=a,
                                     design=(sk, fk) in BY_DESIGN))
    hits.sort(key=lambda h: (h["seat_kind"] != CLASS_KIND, h["firm"], h["seat"]))
    return hits


def _f(v):
    return f"{v:.3f}".rstrip("0").rstrip(".")


def _rect(r):
    return "[" + ",".join(_f(v) for v in r) + "]"


def _solve(raw, plan_path, names, budget_s):
    sys.path.insert(0, str(HERE))
    import schema
    import reset_tree as RT
    P = schema.Plan(raw, Path(plan_path).parent / "die_plan.json")
    out, t0 = {}, time.time()
    for tn in names:
        if time.time() - t0 > budget_s:
            break
        try:
            T = RT.for_type(P, tn)
            seat = T.get("relay_seats") or {}
            out[tn] = [dict(r, xy=seat.get(r.get("name"), r.get("xy"))) for r in T.get("relays") or []]
        except Exception as e:  # noqa: BLE001 - a type whose tree cannot be solved is named, never clean
            out[tn] = e
    return out


def findings(raw, plan_path, tree=None, **kw):
    try:
        types = (raw or {}).get("partition_types") or {}
        want = set(kw["types"]) if kw.get("types") else None
        used = {p.get("type") for p in (raw or {}).get("partitions") or [] if isinstance(p, dict)}
        t0 = time.time()
        solve_all = kw.get("solve_all", os.environ.get("OT_ADV_FIRMSEAT_SOLVE", "") == "all")
        todo = [tn for tn, t in sorted(types.items()) if isinstance(t, dict) and not t.get("hard") is True
                and (want is None or tn in want) and (not used or tn in used)]
        with_seats = {tn for tn in todo if fixed_seats(types[tn])}
        need = [tn for tn in todo if tn in with_seats and (solve_all or any(
            s[0] == CLASS_KIND for s in fixed_seats(types[tn])))]
        solved = kw.get("solved")
        if solved is None:
            solved = _solve(raw, plan_path, need, float(kw.get("budget_s") or os.environ.get("OT_ADV_FIRMSEAT_BUDGET_S", "100"))) \
                if need else {}
        cnt = {k: [0, 0] for k in KINDS}          # kind -> [hits, types] (designed overlaps excluded)
        n_design = 0
        by_type, lines, n_err, n_skip = {}, [], 0, 0
        for tn in sorted(with_seats):
            rel = solved.get(tn)
            if isinstance(rel, Exception):
                n_err += 1
                lines.append(f"WARN {CHECK} {tn}: reset tree not solvable ({type(rel).__name__}: {str(rel)[:120]}); relays NOT checked")
                rel = None
            elif rel is None and tn in need:
                n_skip += 1
            hs = overlaps(types[tn], rel)
            if not hs:
                continue
            n_design += sum(h["design"] for h in hs)
            hs = [h for h in hs if not h["design"]]
            if not hs:
                continue
            by_type[tn] = hs
            for k in KINDS:
                n = sum(h["seat_kind"] == k for h in hs)
                if n:
                    cnt[k][0] += n
                    cnt[k][1] += 1
        listed = 0
        for tn, hs in by_type.items():
            for h in hs:
                if h["seat_kind"] != CLASS_KIND:
                    continue
                if listed < MAX_LINES:
                    lines.append(f"WARN {CHECK} {tn}: FIRM {h['firm_kind']} {h['firm']} {_rect(h['firm_rect'])} overlaps fixed seat "
                                 f"{h['seat']} {_rect(h['seat_rect'])} ({h['area']:.3f} um2); place_fixed_sites.tcl seeds after "
                                 f"reset_tree / landing placement, so the seat is overlapped; fix: move the seat or the FIRM site "
                                 f">= {FIRM_W_UM:g} um apart, or reserve fixed seats first")
                listed += 1
        for k in ("core", "station"):
            ex = [(tn, h) for tn, hs in by_type.items() for h in hs if h["seat_kind"] == k][:3]
            for tn, h in ex:
                lines.append(f"WARN {CHECK} {tn}: (context, not the class) FIRM {h['firm_kind']} {h['firm']} {_rect(h['firm_rect'])} "
                             f"overlaps {k} seat {h['seat']} {_rect(h['seat_rect'])}")
        if listed > MAX_LINES:
            lines.append(f"WARN {CHECK} ... {listed - MAX_LINES} more fixed_site overlap(s) (plan_advisory.py --checks FIRM-FIXED-SEAT for all)")
        fx = sorted(tn for tn, hs in by_type.items() if any(h["seat_kind"] == CLASS_KIND for h in hs))
        lines.append(f"WARN {CHECK} summary fixed_site {cnt['fixed_site'][0]} overlap(s) on "
                     f"{len({h['seat'] for hs in by_type.values() for h in hs if h['seat_kind'] == CLASS_KIND})} seat(s) in {cnt['fixed_site'][1]} type(s) "
                     f"({', '.join(fx[:8])}{' ...' if len(fx) > 8 else ''}); context core {cnt['core'][0]} in {cnt['core'][1]} type(s), "
                     f"station {cnt['station'][0]} in {cnt['station'][1]} type(s), {n_design} designed overlap(s) not counted; {len(with_seats)} of {len(todo)} types carry seats, "
                     f"{len(need) - n_skip - n_err} reset tree(s) solved, {n_skip} not solved (budget), {n_err} not solvable; "
                     f"{time.time() - t0:.1f} s; report-only")
        return lines
    except Exception as e:  # noqa: BLE001 an estimator never breaks the gate
        return [f"WARN {CHECK} not checked: {type(e).__name__}: {str(e)[:200]}"]


if __name__ == "__main__":
    import argparse
    import json
    sys.path.insert(0, str(HERE))
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--types")
    ap.add_argument("--all", action="store_true", help="solve every type with seats, not only fixed_site ones")
    a = ap.parse_args()
    raw = json.load(open(a.plan))
    kw = dict(types=a.types.split(",") if a.types else None, solve_all=a.all)
    for ln in findings(raw, a.plan, **kw):
        print(ln)
