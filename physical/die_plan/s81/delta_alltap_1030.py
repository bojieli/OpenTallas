#!/usr/bin/env python3
"""DIE-S81-39 plan-time clock_reach + tap-load fold-in (COORD 23:5x; 12.20 taps only, nothing moved).

plan_geom.py (AUTOBUILD-GATE-1, the existing AUTO-GEOM rules at plan time) FAILs most S81 non-station types on
clock_reach (> 220 um sink -> nearest clock entry) and grid tap load (> 1500 plan sinks on the nearest-tap split): they
still use the R4 pitch grid (one tap per 400-um cell) while their plan sink inventory is dense.  For every non-hard
type that FAILs clock_reach or clock_tap_sinks (or the --types regex):
  1. a grid / grid+sinks type is frozen as tap_mode "explicit" with its CURRENT taps (schema.tap_grid: same names, same
     xy, same order) -- the stform2 station form; early core taps (clock.taps kind core) stay as they are;
  2. reach: every plan_geom sink (plan sinks, reset relays/root/outs, landing groups, ring read bands, forwarded ring
     corners) farther than REACH_T (200 um, under the 220 limit) from every clock entry gets a light tap at the site
     (greedy farthest-first cover, schema.tap_clear strict, TAP_MARGIN inside the outline); a site that is not already
     a planned sink (relay / landing / ring) also becomes a sink row [x, y, 1] so the explicit tap is never empty;
  3. load: a grid tap whose nearest-tap plan load exceeds LOAD_T (1400, under the 1500 cap) gets one new tap at the
     weighted L1 median of the far half of its sinks;
  iterated with the plan recomputed (reset relays are sited from the taps) until nothing is added.
Forwarded clock out pins re-take the nearest tap (stform2 rule).  Asserted: nothing else changes (outline, pins, buses,
ft slots, cores, latency); per type only clock.taps / tap_mode / sink_sites_um / landing pin source_clock_port.
usage (repo root): delta_alltap_1030.py PLAN_IN PLAN_OUT REPORT.json [--types REGEX] [--only-failing]"""
import argparse
import copy
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "tools" / "die_plan"))
sys.path.insert(0, str(ROOT / "tools" / "autopilot"))
import schema as S  # noqa: E402
import taps as TP  # noqa: E402
import plan_geom as PG  # noqa: E402
import geom_rules as GR  # noqa: E402
from gen_phys import clock_pins  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
import compact_plan as CP  # noqa: E402

REACH_T = 185.0
LOAD_T = 1400.0
MAX_ITER = 40
_VALIDATE = TP.grid_explicit_taps


def _sites_only(P, tn):
    """iteration-time READ of the tap table (schema.tap_grid -> taps.grid_explicit_taps) while taps are still being
    added: geometry-checked endpoints (grid_explicit_sites), budget not yet applied.  The FINAL table of every type is
    validated by the unmodified taps.grid_explicit_taps; a refusal is reported and the type is reverted."""
    return [(n, x, y, 0, 0.0) for n, x, y in TP.grid_explicit_sites(P, tn)]


