#!/usr/bin/env python3
"""stale_tables.py -- PRE class STALETABLE (class P-STALE-TABLE, QC-INT-R2-TOOLS 11-26, COORD FABLE-FLOW-0847 item 11).  ADVISORY (WARN) on
existing plans; $OT_PRE_STALETABLE_BLOCK=1 makes the lines FAIL.

Class: a plan row edit moves a station / tap / macro and a DEPENDENT table is not re-derived.  Static equality checks ("table == re-derived"):
  TAPTABLE   clock.tap_window.per_port_ps / clock.tap_offset.per_port_ps keys must equal the type's tap ports (tap grid + core taps):
             missing ports (QC cA4 lists 9 of 20) and stale ports (name no longer a tap).  Overlaps TAPOFF-MISSING (FAIL, missing only);
             this adds the stale keys and the census per die.
  ORGROUP    internal_stations entry with or_groups: or_groups[0].regs_um must equal the row's regs_um (QC coll_core 624.645 vs 626.454;
             kit_istations.or_group_check refuses it late).  Repair: python3 -I tools/die_plan/stale_tables.py fix-orgroups IN OUT.
  TAPLEGAL   (C-MACRO-TAP-LEGAL) every clock tap the kit gets (tap grid, explicit, added) re-judged against the current macros / halos / outline
             (Coll_s clk_t41 [512.992, 415.776] on the old C9 placement; legal at [504.288, 424.48] after badd78bdf36b) or a
             tap grid the solver cannot evaluate (reason listed).
  RELAYBIT   relay_sites of a station bank (u_ist_<bus>_<j>.q[k]) must sit within TOL_UM of internal_stations bit_sites_um[j][k]
             (QC D2: differ up to 302 um).
Row apply: ORGROUP is re-derived automatically by fix_orgroups (call it at the end of a row; it is the only table here with one
source of truth, the row's regs_um).  The other forms are flagged; their tables come from a solver (tap_offset_cover.py fill, tap
generator) not from the row.
    python3 -I tools/die_plan/stale_tables.py census PLAN | fix-orgroups IN OUT
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))  # -I drops the script dir
TOL_UM = 2.0
LEVEL_ENV = "OT_PRE_STALETABLE_BLOCK"
FORMS = ("TAPTABLE", "ORGROUP", "TAPLEGAL", "RELAYBIT")


def level():
    return "FAIL" if os.environ.get(LEVEL_ENV) == "1" else "WARN"


def _fl(p):
    return [float(v) for v in p]


def tap_table(raw, tn, grid, core):
    """-> [(form, missing [..], stale [..], rows, ports)] for each of the type's window / offsets tables (both are judged: the offsets row wins
    in gen_phys, but a stale window row misleads the next regeneration; cA4: window 9 of 20 ports); grid = grid tap port names, core = core tap names (never required, never stale)"""
    ck = raw.get("clock") or {}
    off = ((ck.get("tap_offset") or {}).get("per_port_ps") or {}).get(tn)
    win = ((ck.get("tap_window") or {}).get("per_port_ps") or {}).get(tn)
    out = []
    for key, tab in (("tap_offset", off), ("tap_window", win)):
        if not tab:
            continue
        miss = sorted(p for p in grid if p not in tab)
        stale = sorted(p for p in tab if p not in grid and p not in core)
        if miss or stale:
            out.append((key, miss, stale, len(tab), len(grid)))
    return out


def or_group_rows(t):
    """[(entry index, conn, group0 regs, row regs)] internal_stations whose or_groups[0].regs_um != regs_um"""
    out = []
    for i, e in enumerate(t.get("internal_stations") or []):
        og = e.get("or_groups") if isinstance(e, dict) else None
        if not og or not isinstance(og, list) or not isinstance(og[0], dict) or "regs_um" not in og[0]:
            continue
        try:
            a, b = [_fl(p) for p in og[0]["regs_um"]], [_fl(p) for p in e.get("regs_um") or []]
        except (TypeError, ValueError):
            continue
        if a != b:
            out.append((i, e.get("conn"), a, b))
    return out


def fix_orgroups(raw):
    """re-derive or_groups[0].regs_um from the row's regs_um in place; -> number of entries rewritten"""
    n = 0
    for t in (raw.get("partition_types") or {}).values():
        for i, _c, _a, b in or_group_rows(t):
            t["internal_stations"][i]["or_groups"][0]["regs_um"] = [list(p) for p in t["internal_stations"][i]["regs_um"]]
            n += 1
    return n


