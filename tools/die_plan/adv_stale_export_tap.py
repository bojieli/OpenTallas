"""adv_stale_export_tap.py -- PRECHECK ADV-STALE-EXPORT-TAP (class C-FWDCLK-WRONG-TAP; report only; R3-STALETAP 11-27).

A forwarded-clock output (clock.landing_contract pin kind clock, dir out) names the tap that sources it (source_clock_port).  The name is
chosen at first landing compose; when the tap grid is regrown / renumbered (density re-solve) the pin keeps its old tap and the export
buffer chain runs from a tap far away (KV A5: 1463 of 2601 pins > 300 um; v6ne 11-26: 48 of 69 exports from clk_t82, 1.8 mm), so the
fclk-vs-data margin at the port is not what the plan assumed.  FABLE-RC-KV 11-27: 'STALE-EXPORT-TAP still not implemented' (static count
1 vs 21 types / 435 aliases): the ENTRYFOOT line in derived_drop prints it only on a PRE that reaches ENTRYFOOT with a tap grid; this
advisory is the standalone, per-type, budgeted reader with counts per die and placed-instance weight.

Per type with export pins (tap grid = schema.tap_grid, the grid the kit gets; plan-relative sink_bins read from the plan's folder):
  STALE    source tap exists, Manhattan hop source-tap -> pin > LIMIT_UM (300) and a strictly nearer tap exists   (re-point fixes it)
  DANGLING source tap no longer in the grid
  NOFIX    over the limit and the source already is the nearest tap                                               (add a tap / move the pin)
Lines: one per type (worst first, MAX_LINES), a per-type LIST of ALL hit types in the summary, die totals in pins, types, placed
instances (partition uses).  Never blocking: the two-sided what-if (KV-SENDER-SKEW 11-24: a blind repoint trades hold for setup) is
NOT judged here, it is the class's counting check only.  OT_ADV_STALE_TAP_LIMIT_UM, OT_ADV_STALE_TAP_BUDGET_S (default 100; 0 = no
budget; types past it are counted as not checked).  findings(raw, plan_path, tree=None, **kw) -> WARN lines, never raises.
"""
import os
import sys
import time
from pathlib import Path

CHECK = "ADV-STALE-EXPORT-TAP"
CLASS_ID = "C-FWDCLK-WRONG-TAP"
LIMIT_UM = 300.0
EPS = 0.5
MAX_LINES = 25


def _w(*p):
    return " ".join(["WARN", CHECK] + [str(x) for x in p])


def man(a, b):
    return abs(float(a[0]) - float(b[0])) + abs(float(a[1]) - float(b[1]))


def export_pins(t):
    lc = ((t or {}).get("clock") or {}).get("landing_contract") or {}
    return [q for q in lc.get("pins") or [] if isinstance(q, dict) and q.get("kind") == "clock" and q.get("dir") == "out"
            and q.get("source_clock_port") is not None and q.get("xy_um")]


def classify(pins, grid, limit=LIMIT_UM):
    """pure: -> dict(stale=[(h0, name, src, near, h1)], dangling=[(name, src, near, h1)], nofix=[(h0, name, src, near, h1)], n=len(pins))
    grid = {tap: (x, y)}; the grid origin 'clk' counts only when it is the only tap (as derived_drop)."""
    taps = [n for n in grid if n != "clk"] or list(grid)
    out = dict(stale=[], dangling=[], nofix=[], n=len(pins))
    for q in pins:
        s, xy, name = q["source_clock_port"], q["xy_um"], q.get("name")
        near = min(taps, key=lambda n: (man(grid[n], xy), n)) if taps else None
        h1 = man(grid[near], xy) if near else float("inf")
        if s not in grid:
            out["dangling"].append((name, s, near, h1))
            continue
        h0 = man(grid[s], xy)
        if h0 <= limit + EPS:
            continue
        (out["stale"] if h1 < h0 - EPS else out["nofix"]).append((h0, name, s, near, h1))
    return out


def _fmt(tn, c, uses, limit):
    st, dg, nf = sorted(c["stale"], reverse=True), c["dangling"], sorted(c["nofix"], reverse=True)
    parts = [f"{len(st)} stale"]
    if dg:
        parts.append(f"{len(dg)} dangling")
    if nf:
        parts.append(f"{len(nf)} no-nearer-tap")
    ex = [f"{n} <- {s} {h0:.0f} um (nearest {nr} {h1:.0f})" for h0, n, s, nr, h1 in (st or nf)[:2]]
    ex += [f"{n} <- {s} gone (nearest {nr} {h1:.0f})" for n, s, nr, h1 in dg[:1]]
    worst = max([x[0] for x in st + nf] or [0.0])
    return (f"{tn}: {len(st) + len(dg) + len(nf)} of {c['n']} forwarded-clock exports over {limit:g} um from their source tap "
            f"({', '.join(parts)}; worst {worst:.0f} um; x{uses} placed): " + "; ".join(ex))