def l1(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def wmedian(vals):
    vals = sorted(vals)
    tot = sum(w for _, w in vals)
    acc = 0.0
    for v, w in vals:
        acc += w
        if acc >= tot / 2:
            return v
    return vals[-1][0]


def freeze(P, raw, tn):
    """grid -> grid+explicit: the R4 grid stays exactly as it is (computed, not stored); added taps go to added_taps."""
    ck = raw["partition_types"][tn]["clock"]
    if ck.get("tap_mode", "grid") != "grid":
        return False
    ck["tap_mode"] = "grid+explicit"
    ck["added_taps"] = []
    return True


def add_tap(raw, tn, xy, P):
    t = raw["partition_types"][tn]
    ck = t["clock"]
    w, h = t["outline_um"]
    n_grid = len(S._grid_taps(P, tn))
    taken = [(x, y) for _, x, y in S._grid_taps(P, tn)] + [tuple(p["xy"]) for p in ck["added_taps"]]
    m = TP.TAP_MARGIN_UM
    x0, y0 = min(max(xy[0], m), w - m), min(max(xy[1], m), h - m)
    q = None
    # the site may sit on a hard core (keep-clear): walk toward the outline centre in 8.64-um steps, then a ring of
    # offsets, until schema.tap_clear(strict) finds a legal site; none -> reported, no tap
    cx, cy = w / 2, h / 2
    cands = [(x0, y0)]
    for k in range(1, 24):
        f = min(1.0, k * 8.64 / max(l1((x0, y0), (cx, cy)), 1e-9))
        cands.append((x0 + (cx - x0) * f, y0 + (cy - y0) * f))
    for r in (17.28, 34.56, 69.12, 103.68, 138.24):
        cands += [(x0 + dx * r, y0 + dy * r) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1))]
    best = None
    for cxy in cands:                                   # the legal site NEAREST the wanted point (tap_clear may jump far)
        if not (m <= cxy[0] <= w - m and m <= cxy[1] <= h - m):
            continue
        try:
            c = S.tap_clear(t, cxy[0], cxy[1], taken, strict=True)
        except ValueError:
            continue
        if best is None or l1(c, (x0, y0)) < l1(best, (x0, y0)):
            best = c
        if l1(best, (x0, y0)) <= 20.0:
            break
    q = best
    if q is None:
        return None
    q = (round(q[0], 4), round(q[1], 4))
    ck["added_taps"].append(dict(name=f"clk_t{n_grid + len(ck['added_taps'])}", xy=list(q)))
    return q


def step(P, raw, tn, rep):
    G = PG.type_sites(P, tn)
    ck = raw["partition_types"][tn]["clock"]
    # cover against the grid (local) taps only: the explicit validator binds every sink to a local tap within
    # tap_radius_um, so core / edge clock entries do not count here (stricter than plan_geom's any-entry reach)
    ent = [(x, y) for n, x, y in G["entries"] if GR.GRID_TAP_RE.match(n)] or [(x, y) for _, x, y in G["entries"]]
    added = 0
    # reach: greedy farthest-first cover
    pts = [((x, y), kind) for x, y, _, kind in G["sinks"]] + [((x, y), kind) for x, y, kind in G["fwd"]]
    far = sorted(((min(l1(p, e) for e in ent), p, k) for p, k in pts), reverse=True)
    newt = []
    for d, p, k in far:
        if d <= REACH_T:
            break
        if any(l1(p, q) <= REACH_T for q in newt):
            continue
        q = add_tap(raw, tn, p, P)
        if q is None or l1(p, q) > REACH_T:
            if q is not None:                           # undo: a tap that does not cover its site is not added
                raw["partition_types"][tn]["clock"]["added_taps"].pop()
            rep["unfixable"].append(dict(site=k, xy=p, tap=q))
            newt.append(p)                              # do not retry the same neighbourhood this pass
            continue
        newt.append(q)
        if not k.startswith(("plan", "relay", "reset")):    # relays are re-sited from the taps: counted by the validator
            ck.setdefault("sink_sites_um", []).append([round(p[0], 4), round(p[1], 4), 1])
        rep["added"].append(dict(why="reach", site=k, xy=[round(p[0], 2), round(p[1], 2)], dist=round(d, 1), tap=q))
        added += 1
    if added:
        return added
    # load: nearest split over grid taps
    grid = [(n, x, y) for n, x, y in G["entries"] if GR.GRID_TAP_RE.match(n)]
    if len(grid) < 1:
        return 0
    gxy = [(x, y) for _, x, y in grid]
    own = [[] for _ in grid]
    for x, y, wt, kind in G["sinks"]:
        if wt <= 0:
            continue
        _, i = PG._nearest((x, y), gxy)
        own[i].append((x, y, wt))
    for i, ss in enumerate(own):
        ld = sum(w for _, _, w in ss)
        if ld <= LOAD_T:
            continue
        ds = [(l1((x, y), gxy[i]), (x, y, w)) for x, y, w in ss]
        md = wmedian([(d, s[2]) for d, s in ds])
        farh = [s for d, s in ds if d >= md] or [s for _, s in ds]
        if len(farh) == len(ss) and len({(x, y) for x, y, _ in ss}) == 1:
            rep["unfixable"].append(dict(load=ld, tap=grid[i][0], note="one sink site"))
            continue
        tries = rep.setdefault("split_tries", {})
        key = f"{gxy[i][0]:.1f},{gxy[i][1]:.1f}"
        tries[key] = tries.get(key, 0) + 1
        if tries[key] > 3:                              # a split that does not unload the tap is not repeated
            if tries[key] == 4:
                rep["unfixable"].append(dict(load=ld, tap=grid[i][0], note="split does not unload"))
            continue
        c = (wmedian([(x, w) for x, _, w in farh]), wmedian([(y, w) for _, y, w in farh]))
        q = add_tap(raw, tn, c, P)
        if q is None:
            rep["unfixable"].append(dict(load=ld, tap=grid[i][0], note="no legal split site"))
            continue
        rep["added"].append(dict(why="load", tap_split=grid[i][0], load=ld, tap=q))
        added += 1
    return added