def relay_bit_rows(t, tol=TOL_UM):
    """[(relay key, relay xy, bit site xy, distance)] relay_sites of u_ist_<bus>_<j>.q[k] vs internal_stations bit_sites_um[j][k]"""
    rs = t.get("relay_sites") or {}
    if not rs:
        return []
    out = []
    for e in t.get("internal_stations") or []:
        if not isinstance(e, dict) or not e.get("bit_sites_um") or not str(e.get("conn", "")).startswith("bus:"):
            continue
        bus = str(e["conn"])[4:]
        banks = e["bit_sites_um"]
        for j, bank in enumerate(banks if isinstance(banks[0], list) and banks and isinstance(banks[0][0], list) else []):
            for k, site in enumerate(bank):
                key = f"u_ist_{bus}_{j}.q[{k}]"
                v = rs.get(key)
                if v is None or len(site) < 2:
                    continue
                d = abs(v[0] - site[0]) + abs(v[1] - site[1])
                if d > tol:
                    out.append((key, (v[0], v[1]), (site[0], site[1]), round(d, 1)))
    return out


def findings(raw, tap_sites=None, legal=None, max_list=3):
    """PRE lines; tap_sites {type: (sites, core, why)}; legal(tn, x, y, name) -> bool or None"""
    lv = level()
    out = []
    cnt = dict.fromkeys(FORMS, 0)
    for tn, t in sorted((raw.get("partition_types") or {}).items()):
        if not isinstance(t, dict):
            continue
        if tap_sites and tn in tap_sites:
            sites, core, why = tap_sites[tn]
            grid = set(sites) if isinstance(sites, dict) else {s[0] for s in sites}
            if why and why.startswith("FileNotFoundError"):
                out.append(f"WARN STALETABLE-UNCHECKED {tn}: tap grid inputs missing ({why[-120:]}); table / legality not judged")
            elif why:
                cnt["TAPLEGAL"] += 1
                out.append(f"{lv} STALETABLE-TAPLEGAL {tn}: tap grid not solvable: {why[:200]}")
            else:
                for key, miss, stale, n_tab, n_ports in tap_table(raw, tn, grid, set(core)):
                    cnt["TAPTABLE"] += 1
                    out.append(f"{lv} STALETABLE-TAPTABLE {tn}: clock.{key}.per_port_ps lists {n_tab} of the type's {n_ports} tap ports: "
                               f"{len(miss)} missing ({','.join(miss[:max_list])}), {len(stale)} stale ({','.join(stale[:max_list])}) "
                               "(fix: tap_offset_cover.py fill)")
        for i, conn, a, b in or_group_rows(t):
            cnt["ORGROUP"] += 1
            d = next((p for p, q in zip(a, b) if p != q), a[0])
            out.append(f"{lv} STALETABLE-ORGROUP {tn} {conn}: or_groups[0].regs_um != the row's regs_um (first differing {d} vs "
                       f"{next((q for p, q in zip(a, b) if p != q), b[0])}); the kit refuses it (fix: stale_tables.py fix-orgroups)")
        if legal is not None and not t.get("hard"):        # a hard IP wrapper's tap IS the macro's clock terminal
            ck = t.get("clock") or {}
            pts = {}
            if tap_sites and tn in tap_sites and not tap_sites[tn][2] and isinstance(tap_sites[tn][0], dict):
                pts.update({n: list(xy) for n, xy in tap_sites[tn][0].items() if not str(n).startswith("clk_c")})   # every tap the kit gets
            for p in (ck.get("added_taps") or []) + (ck.get("taps") if ck.get("tap_mode") == "explicit" else []):
                if isinstance(p, dict) and p.get("kind") != "core" and isinstance(p.get("xy"), list) and len(p["xy"]) == 2:
                    pts[p.get("name")] = p["xy"]
            bad = []
            for name, xy in pts.items():
                try:
                    ok = legal(tn, float(xy[0]), float(xy[1]), name)
                except Exception:  # noqa: BLE001
                    ok = None
                if ok is False:
                    bad.append((name, [round(float(xy[0]), 3), round(float(xy[1]), 3)]))
            if bad:
                cnt["TAPLEGAL"] += 1
                out.append(f"{lv} STALETABLE-TAPLEGAL {tn}: {len(bad)} clock tap(s) overlap a macro / its halo or leave the outline (C-MACRO-TAP-LEGAL): "
                           + ", ".join(f"{n}={xy}" for n, xy in bad[:max_list]) + " (re-seat the tap; re-run after every macro move / row apply)")
        rb = relay_bit_rows(t)
        if rb:
            cnt["RELAYBIT"] += 1
            w = max(rb, key=lambda r: r[3])
            out.append(f"{lv} STALETABLE-RELAYBIT {tn}: {len(rb)} relay_sites seat(s) differ from the station bit_sites_um by over {TOL_UM:g} um, "
                       f"worst {w[3]:g} um ({w[0]} at {w[1]} vs {w[2]})")
    d = raw.get("die")
    d = d.get("name") if isinstance(d, dict) else d
    out.append(f"LIST STALETABLE die {d} " + " ".join(f"{k} {v}" for k, v in cnt.items())
               + ("" if lv == "FAIL" else f" (advisory; ${LEVEL_ENV}=1 makes them FAIL)"))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("census")
    c.add_argument("plan")
    c.add_argument("--no-taps", action="store_true", help="skip the tap solver (TAPTABLE / TAPLEGAL tap forms)")
    f = sub.add_parser("fix-orgroups")
    f.add_argument("inp")
    f.add_argument("out")
    a = ap.parse_args(argv)
    if a.cmd == "fix-orgroups":
        raw = json.loads(Path(a.inp).read_text())
        n = fix_orgroups(raw)
        Path(a.out).write_text(json.dumps(raw, indent=1))
        print(f"fix-orgroups: {n} entr(ies) re-derived")
        return 0
    raw = json.loads(Path(a.plan).read_text())
    ts = legal = None
    if not a.no_taps:
        import tap_reach as TR
        ts = TR.solve_tap_sites(raw, a.plan)
        legal = make_legal(raw, a.plan)
    for line in findings(raw, ts, legal):
        print(line)
    return 0


