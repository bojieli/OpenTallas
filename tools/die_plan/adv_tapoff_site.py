"""adv_tapoff_site.py -- PRECHECK ADV-TAPOFF-SITE (COORD 11-24; report only).

clock.tap_offset.per_port_ps rows are keyed by tap NAME.  The tap grid renumbers clk_t<i> whenever macros / cores / bands move (density
re-solve), so a row measured on tap clk_t57 at one site silently times a DIFFERENT tap after the move; tap_offset_cover census still says
PASS (every name has a row).  QC-OPEN-STA 11-24: st_a r9 kept only 5-22 of 225-408 rows on their own tap, the rest sat on a tap up to
1490 um away.

A row carries no site, so the reference is a BASELINE plan (the plan the offsets were measured / last verified against: --baseline,
kw baseline=): for every type present in both, each row port's site in the baseline tap grid (schema.tap_grid via
tap_offset_cover.type_ports, the same ports the kit gets) is compared with the same port's site in this plan.
  MOVED  site differs by more than TOL_UM (9 um)      -> the row now describes another place (the mismatch)
  SAME   within TOL_UM
  NEW    port exists here only (no baseline site; tap_offset_cover census covers whether it has a row)
  GONE   row port with no tap in the current grid     (tap_offset_cover stale)
Per type: rows, MOVED count, worst move um.  Without a baseline nothing can be judged: one NOT-RUN line.  Both table forms are checked (offsets, and window rows of types without an offsets row: S81).  Core taps (clk_c*) are
skipped (measured rows of their own).  findings(raw, plan_path, tree=None, **kw) -> WARN lines, never raises.
"""
import json
import os
import sys
from pathlib import Path

CHECK = "ADV-TAPOFF-SITE"
TOL_UM = 9.0
MAX_LINES = 25


def _w(*p):
    return " ".join(["WARN", CHECK] + [str(x) for x in p])


def compare(rows, cur, base, tol=TOL_UM):
    """rows: iterable of port names; cur/base: {port: (x, y)} -> (moved [(port, dist)], same, new, gone)"""
    moved, same, new, gone = [], 0, 0, 0
    for p in rows:
        if p not in cur:
            gone += 1
            continue
        if p not in base:
            new += 1
            continue
        d = abs(cur[p][0] - base[p][0]) + abs(cur[p][1] - base[p][1])
        if d > tol:
            moved.append((p, d))
        else:
            same += 1
    return moved, same, new, gone


def _findings(raw, plan_path, tree=None, **kw):
    base = kw.get("baseline")
    if not base:
        return [_w("NOT-RUN: no baseline plan given (the reference where the rows' taps had their sites); pass --baseline-plan / baseline=")]
    here = (Path(tree) / "tools" / "die_plan") if tree and (Path(tree) / "tools" / "die_plan" / "schema.py").is_file() else Path(__file__).resolve().parent
    sys.path.insert(0, str(here))
    for fb in (Path(__file__).resolve().parent, Path(os.environ.get("OT_RT_DIE_PLAN", "/srv/opentallas-scratch2/claude/rt/current/tools/die_plan"))):
        if (fb / "tap_offset_cover.py").is_file() and str(fb) not in sys.path:
            sys.path.append(str(fb))                  # schema comes from the TREE (its resources), the cover helper from main when the tree lacks it
    import schema as S
    import tap_offset_cover as TC
    try:                                              # plan-relative inputs (sink_bins/): the plan's own folder, as bind.py sets it (KW-FIX-45)
        import taps as _T
        _T.PLAN_DIR = os.environ.get("OT_ADV_PLANDIR") or str(Path(plan_path).resolve().parent)
    except Exception:  # noqa: BLE001
        pass
    braw = base if isinstance(base, dict) else json.loads(Path(base).read_text())
    P = S.Plan(raw, Path(plan_path))
    PB = S.Plan(braw, Path(base) if not isinstance(base, dict) else Path(plan_path))
    off = {tn: row for _fm, tn, row in TC.tables(raw)}          # offsets rows, then window rows of types with no offsets row (TAPWIN)
    boff = {tn: row for _fm, tn, row in TC.tables(braw)}
    out, nt, nbad, tot_moved, tot_rows, unev, ew = [], 0, 0, 0, 0, 0, ''
    for tn in sorted(off):
        if tn not in (raw.get("partition_types") or {}) or tn not in (braw.get("partition_types") or {}):
            continue
        cur, core, why = TC.type_ports(P, raw, tn)
        b, bcore, bwhy = TC.type_ports(PB, braw, tn)
        if why or bwhy:
            unev += 1
            ew = ew or (why or bwhy)
            continue
        rows = [p for p in off[tn] if p not in core]
        moved, same, new, gone = compare(rows, cur, b)
        nt += 1
        tot_rows += len(rows)
        if moved:
            nbad += 1
            tot_moved += len(moved)
            moved.sort(key=lambda x: -x[1])
            same_rows_as_base = sum(1 for p in rows if off[tn].get(p) == (boff.get(tn) or {}).get(p))
            out.append((len(moved), _w(f"{tn}: {len(moved)} of {len(rows)} offset rows now sit on a tap that moved > {TOL_UM:g} um vs the baseline "
                                       f"({same} kept their site, {new} new, {gone} gone; worst {moved[0][1]:.0f} um at {moved[0][0]}; "
                                       f"{same_rows_as_base} rows unchanged from the baseline table): the name-keyed row times another place; "
                                       f"fix: re-key the rows by site (QC-OPEN-STA r10 recipe) then tap_offset_cover fill")))
    out.sort(key=lambda x: -x[0])
    lines = [m for _, m in out[:MAX_LINES]]
    lines.append(_w("summary", f"{nbad} of {nt} types with an offsets table have rows on moved taps ({tot_moved} of {tot_rows} rows, tol {TOL_UM:g} um vs baseline); "
                               f"{unev} types not evaluable (tap solver raised: {ew[:110]}); the coverage census cannot see this (it is name-based)"))
    return lines


def findings(raw, plan_path, tree=None, **kw):
    try:
        return _findings(raw, plan_path, tree, **kw)
    except Exception as e:  # noqa: BLE001
        return [_w("not checked", f"{type(e).__name__}: {str(e)[:200]}")]


if __name__ == "__main__":
    for ln in findings(json.load(open(sys.argv[1])), sys.argv[1], sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] else None,
                       baseline=sys.argv[3] if len(sys.argv) > 3 else None):
        print(ln)