_REFUSE = re.compile(r"grid\+explicit tap (\S+) load=([\d.e+-]+)/(\d+), radius=([\d.e+-]+)/([\d.e+-]+), empty=(True|False)")


def renumber(P, ck, tn):
    n = len(S._grid_taps(P, tn))
    for i, p in enumerate(ck["added_taps"]):
        p["name"] = f"clk_t{n + i}"


def finalize(raw, tn, src, rep):
    """validate with the real taps.grid_explicit_taps.  An ADDED tap that ends up empty is my own surplus: it is
    removed (names renumbered) and the table re-validated.  Any other refusal is reported and the type reverted."""
    ck = raw["partition_types"][tn]["clock"]
    for _ in range(200):
        P = S.Plan(copy.deepcopy(raw), Path(src).resolve())
        try:
            TP.grid_explicit_taps(P, tn)
            return True
        except ValueError as ex:
            m = _REFUSE.search(str(ex))
            n_grid = len(S._grid_taps(P, tn))
            if m and m.group(6) == "True":
                k = int(m.group(1).split("_t")[1]) - n_grid if "_t" in m.group(1) else -1
                if 0 <= k < len(ck["added_taps"]):
                    rep.setdefault("dropped_added", []).append(ck["added_taps"].pop(k)["xy"])
                    renumber(P, ck, tn)
                    continue
            rep["refused"] = str(ex)[:240]
            return False
    rep["refused"] = "finalize did not converge"
    return False


