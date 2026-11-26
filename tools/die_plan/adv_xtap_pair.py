#!/usr/bin/env python3
"""adv_xtap_pair.py -- static pre-launch advisory ADV-XTAP-PAIR (QC-INT-R2-HC0TAP 11-26, class C-XTAP-SETUP; COORD FABLE-RC-QC).
REPORT-ONLY: a WARN line, never a gate.

Flags register-to-register paths whose launch and capture registers sit on DIFFERENT clock taps of the plan and whose planned
insertion spread plus tolerance exceeds a budget (default 40 ps; 833 ps clock).  The kit connects every flop to its nearest tap
(clock_taps.tcl, Manhattan), so a pair that straddles a tap boundary is timed against the two trees' insertion difference:
QC sle_hc0 cl38badc56 TT -85.6 ps xh0.go_bad_bits[11] (clk_t67, 267.5 ps) -> xh0.flt (clk_t107, 231.6 ps, skew 76.8 ps).  The
plan already carries the planned model per tap: clock.tap_offset.per_port_ps[type][tap] = {TT, FF, tol} (arrival minus the
partition's median glue tap; tol = half the instance range + 10 ps).  For a pair on taps a != b:

    est_ps = |TT_a - TT_b| + max(tol_a, tol_b)         (a tap without a row counts as TT 0 / tol 0 and is named in the line)

Inputs: the plan taps (explicit clock.taps / added_taps / the pitch grid via adv_tap_insbudget._taps; density-mode types through
taps.density_taps when schema imports) and a pair census of a placed netlist, cache["xtap_pairs"][type] =
{"die_um": [w, h], "kit": str, "pairs": [[launch_x, launch_y, capture_x, capture_y, n], ...]} (n = pairs binned at those sites).
`adv_xtap_pair.py build-pairs` writes one from a sink list (inst x y per register) and a cone dump (EP <capture> x y / S <capture>
<launch> x y, the format of QC-INT-R2-HC0TAP cone.tcl).  A type without a pair census is not judged.

    findings(raw, plan_path=None, cache=None|path|dict, types=None, max_lines=20, budget_ps=40.0) -> [str]
    adv_xtap_pair.py PLAN --cache pairs.json [--types a,b] [--budget-ps 40] [--json OUT]
    adv_xtap_pair.py build-pairs --type T --die W,H --sinks sinks.txt --cone cone.txt -o pairs.json
"""
import collections
import json
import os
import sys

CHECK = "ADV-XTAP-PAIR"
BUDGET_PS = 40.0
MAX_LINES = 20


def _row(raw, tn, tap):
    r = (((raw.get("clock") or {}).get("tap_offset") or {}).get("per_port_ps") or {}).get(tn, {}).get(tap)
    if not isinstance(r, dict) or "TT" not in r:
        return None
    return float(r["TT"]), float(r.get("tol", 0.0))


def est_ps(raw, tn, a, b):
    """-> (est ps, rows missing) for a pair on distinct taps a and b."""
    ra, rb = _row(raw, tn, a), _row(raw, tn, b)
    miss = [n for n, r in ((a, ra), (b, rb)) if r is None]
    (ta, ua), (tb, ub) = ra or (0.0, 0.0), rb or (0.0, 0.0)
    return abs(ta - tb) + max(ua, ub), miss


def _taps(raw, plan_path, tn):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import adv_tap_insbudget as T
    taps, mode = T._taps(raw, plan_path, tn)
    if taps is not None:
        return taps, mode
    if mode != "density":
        return None, mode
    try:
        import schema
        import taps as TP
        P = schema.Plan(raw, plan_path)
        return [(n, float(x), float(y)) for n, x, y, *_ in TP.density_taps(P, tn)], mode
    except Exception as e:  # noqa: BLE001 -- an estimator reports
        return None, f"density taps not derived ({type(e).__name__})"


def nearest(taps, x, y):
    best, bd = 0, None
    for i, (_n, tx, ty) in enumerate(taps):
        d = abs(x - tx) + abs(y - ty)
        if bd is None or d < bd:
            best, bd = i, d
    return best


def load_cache(src):
    if isinstance(src, dict):
        return src
    if src and os.path.exists(src):
        return json.load(open(src))
    return {}


def judge(raw, plan_path, tn, census, budget_ps):
    taps, mode = _taps(raw, plan_path, tn)
    if not taps:
        return None, f"tap_mode {mode}"
    t = raw["partition_types"][tn]
    if [round(v, 2) for v in census.get("die_um") or []] != [round(v, 2) for v in t.get("outline_um") or []]:
        return None, f"pair census outline {census.get('die_um')} != plan {t.get('outline_um')}"
    total = cross = over = 0
    by = collections.Counter()
    miss = set()
    worst = (0.0, "", "")
    for ax, ay, bx, by_, n in census.get("pairs") or []:
        n = int(n)
        total += n
        ia, ib = nearest(taps, ax, ay), nearest(taps, bx, by_)
        if ia == ib:
            continue
        cross += n
        a, b = taps[ia][0], taps[ib][0]
        e, m = est_ps(raw, tn, a, b)
        miss.update(m)
        if e > budget_ps:
            over += n
            by[(a, b)] += n
            if e > worst[0]:
                worst = (e, a, b)
    return dict(type=tn, total=total, cross=cross, over=over, worst=worst, top=by.most_common(3), missing=sorted(miss),
                kit=str(census.get("kit", ""))[:80]), ""


