#!/usr/bin/env python3
"""adv_insertion_band.py -- static estimator ADV-INSERTION-BAND (FP-CONVERGE-QC C2, 11-25).  REPORT-ONLY, never a gate.

The flow reads the pin-register TT/FF insertion mean in tools/die_plan/postcts_gate.tcl: dev = |mean - bound| against
tol (OT_POSTCTS_TOL, default 20 ps; the plan's clock.insertion_tol_ps, 40 ps, is the per-tap band); a miss with
SETUP_TRIAGE stops the row.  The mean moves with the tap-to-sink leg of each tap region, because tap_balance pulls every
fast tap to ~target + 17 ps and leaves a slow tap at its latest sink + 29 ps (adv_tap_budget.py model, 40.8 + 0.6845 *
dmax + 6.23 log2 n).  So a type's insertion band = spread of that arrival over its tap regions (taps with >= 20 sinks).

Per type (density / explicit): taps = plan clock.taps without kind (taps solve through schema when importable, else the
table + added_taps) ; sinks = clock.sink_bins_file bins; each bin goes to its nearest tap (Manhattan).  A leg whose
straight L-route (both orders) crosses a hard-core box (+halo) pays a detour (min(w,h) + 2 halo: the macro-face stair).
Region verdicts:
  LEG   a region whose farthest leg (incl. detour) exceeds the hop budget REACH_UM (405 um) or leaves the target
  SLOW  a region whose natural latest-sink arrival (+29) exceeds clock.tap_slowest_max_ps (else target + 15): tap_balance
        cannot pull it into the band, so the pin-register mean and band widen
  BAND  est arrival spread over regions (max - min) > band tol (clock.insertion_tol_ps, 40 ps)
  DEV   sink-weighted mean arrival minus (target + FLOOR 20 = tol) above target + tol  (est mean over the gate bound)

    findings(raw, plan_path, tree=None, types=None, **kw) -> [str]
    adv_insertion_band.py PLAN [--types a,b] [--tree DIR] [--json OUT]
"""
import json
import math
import os
import re
import sys
from pathlib import Path

CHECK = "ADV-INSERTION-BAND"
REACH_UM = 405.0
A_PS, B_PS_PER_UM, C_PS_PER_LOG2 = 40.8, 0.6845, 6.23     # adv_tap_budget.py
SLOW_OVER_PS, BALANCE_OVER_PS = 29.0, 17.0
GATE_TOL_PS = float(os.environ.get("OT_POSTCTS_TOL", "20"))
N_MIN = 20
MAX_LINES = 25
DEFAULT_TREES = ("/srv/opentallas-scratch2/claude/QC-C1O-COMPOSE/launch_c1o_bind",
                 "/srv/opentallas-scratch2/claude/QC-SINKBINS/tree",
                 "/srv/opentallas-scratch3/claude/kw45/snap_qwen_compute/qwen_compute_v4c4_postbind_1123203737",
                 "/home/ubuntu/scratch-root/claude/kw45/snap_qwen_compute/qwen_compute_v4c4_postbind_1123203737")
SUFFIX = re.compile(r"(?:__(?:cl|pv)[0-9a-f]{6,})+$")


def est_natural(dmax, n):
    return A_PS + B_PS_PER_UM * dmax + C_PS_PER_LOG2 * math.log2(max(2.0, n))


def est_arrival(dmax, n, target):
    """post-balance pin-register arrival of a tap region (ps)"""
    return max(target + BALANCE_OVER_PS, est_natural(dmax, n) + SLOW_OVER_PS)


def _seg_hits(box, p, q):
    """axis-aligned segment p-q crosses the open box (x0,y0,x1,y1)"""
    x0, y0, x1, y1 = box
    ax, bx = sorted((p[0], q[0]))
    ay, by = sorted((p[1], q[1]))
    return ax < x1 and bx > x0 and ay < y1 and by > y0


def leg_um(tap, pt, boxes):
    """Manhattan leg tap -> sink, plus a detour when both L-routes cross a hard-core box"""
    d = abs(tap[0] - pt[0]) + abs(tap[1] - pt[1])
    if not boxes:
        return d
    c1, c2 = (pt[0], tap[1]), (tap[0], pt[1])
    blk = [b for b in boxes if (_seg_hits(b[:4], tap, c1) or _seg_hits(b[:4], c1, pt))
           and (_seg_hits(b[:4], tap, c2) or _seg_hits(b[:4], c2, pt))
           and not (b[0] < pt[0] < b[2] and b[1] < pt[1] < b[3])]
    if not blk:
        return d
    return d + max(min(b[2] - b[0], b[3] - b[1]) + 2 * b[4] for b in blk)