def judge(P, tn):
    m = PG.type_metrics(P, tn)
    r = {x["rule"]: x for x in PG.judge(m, P.name)}
    return m, r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("rp")
    ap.add_argument("--types", default=None)
    a = ap.parse_args()
    text = open(a.src).read()
    raw = json.loads(text)
    orig = copy.deepcopy(raw)
    P = S.Plan(copy.deepcopy(raw), Path(a.src).resolve())
    used = sorted({p["type"] for p in P.parts.values()})
    todo, rep = [], {}
    for tn in used:
        if P.types[tn].get("hard") or (a.types and not re.search(a.types, tn)):
            continue
        try:
            m, r = judge(P, tn)
        except Exception as ex:
            rep[tn] = dict(skip=f"not evaluable: {type(ex).__name__}: {str(ex)[:120]}")
            continue
        bad = [k for k in ("clock_reach", "clock_tap_sinks") if r.get(k, {}).get("status") == "FAIL"]
        if bad:
            todo.append(tn)
            rep[tn] = dict(before={k: r[k]["value"] for k in ("clock_reach", "clock_tap_sinks") if k in r},
                           taps0=len(S.tap_grid(P, tn)), mode0=P.types[tn]["clock"].get("tap_mode", "grid"),
                           added=[], unfixable=[])
    for tn in todo:
        rep[tn]["frozen"] = freeze(P, raw, tn)
        if not rep[tn]["frozen"]:
            rep[tn]["skip"] = "tap_mode " + rep[tn]["mode0"] + " is not grid: outside this delta (reported)"
    todo = [tn for tn in todo if rep[tn]["frozen"]]
    active = list(todo)
    TP.grid_explicit_taps = _sites_only
    for it in range(MAX_ITER):
        P = S.Plan(copy.deepcopy(raw), Path(a.src).resolve())
        n = 0
        nxt = []
        for tn in active:
            k = step(P, raw, tn, rep[tn])
            n += k
            if k:
                nxt.append(tn)
        import time
        print(time.strftime("%H:%M:%S"), "pass", it, "types", len(active), "taps added", n, flush=True)
        active = nxt
        if not active:
            break
    TP.grid_explicit_taps = _VALIDATE
    reverted = []
    for tn in todo:
        if not finalize(raw, tn, a.src, rep[tn]):
            raw["partition_types"][tn] = copy.deepcopy(orig["partition_types"][tn])
            reverted.append(tn)
    todo = [tn for tn in todo if tn not in reverted]
    P = S.Plan(copy.deepcopy(raw), Path(a.src).resolve())
    for tn in todo:
        t = raw["partition_types"][tn]
        fin = TP.grid_explicit_taps(P, tn)
        rep[tn].update(taps=len(fin), tap_load_max=max(q[3] for q in fin), tap_radius_max=max(q[4] for q in fin))
        roots = clock_pins(P, tn)
        moved = []
        for p in t["clock"].get("landing_contract", {}).get("pins", []):
            if p.get("kind") == "clock" and p.get("dir") == "out" and "source_clock_port" in p:
                tap = min(roots, key=lambda r: abs(r[1] - p["xy_um"][0]) + abs(r[2] - p["xy_um"][1]))[0]
                if tap != p["source_clock_port"]:
                    moved.append(f"{p['name']}:{p['source_clock_port']}->{tap}")
                p["source_clock_port"] = tap
        rep[tn]["source_retap"] = moved
    P = S.Plan(copy.deepcopy(raw), Path(a.src).resolve())
    for tn in todo:
        try:
            m, r = judge(P, tn)
            rep[tn]["after"] = {k: [r[k]["value"], r[k]["status"]] for k in ("clock_reach", "clock_tap_sinks") if k in r}
        except Exception as ex:
            rep[tn]["after"] = f"ERROR {type(ex).__name__}: {str(ex)[:160]}"
    # nothing else changed
    for tn in raw["partition_types"]:
        if tn not in todo:
            assert raw["partition_types"][tn] == orig["partition_types"][tn], tn
            continue
        x, y = copy.deepcopy(raw["partition_types"][tn]), copy.deepcopy(orig["partition_types"][tn])
        for z in (x, y):
            for k in ("added_taps", "tap_mode", "sink_sites_um"):
                z["clock"].pop(k, None)
            for p in z["clock"].get("landing_contract", {}).get("pins", []):
                p.pop("source_clock_port", None)
        assert x == y, tn
    for k in raw:
        if k != "partition_types":
            assert raw[k] == orig[k], k
    for tn in todo:
        m = re.search(r'^  "' + re.escape(tn) + r'": ', text, re.M)
        _, j = json.JSONDecoder().raw_decode(text, m.end())
        text = text[:m.end()] + CP._d(raw["partition_types"][tn], 2) + text[j:]
    assert json.loads(text) == raw
    open(a.dst, "w").write(text)
    done = [tn for tn in todo if isinstance(rep[tn].get("after"), dict)
            and all(v[1] != "FAIL" for v in rep[tn]["after"].values())]
    summ = dict(types=len(todo), pass_after=len(done), taps_added=sum(len(rep[t]["added"]) for t in todo),
                reverted_refused=reverted,
                still_fail=sorted(set(todo) - set(done)),
                unfixable=sum(len(rep[t]["unfixable"]) for t in todo))
    rep["_summary"] = summ
    json.dump(rep, open(a.rp, "w"), indent=1, default=str)
    print(json.dumps(summ)[:3000])


if __name__ == "__main__":
    main()
