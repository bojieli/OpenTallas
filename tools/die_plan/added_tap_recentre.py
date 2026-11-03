#!/usr/bin/env python3
"""Re-site grid+explicit ADDED clock taps that fail the tap radius under the current tools (DIE-S81-48 11-02).

Class: main e2a63cfee7d / 74080dbb823 (canonical placement-obstacle union for tap sites and reset relay planning) re-site
the reset relays of a plan built with older tools; a relay (a clocked flop, a tap sink since DIE-S81-39) can land just
beyond tap_radius_um of its nearest ADDED tap, so taps.grid_explicit_taps raises and every consumer of the plan (die
kit, type kits, G0) stops on that type.  Fix = move only the failing added tap, minimally, to a legal site from which
every sink it takes is within the radius (Manhattan minimax box in rotated u=x+y / v=x-y coordinates, nearest legal
point to the old site), re-validate the type with the SAME tools (relays are re-planned from the moved tap), iterate.
A type where no single-tap move closes is reported, never forced.

Frozen reset contract (DIE-S81-49 11-02): a type that publishes a landing collector_tree (clock.landing_contract) keeps
its reset contract -- tap count and indices (rst_n_t<k> nodes the landing children / local sources name), depths,
tap_depth, entry/root, outs and core resets (GUARD_KEYS) -- or the candidate is rejected; so an ADDED tap (which
renumbers the reset outs / core-reset taps) is never taken on such a type, and a move is taken only when the relays it
re-sites keep that contract.  --sidecar SIDECAR republishes the re-solved relays (collector_tree) of every fixed type
into the plan and into the landed sidecar's collector.types[<type>].tree, only where the published tree equalled the
re-solved one before the fix (stale snapshots are refused, never refreshed).  Grid taps, tap names/order and every other type are
untouched; the delta is a list of (type, tap, old_xy, new_xy).

    added_tap_recentre.py PLAN --out PLAN2 [--report R.json] [--types a,b] [--step 0.054] [--max-iter 4] [--add]
                          [--sidecar SIDECAR.json --sidecar-out SIDECAR2.json]
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import schema as S  # noqa: E402
import taps  # noqa: E402
import reset_tree as RT  # noqa: E402

GUARD_KEYS = ("root", "entry", "sync_stages", "depth", "own_depth", "tap_depth", "taps", "n_clock_taps",
              "n_reset_consumers", "local_reset_taps", "outs", "core_resets")


def _norm(o):
    """JSON-normal form (tuples -> lists, int keys -> str) for comparing a re-solved tree with a published one"""
    return json.loads(json.dumps(o, sort_keys=True))


def published_tree(raw, tn):
    return ((raw["partition_types"][tn].get("clock") or {}).get("landing_contract") or {}).get("collector_tree")


def reset_guard(P, raw, tn):
    """None when tn publishes no landing collector_tree or its re-solved reset tree keeps every GUARD_KEYS field of
    the published one; else the first field that changed (relay names / sites may change: --sidecar republishes them)"""
    pub = published_tree(raw, tn)
    if pub is None:
        return None
    new, pub = _norm(RT.for_type(P, tn)), _norm(pub)
    return next((k for k in GUARD_KEYS if pub.get(k) != new.get(k)), None)


def tree_matches(P, raw, tn):
    """the published collector_tree IS the reset tree the current tools solve for tn (relays included)"""
    pub = published_tree(raw, tn)
    return pub is not None and _norm(pub) == _norm(RT.for_type(P, tn))


def republish(P, raw, tn, side=None):
    """write tn's re-solved reset tree as its landing collector_tree (plan + sidecar collector.types[tn].tree, when that
    copy equals the published one); returns (relays before, relays after, relays whose (q, d, xy) changed)"""
    lc = raw["partition_types"][tn]["clock"]["landing_contract"]
    old = lc["collector_tree"]
    new = json.loads(json.dumps(RT.for_type(P, tn)))
    if side is not None:
        st = ((side.get("collector") or {}).get("types") or {}).get(tn)
        if st is not None:
            if _norm(st.get("tree")) != _norm(old):
                raise ValueError(f"{tn}: sidecar collector tree differs from the plan's published collector_tree")
            st["tree"] = new
    key = lambda r: (r.get("q"), r.get("d"), round(float(r["xy"][0]), 4), round(float(r["xy"][1]), 4))
    ko, kn = {key(r) for r in old["relays"]}, {key(r) for r in new["relays"]}
    lc["collector_tree"] = new
    return len(old["relays"]), len(new["relays"]), len(kn - ko)


def check(P, tn):
    try:
        taps.grid_explicit_taps(P, tn)
        return None
    except ValueError as e:
        return str(e)


def tap_sinks(P, tn):
    out = taps.grid_explicit_sites(P, tn)
    ck = P.types[tn].get("clock", {})
    sinks = taps.sink_sites(P, tn)
    if not P.types[tn].get("hard"):
        import reset_tree as RT
        sinks = sinks + [(float(r["xy"][0]), float(r["xy"][1]), 1.0) for r in RT.for_type(P, tn).get("relays", [])]
    cap = int(ck.get("tap_max_sinks", 1500))
    radius = float(ck.get("tap_radius_um", 200.))
    load, far, asg = taps.assign(out, sinks, cap, radius, max_distance_um=radius)
    return out, sinks, asg, load, far, radius


def legal(P, tn, x, y, name):
    t = P.types[tn]
    w, h = t["outline_um"]
    clear = S.TAP_CLEAR_UM
    eps = 1e-8
    from placement_obstacles import placement_boxes
    boxes = list(placement_boxes(t, halo=clear).values())
    others = [(a, b) for n, a, b in taps.grid_explicit_sites(P, tn) if n != name]
    return (clear - eps <= x <= w - clear + eps and clear - eps <= y <= h - clear + eps
            and not any(abs(x - a) < clear - eps and abs(y - b) < clear - eps for a, b in others)
            and not any(a + eps < x < c - eps and b + eps < y < d - eps for a, b, c, d in boxes))


def candidates(pts, x0, y0, radius, step, margin=1.0):
    """legal-agnostic candidate points of the minimax box (radius - margin), nearest to (x0, y0) first"""
    R = radius - margin
    u = [p[0] + p[1] for p in pts]
    v = [p[0] - p[1] for p in pts]
    ulo, uhi, vlo, vhi = max(u) - R, min(u) + R, max(v) - R, min(v) + R
    if ulo > uhi or vlo > vhi:
        return []
    out = []
    n = int(__import__("os").environ.get("ATR_GRID", "24"))
    for i in range(n + 1):
        for j in range(n + 1):
            uu = ulo + (uhi - ulo) * i / n
            vv = vlo + (vhi - vlo) * j / n
            x, y = (uu + vv) / 2, (uu - vv) / 2
            x, y = round(round(x / step) * step, 4), round(round(y / step) * step, 4)
            out.append((abs(x - x0) + abs(y - y0), x, y))
    # also the clamp of the old point into the box
    uu = min(max(x0 + y0, ulo), uhi)
    vv = min(max(x0 - y0, vlo), vhi)
    x, y = (uu + vv) / 2, (uu - vv) / 2
    out.append((abs(x - x0) + abs(y - y0), round(round(x / step) * step, 4), round(round(y / step) * step, 4)))
    return sorted(set(out))


def fix_type(P, raw, tn, step, max_iter, add=False):
    rec = dict(type=tn, moves=[], before=check(P, tn),
               published_tree=published_tree(raw, tn) is not None, tree_matched_before=tree_matches(P, raw, tn))
    for _ in range(max_iter):
        err = check(P, tn)
        if err is None:
            break
        out, sinks, asg, load, far, radius = tap_sinks(P, tn)
        ng = len(S._grid_taps(P, tn))
        bad = [i for i in range(ng, len(out)) if far[i] > radius + 1e-6]
        if not bad:
            rec["unfixable"] = f"error not a radius failure: {err}"
            break
        i = bad[0]
        name, x0, y0 = out[i]
        pts = [(s[0], s[1]) for s, j in zip(sinks, asg) if j == i]
        table = raw["partition_types"][tn]["clock"]["added_taps"]
        ent = next(e for e in table if e["name"] == name)
        done = False
        for _, x, y in candidates(pts, x0, y0, radius, step)[:int(__import__("os").environ.get("ATR_MAXC", "400"))]:
            if not legal(P, tn, x, y, name):
                continue
            old = list(ent["xy"])
            ent["xy"] = [x, y]
            P.types[tn]["clock"]["added_taps"] = table
            S_reset_cache(P)
            e2 = check(P, tn)
            g = reset_guard(P, raw, tn) if (e2 is None or name not in e2) else "radius"
            if g is not None and g != "radius":
                rec.setdefault("rejected_reset_contract", {}).setdefault(g, 0)
                rec["rejected_reset_contract"][g] += 1
            if g is None:
                rec["moves"].append(dict(tap=name, old_xy=old, new_xy=[x, y], move_um=round(abs(x - old[0]) + abs(y - old[1]), 3),
                                         sinks=len(pts), after=e2))
                done = True
                break
            ent["xy"] = old
            S_reset_cache(P)
        if not done and add:
            # no single move closes it (the tap's sinks span > 2 x radius): append ONE light tap at the legal site nearest
            # the out-of-radius sinks' minimax centre; it takes them by the nearest-tap rule, the old tap keeps the rest
            farp = [p for p in pts if abs(p[0] - x0) + abs(p[1] - y0) > radius - 1.0]
            nm = f"clk_t{len(out)}"
            cx = sum(p[0] for p in farp) / len(farp)
            cy = sum(p[1] for p in farp) / len(farp)
            for _, x, y in candidates(farp, cx, cy, radius, step)[:int(__import__("os").environ.get("ATR_MAXC", "400"))]:
                if not legal(P, tn, x, y, nm):
                    continue
                table.append(dict(name=nm, xy=[x, y]))
                S_reset_cache(P)
                e2 = check(P, tn)
                g = reset_guard(P, raw, tn) if (e2 is None or (name not in e2 and nm not in e2)) else "radius"
                if g is not None and g != "radius":
                    rec.setdefault("rejected_reset_contract", {}).setdefault(g, 0)
                    rec["rejected_reset_contract"][g] += 1
                if g is None:
                    rec["moves"].append(dict(tap=nm, old_xy=None, new_xy=[x, y], added=True, for_tap=name,
                                             sinks=len(farp), after=e2))
                    done = True
                    break
                table.pop()
                S_reset_cache(P)
        if not done:
            rec["unfixable"] = f"no legal single-tap move{' or one added tap' if add else ''} closes {name} ({err})"
            break
    rec["after"] = check(P, tn)
    return rec


def S_reset_cache(P):
    """drop the per-plan reset-tree memo and the taps per-type memo (both key on the plan object / type name)"""
    P.__dict__.pop("_reset_tree_cache", None)
    getattr(taps, "_CACHE", {}).clear()
    import reset_tree as RT
    getattr(RT, "_TAPS", {}).clear()      # reset_tree memoises the geometry-only tap read per (plan, type)


def dumps_like(raw, src):
    """write the plan in the format of its source: the repo plan format (pin_template.dumps) or plain indent 1"""
    import pin_template as PT
    try:
        if PT.dumps(json.loads(src)) == src:
            return PT.dumps(raw)
    except (KeyError, TypeError, AttributeError):
        pass
    return json.dumps(raw, indent=1) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--out", required=True)
    ap.add_argument("--report")
    ap.add_argument("--types")
    ap.add_argument("--step", type=float, default=0.054)
    ap.add_argument("--max-iter", type=int, default=4)
    ap.add_argument("--add", action="store_true", help="opt-in: when no single move closes a tap, append one light added tap")
    ap.add_argument("--sidecar", help="landed sidecar (clock_landing_table) whose collector trees are republished too")
    ap.add_argument("--sidecar-out", help="where the republished sidecar is written (required with --sidecar)")
    a = ap.parse_args()
    if bool(a.sidecar) != bool(a.sidecar_out):
        ap.error("--sidecar and --sidecar-out go together")
    raw = S.load(a.plan)
    P = S.Plan(raw, a.plan)
    want = a.types.split(",") if a.types else sorted(P.types)
    recs = []
    for tn in want:
        if P.types[tn].get("clock", {}).get("tap_mode") != "grid+explicit":
            continue
        if check(P, tn) is None:
            continue
        recs.append(fix_type(P, raw, tn, a.step, a.max_iter, add=a.add))
    side = json.loads(Path(a.sidecar).read_text()) if a.sidecar else None
    S_reset_cache(P)
    for r in recs:
        if r["after"] is None and r["moves"] and r["published_tree"]:
            if not r["tree_matched_before"]:
                r["after"] = "published collector_tree was stale before the fix: not republished"
                continue
            if side is None:
                r["after"] = "reset relays re-sited: rerun with --sidecar to republish the collector_tree"
                continue
            r["republished"] = dict(zip(("relays_before", "relays_after", "relays_changed"), republish(P, raw, r["type"], side)))
    rep = dict(plan=a.plan, out=a.out, failing=len(recs), fixed=sum(1 for r in recs if r["after"] is None), types=recs)
    if side is not None:
        Path(a.sidecar_out).write_text(json.dumps(side, separators=(",", ":")))
    Path(a.out).write_text(dumps_like(raw, Path(a.plan).read_text()))
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1))
    print(json.dumps(dict(failing=rep["failing"], fixed=rep["fixed"],
                          moves=[(r["type"], m["tap"], m["old_xy"], m["new_xy"], m.get("move_um", "added")) for r in recs for m in r["moves"]],
                          republished={r["type"]: r["republished"] for r in recs if r.get("republished")},
                          unfixable=[(r["type"], r.get("unfixable") or r["after"]) for r in recs if r["after"] is not None])))
    return 0 if rep["fixed"] == rep["failing"] else 1


if __name__ == "__main__":
    sys.exit(main())