def regions(taps, bins, boxes):
    """taps [(name,x,y)], bins [(x,y,n)] -> {name: dict(n, dmax, over)}; nearest tap, detour-aware leg"""
    out = {nm: dict(n=0.0, dmax=0.0, over=0.0) for nm, _, _ in taps}
    for x, y, n in bins:
        best = min(taps, key=lambda t: abs(t[1] - x) + abs(t[2] - y))
        d = leg_um((best[1], best[2]), (x, y), boxes)
        r = out[best[0]]
        r["n"] += n
        r["dmax"] = max(r["dmax"], d)
        if d > REACH_UM:
            r["over"] += n
    return out


def judge(taps, bins, boxes, target, band_tol, slowmax=None):
    """-> (verdict list, rows).  rows: per region with n >= N_MIN"""
    reg = regions(taps, bins, boxes)
    rows = [dict(tap=k, n=v["n"], dmax=v["dmax"], over=v["over"], arr=est_arrival(v["dmax"], v["n"], target),
                 slow=est_natural(v["dmax"], v["n"]) + SLOW_OVER_PS)
            for k, v in reg.items() if v["n"] >= N_MIN]
    bad = []
    if not rows:
        return bad, rows
    for r in rows:
        if r["dmax"] > REACH_UM:
            bad.append(("LEG", r))
    cap = slowmax if slowmax is not None else target + 15.0
    sl = [r for r in rows if r["slow"] > cap]
    if sl:
        w = max(sl, key=lambda r: r["slow"])
        bad.append(("SLOW", dict(tap=w["tap"], slow=w["slow"], cap=cap, k=len(sl), dmax=w["dmax"], n=w["n"])))
    arr = [r["arr"] for r in rows]
    spread = max(arr) - min(arr)
    if spread > band_tol:
        bad.append(("BAND", dict(spread=spread, lo=min(arr), hi=max(arr))))
    tot = sum(r["n"] for r in rows)
    mean = sum(r["arr"] * r["n"] for r in rows) / tot
    if mean > target + BALANCE_OVER_PS + GATE_TOL_PS:
        bad.append(("DEV", dict(mean=mean, limit=target + BALANCE_OVER_PS + GATE_TOL_PS)))
    return bad, rows


def _boxes(t):
    out = []
    for h in t.get("hard_cores") or []:
        x, y = h["origin_um"]
        w, hh = h["outline_um"]
        if h.get("orient") in ("R90", "R270", "MXR90", "MYR90"):
            w, hh = hh, w
        out.append((x, y, x + w, y + hh, float(h.get("halo_um", 0.0) or 0.0)))
    return out


def _tap_list(raw, plan_path, tn, t, P, cache=None):
    ck = t["clock"]
    added = [(p["name"], float(p["xy"][0]), float(p["xy"][1])) for p in ck.get("added_taps") or [] if p.get("xy")]
    tab = [(p["name"], float(p["xy"][0]), float(p["xy"][1])) for p in ck.get("taps") or [] if not p.get("kind") and p.get("xy")]
    mode = ck.get("tap_mode", "grid")
    if cache and tn in cache:
        return [(n, float(x), float(y)) for n, x, y in cache[tn]] + added, "density taps cache"
    if mode == "density" and P is not None:
        try:
            import contextlib
            import io
            import taps as TP
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                base = TP._density_base(P, tn)
            return [(n, x, y) for n, x, y, *_ in base] + added, "density solve"
        except Exception as e:  # noqa: BLE001
            return tab + added, f"density solve unavailable ({type(e).__name__}); table + added_taps"
    return tab + added, mode


def _read_bins(ck, plan_path, tree):
    f = ck.get("sink_bins_file")
    if not f:
        return None
    pd = Path(plan_path).resolve().parent if plan_path else Path(".")
    cands = [Path(f)] if os.path.isabs(f) else []
    for root in [tree] + list(DEFAULT_TREES) + [str(pd)]:
        if root:
            cands.append(Path(root) / f)
    cands.append(pd / "sink_bins" / Path(f).name)
    for c in cands:
        if c.is_file():
            try:
                return [(float(r[0]), float(r[1]), float(r[2]) if len(r) > 2 else 1.0) for r in json.loads(c.read_text())["bins"]]
            except (OSError, ValueError, KeyError, TypeError):
                return None
    return None