def tap_legal_in(outline, clear, boxes, x, y):
    """C-MACRO-TAP-LEGAL: a clock tap at (x, y) must lie inside the outline (tap clearance) and in no interior of a macro / obstacle box
    already grown by the tap clearance (placement_obstacles.placement_boxes(halo=clear), keepouts); boundary contact is legal"""
    w, h = outline
    eps = 1e-8
    return (clear - eps <= x <= w - clear + eps and clear - eps <= y <= h - clear + eps
            and not any(a + eps < x < c - eps and b + eps < y < d - eps for a, b, c, d in boxes))


def make_legal(raw, plan_path):
    """legal(tn, x, y, name): the tap lies inside the outline (tap clearance) and in no macro / obstacle halo interior
    (placement_obstacles.placement_boxes, as taps.grid_explicit_sites / added_tap_recentre.legal judge it); None when the tools do not import"""
    try:
        import schema as S
        from placement_obstacles import placement_boxes
        P = S.Plan(raw, Path(plan_path))
    except Exception:  # noqa: BLE001
        return None
    cache = {}

    def legal(tn, x, y, name):
        if tn not in cache:
            t = P.types[tn]
            clear = S.type_tap_clear(t) if hasattr(S, "type_tap_clear") else S.TAP_CLEAR_UM
            boxes = list(placement_boxes(t, halo=clear).values())
            boxes += [(a - clear, b - clear, c + clear, d + clear) for a, b, c, d in (t.get("clock") or {}).get("keepouts_um", [])]
            cache[tn] = (t["outline_um"], clear, boxes)
        outline, clear, boxes = cache[tn]
        return tap_legal_in(outline, clear, boxes, x, y)
    return legal


if __name__ == "__main__":
    sys.exit(main())
