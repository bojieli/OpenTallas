"""ref_site.py -- REF-SITE (TAPKEY-SITE 11-24, FABLE flow review item 3; report only): every NAME or INDEX reference of a type to a
clock tap or reset-tree node is resolved to xy on the plan's CURRENT tap grid, then
  REACH   (one plan)   a LOCAL index-keyed reset reference (collector_children / collector_local_sources / landing_local_resets) rst_n_t<i> / rr_t<i> whose node (tap i's terminal relay, i < n_taps) lies more
                       than one relay hop (REACH_UM, the bind's 405-um gate) from the consumer it serves (status_pins_xy_um /
                       pin_xy_um / xy_um of the same entry).  QC sle_sc_v3: collector_children node rst_n_t69 was the seam output
                       n_taps + 0 with 69 taps; at 73 taps index 69 is clock tap 69, 1184 um from its monitors (-241 ps), and PRE,
                       strict, LATCHECK and G0 all passed.
  MOVED   (vs baseline = the plan the references were last bound / measured on) a reference present in both plans whose resolved
                       site moved > TOL_UM (9 um): name-keyed tap tables (tap_offset / tap_window per_port_ps, tap_pin_heights_um,
                       tap_group.fixed_taps, tap_site.type_tables) and the index-keyed reset references above.
  KIND    (vs baseline) an index reference that crossed the tap count: a seam output (i >= n_taps) became a clock tap's relay or back.
Index i >= n_taps names a reset-tree OUTPUT (seam), which has no tap site: counted, not sited.  Bit sites (internal_stations
bit_sites_um) are explicit xy, checked by ADV-BITSITE-SEAT in the same PRE run.  The published collector_tree is skipped (G0
collector_reach checks its own edges).

    python3 tools/die_plan/ref_site.py PLAN [--baseline BASE] [--types a,b] [--root R] [--base-root R]
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

import tap_site as TS

TOL_UM = TS.TOL_UM
REACH_UM = 405.0
REF = re.compile(r"^(rst_n_t|rr_t)(\d+)$")
# REACH applies to references that name the node SERVING the entry locally (collector ready/fault monitors, local resets);
# transport stages (landing_*_start raw_reset, landing_raw_branches original) carry the reset away from its tap by design
LOCAL_FAMILIES = ("collector_children", "collector_local_sources", "landing_local_resets")


def _reach_um():
    try:
        import cbc_rules as C
        return float(C.REACH_GATE_UM)
    except Exception:  # noqa: BLE001
        return REACH_UM


def tap_index(name):
    if name == "clk":
        return 0
    m = re.fullmatch(r"clk_t(\d+)", str(name))
    return int(m.group(1)) if m else None


def _pts(o):
    s = o.get("status_pins_xy_um")
    if isinstance(s, list) and s and all(isinstance(p, (list, tuple)) and len(p) == 2 for p in s):
        return [tuple(map(float, p)) for p in s]
    for k in ("pin_xy_um", "xy_um"):
        p = o.get(k)
        if isinstance(p, (list, tuple)) and len(p) == 2 and all(isinstance(v, (int, float)) for v in p):
            return [(float(p[0]), float(p[1]))]
    return []


def family(path):
    for f in ("collector_children", "collector_local_sources", "landing_local_resets", "landing_raw_branches",
              "landing_reader_start", "landing_writer_start", "reset."):
        if f in path:
            return f.rstrip(".")
    return path.split(".")[1] if "." in path else path


def index_refs(t):
    """[(path, value, index, consumer pts)] of every rst_n_t<i> / rr_t<i> string of a type (collector_tree skipped); list items are
    labelled by their 'name' when they have one, so a path is the same in two plans."""
    out = []

    def walk(o, p):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "collector_tree":
                    continue
                if isinstance(v, str):
                    m = REF.match(v)
                    if m:
                        out.append((f"{p}.{k}", v, int(m.group(2)), _pts(o)))
                else:
                    walk(v, f"{p}.{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                lab = v.get("name") if isinstance(v, dict) and isinstance(v.get("name"), str) else i
                walk(v, f"{p}[{lab}]")
    walk(t, "")
    return out


def type_refs(P, raw, tn):
    """{key: (kind, value, site or None, consumer pts)}; kind tap / reset / seam.  Raises if the grid cannot be evaluated."""
    import schema as S
    grid = S.tap_grid(P, tn)
    sites = {n: (float(x), float(y)) for n, x, y in grid}
    idx = {tap_index(n): xy for n, xy in sites.items() if tap_index(n) is not None}
    n_taps = len(idx)
    refs = {}
    for label, box, key, form in TS.type_tables(raw, tn):
        ports = list(box[key].keys()) if form == "keys" else list(box[key].values())
        for q in ports:
            if TS._is_core(q):
                continue
            refs[f"{label}[{q}]"] = ("tap", q, sites.get(q), [])
    for path, v, i, pts in index_refs(raw["partition_types"][tn]):
        refs[path] = ("reset", v, idx.get(i), pts) if i < n_taps else ("seam", v, None, pts)
    return refs, n_taps


def _d(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def reach_rows(refs, reach):
    rows = []
    for k, (kind, v, site, pts) in refs.items():
        if kind == "reset" and site and pts and family(k) in LOCAL_FAMILIES:
            d = max(_d(site, p) for p in pts)
            if d > reach:
                rows.append((k, v, d))
    return rows


def moved_rows(refs, brefs, tol=TOL_UM):
    mv, kind = [], []
    for k in sorted(set(refs) & set(brefs)):
        a, b = refs[k], brefs[k]
        if (a[2] is None) != (b[2] is None) and a[0] in ("reset", "seam") and b[0] in ("reset", "seam"):
            site = a[2] or b[2]
            kind.append((k, b[1], a[1], a[0], max((_d(site, q) for q in (a[3] or b[3])), default=None)))
        elif a[2] and b[2] and _d(a[2], b[2]) > tol:
            mv.append((k, a[1], _d(a[2], b[2])))
    return mv, kind


def run(raw, plan_path, braw=None, base_path=None, types=None, log=print):
    reach = _reach_um()
    P = TS._plan(raw, plan_path)
    PB = TS._plan(braw, base_path) if braw is not None else None
    tot = Counter()
    fam_reach, fam_moved, fam_kind = Counter(), Counter(), Counter()
    lines = []
    for tn in sorted(raw.get("partition_types") or {}):
        if types and tn not in types:
            continue
        t = raw["partition_types"][tn]
        if not TS.type_tables(raw, tn) and not index_refs(t):
            continue
        try:
            TS._plandir(plan_path)
            refs, n = type_refs(P, raw, tn)
        except Exception as e:  # noqa: BLE001
            tot["unev"] += 1
            lines.append((0, f"NOT-EVALUABLE\t{tn}\t{type(e).__name__}: {str(e)[:120]}"))
            continue
        tot["types"] += 1
        tot["refs"] += len(refs)
        tot["seam"] += sum(1 for r in refs.values() if r[0] == "seam")
        rr = reach_rows(refs, reach)
        for k, _v, _d2 in rr:
            fam_reach[family(k)] += 1
        if rr:
            rr.sort(key=lambda x: -x[2])
            lines.append((len(rr), f"REACH\t{tn}\t{len(rr)} index-keyed reset refs > {reach:g} um from their consumer (n_taps {n}; worst "
                                   f"{rr[0][1]} {rr[0][2]:.0f} um at {rr[0][0]}): " + " ".join(f"{k}={v}:{d:.0f}" for k, v, d in rr[1:5])))
        if PB is None or tn not in (braw.get("partition_types") or {}):
            continue
        try:
            TS._plandir(base_path)
            brefs, bn = type_refs(PB, braw, tn)
        except Exception as e:  # noqa: BLE001
            tot["bunev"] += 1
            continue
        mv, kd = moved_rows(refs, brefs)
        tot["common"] += len(set(refs) & set(brefs))
        for k, *_ in mv:
            fam_moved[family(k) if not k.startswith("clock.") and not k.startswith("tap_") else k.split("[")[0]] += 1
        for k, *_ in kd:
            fam_kind[family(k)] += 1
        if mv or kd:
            mv.sort(key=lambda x: -x[2])
            lines.append((len(mv) + len(kd), f"MOVED\t{tn}\t{len(mv)} refs on a site moved > {TOL_UM:g} um, {len(kd)} index refs crossed the tap count "
                                             f"(n_taps {bn} -> {n})" + (f"; worst {mv[0][1]} {mv[0][2]:.0f} um at {mv[0][0]}" if mv else "")
                                             + (f"; KIND worst consumer distance {max(x[4] for x in kd if x[4] is not None):.0f} um" if any(x[4] is not None for x in kd) else "")
                                             + "".join(f"; KIND {k}: {a}->{b} now {c}" + (f" {d:.0f} um from consumer" if d is not None else "")
                                                       for k, a, b, c, d in sorted(kd, key=lambda x: -(x[4] or 0))[:3])))
    lines.sort(key=lambda x: -x[0])
    for _n, ln in lines:
        log(ln)
    log(f"SUMMARY\t{tot['types']} types, {tot['refs']} name/index refs resolved ({tot['seam']} seam-output indices, unsited), {tot['unev']} not evaluable; "
        f"REACH {sum(fam_reach.values())} {dict(fam_reach)}"
        + (f"; vs baseline: {tot['common']} common refs, MOVED {sum(fam_moved.values())} {dict(fam_moved)}, KIND {sum(fam_kind.values())} {dict(fam_kind)}, "
           f"{tot['bunev']} baseline types not evaluable" if PB is not None else "; no baseline: MOVED/KIND not run"))
    return dict(tot=tot, reach=fam_reach, moved=fam_moved, kind=fam_kind)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan")
    ap.add_argument("--baseline")
    ap.add_argument("--types", default="")
    ap.add_argument("--root")
    ap.add_argument("--base-root")
    a = ap.parse_args(argv)
    raw = json.loads(Path(a.plan).read_text())
    braw = json.loads(Path(a.baseline).read_text()) if a.baseline else None
    if a.root:
        TS.ROOTS[str(a.plan)] = a.root
    if a.base_root and a.baseline:
        TS.ROOTS[str(a.baseline)] = a.base_root
    run(raw, a.plan, braw, a.baseline, [t for t in a.types.split(",") if t] or None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
