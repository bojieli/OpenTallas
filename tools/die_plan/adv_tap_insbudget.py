#!/usr/bin/env python3
"""adv_tap_insbudget.py -- static pre-launch estimator ADV-TAP-INSBUDGET (S81HEAD-TAPSPLIT 11-25, COORD Fable item 11).
REPORT-ONLY: never a gate (mode "report"); it returns FAIL lines only for the caller to print.

Predicts a clock tap's post-balance CTS insertion and intra-tap skew from its sink load, and flags the types whose worst tap is
over the per-type budget (insertion <= 550 ps = the 450 ps S81 target + 100, intra-tap skew <= 150 ps; 833 ps clock).

Model (calibrated 2026-11-25 from 3,976 taps >= 20 sinks of 84 S81 / HEAD kits, OT_TAP_INSERTION tap/sinks/ins_ps/skew_ps of the
final post-hook 4_1_cts.log; plan 18a2688b741 and W6).  tap_balance pulls every tap to the target, so insertion does NOT grow with
load until a tap is too big to balance; the load bands (p90 insertion / p90 skew, ps; share over 600 ps / over 150 ps):
      <= 1000 : 489 / 66   (0 % / 1 %)        1651-3000 : 494 / 76  (2 % / 1 %)
    1001-1650 : 490 / 72   (1 % / 1 %)        3001-5000 : 535 / 132 (4 % / 9 %)
   5001-10000 : 610 / 203  (14 % / 19 %)        > 10000 : 1048 / 323 (45 % / 55 %)
  Linear fits on log2(load) explain ~2 % (insertion) / 7 % (skew) of the variance: below 5000 load is not the driver.
  So the budget fails a tap predicted (p90) over budget: load > 5000 FAIL, 3001-5000 WARN, <= 3000 OK.

Load per tap: the newest placed register bins of the type (flops cache placed_bins, exact type else __cl/__pv base; same outline
only) assigned to the plan's taps by the kit's Manhattan nearest-tap rule.  Taps: explicit clock.taps (core taps with a kind are
excluded) + clock.added_taps (+ the pitch grid for grid / grid+explicit types when schema is importable).  Density-mode types are
not judged (their taps come from the density solve).

    findings(raw, plan_path=None, cache=None|path|dict, types=None, max_lines=20) -> [str]
    adv_tap_insbudget.py PLAN [--cache flops_cache.json] [--types a,b] [--json OUT]
"""
import json
import math
import os
import re
import sys

CHECK = "ADV-TAP-INSBUDGET"
INS_BUDGET_PS, SKEW_BUDGET_PS = 550.0, 150.0
# (upper load, p90 insertion ps, p90 skew ps)
BANDS = ((1000, 489, 66), (1650, 490, 72), (3000, 494, 76), (5000, 535, 132), (10000, 610, 203), (float("inf"), 1048, 323))
SUFFIX = re.compile(r"(?:__(?:cl|pv)[0-9a-f]{6,})+$")
CACHE_DEFAULTS = ("adv_cache/flops_cache.json", "/srv/opentallas-scratch2/claude/precheck-cache/flops_cache.json")
MAX_LINES = 20


def predict(load):
    """-> (p90 insertion ps, p90 skew ps) of a tap carrying `load` sinks."""
    for hi, ins, sk in BANDS:
        if load <= hi:
            return float(ins), float(sk)
    return float(BANDS[-1][1]), float(BANDS[-1][2])


def verdict(load):
    ins, sk = predict(load)
    if ins > INS_BUDGET_PS or sk > SKEW_BUDGET_PS:
        return "FAIL"
    return "WARN" if load > 3000 else "OK"


def _taps(raw, plan_path, tn):
    t = raw["partition_types"][tn]
    ck = t.get("clock") or {}
    mode = ck.get("tap_mode")
    if mode == "density":
        return None, "density"
    out = [(x["name"], float(x["xy"][0]), float(x["xy"][1])) for x in ck.get("taps") or []
           if isinstance(x, dict) and "kind" not in x and x.get("xy")]
    out += [(x["name"], float(x["xy"][0]), float(x["xy"][1])) for x in ck.get("added_taps") or [] if x.get("xy")]
    if mode in ("grid", "grid+explicit"):
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import schema
            P = _taps.plan if getattr(_taps, "key", None) == id(raw) else schema.Plan(raw, plan_path)
            _taps.plan, _taps.key = P, id(raw)
            out = [(g[0], float(g[1]), float(g[2])) for g in schema._grid_taps(P, tn)] + \
                  [(x["name"], float(x["xy"][0]), float(x["xy"][1])) for x in ck.get("added_taps") or [] if x.get("xy")]
        except Exception as e:  # noqa: BLE001 -- an estimator reports
            return None, f"grid taps not derived ({type(e).__name__})"
    return out, mode