def findings(raw, plan_path=None, cache=None, types=None, max_lines=MAX_LINES, budget_ps=BUDGET_PS, **_kw):
    try:
        return _findings(raw, plan_path, cache, types, max_lines, budget_ps)[0]
    except Exception as e:  # noqa: BLE001
        return [f"WARN {CHECK} not checked: {type(e).__name__}: {str(e)[:200]}"]


def _findings(raw, plan_path, cache, types, max_lines, budget_ps):
    pairs = (load_cache(cache) or {}).get("xtap_pairs") or {}
    rows, skipped = [], {}
    for tn in sorted(types or raw["partition_types"]):
        c = pairs.get(tn)
        if not c or tn not in raw["partition_types"]:
            continue
        r, why = judge(raw, plan_path, tn, c, budget_ps)
        if r is None:
            skipped[tn] = why
        else:
            rows.append(r)
    out = []
    for r in sorted((r for r in rows if r["over"]), key=lambda r: -r["over"])[:max_lines]:
        e, a, b = r["worst"]
        top = ", ".join(f"{x}->{y} x{n}" for (x, y), n in r["top"])
        miss = f"; no tap_offset row: {','.join(r['missing'][:4])}" if r["missing"] else ""
        out.append(f"WARN {CHECK} {r['type']}: {r['over']:,} of {r['total']:,} register pairs cross taps with planned spread+tol over "
                   f"{budget_ps:.0f} ps ({r['cross']:,} cross-tap); worst {a} vs {b} {e:.1f} ps; top {top}{miss} "
                   f"-> seat launch and capture on one tap (tap_group / place_region); report-only")
    nbad = sum(1 for r in rows if r["over"])
    out.append(f"WARN {CHECK} summary: {len(rows)} types judged, {nbad} with cross-tap pairs over {budget_ps:.0f} ps, {len(skipped)} not judged; report-only")
    return out, rows, skipped


def build_pairs(type_name, die, sinks_txt, cone_txt, kit=""):
    """{"xtap_pairs": {type: census}} from `inst x y` register sites and an EP/S cone dump."""
    def norm(s):
        return s.replace("\\", "")
    at = {}
    for ln in open(sinks_txt):
        f = ln.split()
        if len(f) >= 4:
            at[norm(f[0])] = (float(f[2]), float(f[3]))
    cap = {}
    pairs = collections.Counter()
    for ln in open(cone_txt):
        f = ln.split()
        if f[0] == "EP" and len(f) >= 4 and f[2] != "MISSING":
            cap[norm(f[1])] = (float(f[-2]), float(f[-1]))
        elif f[0] == "S" and len(f) >= 5:
            c, s = norm(f[1]), norm(f[2])
            if c in cap and s in at:
                (cx, cy), (sx, sy) = cap[c], at[s]
                pairs[(round(sx, 1), round(sy, 1), round(cx, 1), round(cy, 1))] += 1
    return {"xtap_pairs": {type_name: {"die_um": list(die), "kit": kit, "pairs": [list(k) + [n] for k, n in sorted(pairs.items())]}}}


def main(argv=None):
    import argparse
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "build-pairs":
        ap = argparse.ArgumentParser(prog="adv_xtap_pair.py build-pairs")
        ap.add_argument("--type", required=True)
        ap.add_argument("--die", required=True)
        ap.add_argument("--sinks", required=True)
        ap.add_argument("--cone", required=True)
        ap.add_argument("--kit", default="")
        ap.add_argument("-o", "--out", required=True)
        a = ap.parse_args(argv[1:])
        doc = build_pairs(a.type, [float(v) for v in a.die.split(",")], a.sinks, a.cone, a.kit)
        json.dump(doc, open(a.out, "w"))
        print(f"{a.out}: {sum(p[4] for p in doc['xtap_pairs'][a.type]['pairs'])} pairs")
        return 0
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--cache", required=True)
    ap.add_argument("--types")
    ap.add_argument("--budget-ps", type=float, default=BUDGET_PS)
    ap.add_argument("--json")
    ap.add_argument("--max-lines", type=int, default=MAX_LINES)
    a = ap.parse_args(argv)
    raw = json.load(open(a.plan))
    lines, rows, skipped = _findings(raw, a.plan, a.cache, a.types.split(",") if a.types else None, a.max_lines, a.budget_ps)
    for ln in lines:
        print(ln)
    if a.json:
        json.dump(dict(rows=rows, skipped=skipped), open(a.json, "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