def _run(raw, plan_path, tree, types, P=None, cache=None):
    pt = raw["partition_types"]
    res, skipped, tried = [], {}, []
    for tn in sorted(types or pt):
        t = pt.get(tn)
        if not t or not t.get("clock"):
            continue
        ck = t["clock"]
        if ck.get("tap_mode") in ("grid", "grid+sinks", "sinks", "grid+explicit") and not (ck.get("added_taps") or ck.get("taps")):
            skipped[tn] = "grid taps not derived"
            continue
        if P is None and ck.get("tap_mode") == "density" and not tried and not (cache and tn in cache):
            tried.append(1)
            try:
                import schema
                P = schema.Plan(raw, plan_path)
            except Exception:  # noqa: BLE001 -- falls back to the clock.taps table
                P = None
        bins = _read_bins(ck, plan_path, tree)
        if not bins:
            skipped[tn] = "no sink bins"
            continue
        taps, how = _tap_list(raw, plan_path, tn, t, P, cache)
        if not taps:
            skipped[tn] = "no taps"
            continue
        target = float(ck.get("insertion_ps", 250.0))
        tol = float(ck.get("insertion_tol_ps", 40.0))
        bad, rows = judge(taps, bins, _boxes(t), target, tol, ck.get("tap_slowest_max_ps"))
        res.append(dict(type=tn, cap=float(ck.get('tap_slowest_max_ps') or target + 15.0), taps=len(taps), how=how, regions=len(rows), target=target, tol=tol, bad=bad, rows=rows,
                        max_leg=max((r["dmax"] for r in rows), default=0.0),
                        spread=(max(r["arr"] for r in rows) - min(r["arr"] for r in rows)) if rows else 0.0))
    return res, skipped


def _cache(c):
    if isinstance(c, (str, Path)) and os.path.isfile(c):
        return json.load(open(c))
    return c if isinstance(c, dict) else None


def _line(r):
    parts = []
    for kind, d in r["bad"]:
        if kind == "LEG":
            parts.append(f"LEG tap {d['tap']} leg {d['dmax']:.0f} um > {REACH_UM:.0f} ({d['over']:.0f} of {d['n']:.0f} sinks over)")
        elif kind == "SLOW":
            parts.append(f"SLOW {d['k']} region(s) cannot balance: tap {d['tap']} natural+29 = {d['slow']:.0f} ps > slowest cap {d['cap']:.0f} (leg {d['dmax']:.0f} um, {d['n']:.0f} sinks)")
        elif kind == "BAND":
            parts.append(f"BAND est arrival {d['lo']:.0f}..{d['hi']:.0f} ps spread {d['spread']:.1f} > tol {r['tol']:.0f}")
        else:
            parts.append(f"DEV est mean {d['mean']:.0f} ps > {d['limit']:.0f}")
    legs = [x for x in r["bad"] if x[0] == "LEG"]
    if len(legs) > 1:
        parts = [p for p in parts if not p.startswith("LEG")] + [f"LEG {len(legs)} regions over {REACH_UM:.0f} um (worst {r['max_leg']:.0f})"]
    return f"WARN {CHECK} {r['type']}: " + "; ".join(parts) + f" ({r['regions']} regions, target {r['target']:.0f}; {r['how']})"


def findings(raw, plan_path=None, tree=None, types=None, P=None, taps_cache=None, **_kw):
    try:
        res, skipped = _run(raw, plan_path, tree, types, P, _cache(taps_cache))
    except Exception as e:  # noqa: BLE001 -- an estimator reports
        return [f"WARN {CHECK} not checked: {type(e).__name__}: {str(e)[:200]}"]
    out = [_line(r) for r in sorted(res, key=lambda r: -r["max_leg"]) if r["bad"]][:MAX_LINES]
    nb = sum(1 for r in res if r["bad"])
    out.append(f"WARN {CHECK} summary: {len(res)} types judged, {nb} over, {len(skipped)} not judged (no bins/taps); report-only")
    return out


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--types")
    ap.add_argument("--tree")
    ap.add_argument("--taps-cache")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    here = str(Path(__file__).resolve().parent)
    sys.path.insert(0, here)
    raw = json.load(open(a.plan))
    P = None
    cache = _cache(a.taps_cache)
    try:
        if cache:
            raise ImportError("taps cache given")
        import schema
        P = schema.Plan(raw, a.plan)
    except Exception as e:  # noqa: BLE001
        print(f"# schema.Plan unavailable: {type(e).__name__}", file=sys.stderr)
    res, skipped = _run(raw, a.plan, a.tree, a.types.split(",") if a.types else None, P, cache)
    for r in res:
        print(("FAIL " if r["bad"] else "PASS ") + f"{r['type']}: regions {r['regions']} max_leg {r['max_leg']:.0f} um nat+29 max {max(x['slow'] for x in r['rows']):.0f} ps (cap {r['cap']:.0f}) spread {r['spread']:.1f} ps"
              + ("  | " + _line(r).split(": ", 1)[1] if r["bad"] else ""))
    print(f"# not judged: {skipped}")
    if a.json:
        json.dump(dict(res=res, skipped=skipped), open(a.json, "w"), indent=1, default=str)
    return 0


if __name__ == "__main__":
    sys.exit(main())