def _findings(raw, plan_path, tree=None, **kw):
    limit = float(kw.get("limit") or os.environ.get("OT_ADV_STALE_TAP_LIMIT_UM", LIMIT_UM))
    budget = float(os.environ.get("OT_ADV_STALE_TAP_BUDGET_S", "100"))
    here = (Path(tree) / "tools" / "die_plan") if tree and (Path(tree) / "tools" / "die_plan" / "schema.py").is_file() else Path(__file__).resolve().parent
    sys.path.insert(0, str(here))
    import schema as S
    try:
        import taps as _T
        _T.PLAN_DIR = os.environ.get("OT_ADV_PLANDIR") or str(Path(plan_path).resolve().parent)
    except Exception:  # noqa: BLE001
        pass
    P = S.Plan(raw, Path(plan_path))
    types = (raw or {}).get("partition_types") or {}
    uses = {}
    for p in (raw or {}).get("partitions") or []:
        if isinstance(p, dict) and p.get("type"):
            uses[p["type"]] = uses.get(p["type"], 0) + 1
    t0, hit, errs, left, tot = time.time(), [], [], [], dict(types=0, pins=0, ipins=0)
    cnt = dict(over=0, iover=0, stale=0, dang=0, nofix=0)
    for tn, t in sorted(types.items()):
        if not isinstance(t, dict) or not export_pins(t):
            continue
        if budget > 0 and time.time() - t0 > budget:
            left.append(tn)
            continue
        pins, k = export_pins(t), uses.get(tn, 1)
        try:
            c = classify(pins, {n: (x, y) for n, x, y in S.tap_grid(P, tn)}, limit)
        except Exception as e:  # noqa: BLE001
            errs.append(f"{tn} ({type(e).__name__}: {str(e)[:80]})")
            continue
        tot["types"] += 1
        tot["pins"] += c["n"]
        tot["ipins"] += c["n"] * k
        n = len(c["stale"]) + len(c["dangling"]) + len(c["nofix"])
        if n:
            hit.append((max([x[0] for x in c["stale"] + c["nofix"]] or [0.0]), tn, c, k))
            cnt["over"] += n
            cnt["iover"] += n * k
            cnt["stale"] += len(c["stale"])
            cnt["dang"] += len(c["dangling"])
            cnt["nofix"] += len(c["nofix"])
    hit.sort(key=lambda x: (-x[0], x[1]))
    out = [_w(_fmt(tn, c, k, limit)) for _w_, tn, c, k in hit[:MAX_LINES]]
    if len(hit) > MAX_LINES:
        out.append(_w(f"{len(hit) - MAX_LINES} more type(s): " + ", ".join(tn for _x, tn, _c, _k in hit[MAX_LINES:][:40])))
    if errs:
        out.append(_w("not checked", f"{len(errs)} type(s): " + "; ".join(errs[:4])))
    if left:
        out.append(_w("not checked", f"{len(left)} type(s) past the {budget:.0f} s budget (OT_ADV_STALE_TAP_BUDGET_S): " + ", ".join(left[:6])))
    out.append(_w("summary", f"class {CLASS_ID}: {len(hit)} of {tot['types']} export types hit; {cnt['over']} of {tot['pins']} forwarded-clock "
                             f"export pins over {limit:g} um from their source tap ({cnt['stale']} stale, {cnt['dang']} dangling, "
                             f"{cnt['nofix']} no-nearer-tap); {cnt['iover']} of {tot['ipins']} per placed instance; report only, "
                             f"re-point is two-sided (KV-SENDER-SKEW: hold vs setup), fix via fwdclk_repoint.py"))
    return out


def findings(raw, plan_path, tree=None, **kw):
    try:
        return _findings(raw, plan_path, tree, **kw)
    except Exception as e:  # noqa: BLE001
        return [_w("not checked", f"{type(e).__name__}: {str(e)[:200]}")]


if __name__ == "__main__":
    import json
    for ln in findings(json.load(open(sys.argv[1])), sys.argv[1], sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] else None):
        print(ln)
