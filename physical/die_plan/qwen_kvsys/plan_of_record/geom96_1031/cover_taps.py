#!/usr/bin/env python3
"""DIE-KV-58 10-31 (GEOM-96, kv3_io_cor): the cover search behind added_taps.json (same model DIE-KV-57 used for
GEOM-93): plan_geom.type_sites sinks (planned sinks, ring-read bands, landed out-face registers, reset relays) and
forwarded-clock band corners.  Greedy: while some sink is beyond RADIUS of every clock entry, put a tap where it covers
the most uncovered sinks (candidate = an uncovered sink near the farthest one), legalised by schema.tap_clear(strict)
clear of the taps and reset.local_taps_um; then split any tap whose nearest-tap load exceeds LOAD_MAX at the centroid
of its far half.  The reset tree re-sites with the taps, so repeat on the updated plan until stable.
usage (repo root): cover_taps.py PLAN TYPE OUT_ADDED.json"""
import copy, json, sys
from pathlib import Path
sys.path.insert(0, "tools/die_plan")
import schema as S  # noqa: E402
import plan_geom as PG  # noqa: E402
import taps as TP  # noqa: E402

RADIUS = 170.0
LOAD_MAX = 1300.0


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def plan_with(raw, path, tn, added):
    r = copy.deepcopy(raw)
    ck = r["partition_types"][tn]["clock"]
    if added:
        ck["tap_mode"] = "grid+explicit"
        ck["added_taps"] = [dict(name=f"clk_t{len(GRID) + i}", xy=list(xy)) for i, xy in enumerate(added)]
    return S.Plan(r, path)


def main():
    global GRID
    path, tn, out = sys.argv[1], sys.argv[2], sys.argv[3]
    raw = json.loads(open(path).read())
    P0 = S.Plan(copy.deepcopy(raw), Path(path).resolve())
    GRID = [(x, y) for _, x, y in S._grid_taps(P0, tn)]
    t = P0.types[tn]
    resv = [tuple(x) for x in t.get("reset", {}).get("local_taps_um", [])]
    added = []
    for it in range(8):
        P = plan_with(raw, Path(path).resolve(), tn, added)
        G = PG.type_sites(P, tn)
        pts = [(x, y, wt) for x, y, wt, _ in G["sinks"]] + [(x, y, 0.0) for x, y, _ in G["fwd"]]
        ent = GRID + added
        changed = False
        while True:
            unc = [p for p in pts if min(man(p, e) for e in ent) > RADIUS]
            if not unc:
                break
            far = max(unc, key=lambda p: min(man(p, e) for e in ent))
            cand = [p for p in unc if man(p, far) <= RADIUS] or [far]
            best = max(cand, key=lambda c: (sum(1 for q in unc if man(q, c) <= RADIUS), -man(c, far)))
            x, y = S.tap_clear(t, best[0], best[1], taken=ent + resv, strict=True)
            if man((x, y), far) > RADIUS:                 # legalised too far: put it on the far sink instead
                x, y = S.tap_clear(t, far[0], far[1], taken=ent + resv, strict=True)
            added.append((round(x, 4), round(y, 4)))
            ent = GRID + added
            changed = True
        # load split on the nearest-tap rule
        for _ in range(20):
            load = {}
            for x, y, wt in pts:
                if wt <= 0:
                    continue
                i = min(range(len(ent)), key=lambda j: man((x, y), ent[j]))
                load.setdefault(i, []).append((x, y, wt))
            i, L = max(load.items(), key=lambda kv: sum(w for *_, w in kv[1]))
            if sum(w for *_, w in L) <= LOAD_MAX:
                break
            e = ent[i]
            L.sort(key=lambda p: -man(p, e))
            half, acc, tot = [], 0.0, sum(w for *_, w in L)
            for p in L:
                half.append(p)
                acc += p[2]
                if acc >= tot / 2:
                    break
            cx = sum(p[0] * p[2] for p in half) / acc
            cy = sum(p[1] * p[2] for p in half) / acc
            x, y = S.tap_clear(t, cx, cy, taken=ent + resv, strict=True)
            added.append((round(x, 4), round(y, 4)))
            ent = GRID + added
            changed = True
        print("iter", it, "added", len(added), flush=True)
        if not changed:
            break
    P = plan_with(raw, Path(path).resolve(), tn, added)
    m = PG.type_metrics(P, tn)
    fin = TP.grid_explicit_taps(P, tn)
    json.dump({tn: [dict(name=f"clk_t{len(GRID) + i}", xy=list(xy)) for i, xy in enumerate(added)]}, open(out, "w"),
              indent=1)
    print(tn, "added", len(added), "clock_reach", m["clock_reach_max"], m["clock_reach_far"], "tap_sinks",
          m.get("grid_tap_sinks_max"), "grid_explicit PASS", len(fin))


if __name__ == "__main__":
    main()