def loads(taps, bins):
    """nearest-tap (Manhattan, ties to the lower index) load and far distance per tap."""
    load = [0.0] * len(taps)
    far = [0.0] * len(taps)
    for x, y, n in bins:
        best, bd = 0, None
        for i, (_nm, tx, ty) in enumerate(taps):
            d = abs(x - tx) + abs(y - ty)
            if bd is None or d < bd:
                best, bd = i, d
        load[best] += n
        far[best] = max(far[best], bd)
    return load, far


def load_cache(src):
    if isinstance(src, dict):
        return src
    for c in ([src] if src else []) + [os.environ.get("OT_ADV_FLOPS_CACHE") or ""] + list(CACHE_DEFAULTS):
        if c and os.path.exists(c):
            return json.load(open(c))
    return {}


def findings(raw, plan_path=None, cache=None, types=None, max_lines=MAX_LINES):
    try:
        return _findings(raw, plan_path, cache, types, max_lines)[0]
    except Exception as e:  # noqa: BLE001
        return [f"WARN {CHECK} not checked: {type(e).__name__}: {str(e)[:200]}"]


def _findings(raw, plan_path, cache, types, max_lines):
    pb = (load_cache(cache) or {}).get("placed_bins") or {}
    pt = raw["partition_types"]
    rows, skipped = [], {}
    for tn in sorted(types or pt):
        t = pt.get(tn)
        if not t or not (t.get("clock") or {}):
            continue
        b = pb.get(tn) or pb.get(SUFFIX.sub("", tn))
        if not b:
            skipped[tn] = "no placed bins"
            continue
        if [round(v, 2) for v in b.get("die_um") or []] != [round(v, 2) for v in t.get("outline_um") or []]:
            skipped[tn] = f"placed outline {b.get('die_um')} != plan {t.get('outline_um')}"
            continue
        taps, mode = _taps(raw, plan_path, tn)
        if not taps:
            skipped[tn] = f"tap_mode {mode}"
            continue
        ld, far = loads(taps, b["bins"])
        j = max(range(len(ld)), key=lambda i: ld[i])
        ins, sk = predict(ld[j])
        rows.append(dict(type=tn, taps=len(taps), max_tap=taps[j][0], max_load=ld[j], far_um=far[j], ins_p90=ins, skew_p90=sk,
                         verdict=verdict(ld[j]), over5000=sum(1 for v in ld if v > 5000), over3000=sum(1 for v in ld if v > 3000),
                         kit=b.get("kit", "")[:80]))
    out = []
    bad = [r for r in rows if r["verdict"] != "OK"]
    for r in sorted(bad, key=lambda r: -r["max_load"])[:max_lines]:
        out.append(f"{'FAIL' if r['verdict'] == 'FAIL' else 'WARN'} {CHECK} {r['type']}: tap {r['max_tap']} {r['max_load']:,.0f} sinks "
                   f"(far {r['far_um']:.0f} um; {r['over5000']} taps > 5000, {r['over3000']} > 3000 of {r['taps']}) -> predicted p90 "
                   f"insertion {r['ins_p90']:.0f} ps / intra-tap skew {r['skew_p90']:.0f} ps vs budget {INS_BUDGET_PS:.0f} / "
                   f"{SKEW_BUDGET_PS:.0f} (report-only)")
    nf = sum(1 for r in rows if r["verdict"] == "FAIL")
    out.append(f"WARN {CHECK} summary: {len(rows)} types judged, {nf} FAIL (tap > 5000), {len(bad) - nf} WARN (3001-5000), "
               f"{len(skipped)} not judged (no placed bins / other outline / density); report-only")
    return out, rows, skipped


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--cache")
    ap.add_argument("--types")
    ap.add_argument("--json")
    ap.add_argument("--max-lines", type=int, default=MAX_LINES)
    a = ap.parse_args(argv)
    raw = json.load(open(a.plan))
    lines, rows, skipped = _findings(raw, a.plan, a.cache, a.types.split(",") if a.types else None, a.max_lines)
    for ln in lines:
        print(ln)
    if a.json:
        json.dump(dict(rows=rows, skipped=skipped), open(a.json, "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
