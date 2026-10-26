#!/usr/bin/env python3
"""KV-PLAN3F 10-25 (KV-KITS fwd_reach, scope add 2): FIRM internal stations for tap-tree FORWARD legs over the reach.

tools/die_plan/fwd_reach.py lists every pass-through leg (type, in bus -> out bus of one tap tree) whose type-frame
window distance exceeds ft_station_max_um (405); the bind realises the leg as one register hop, which fails post-route.
For each out bus with a FAIL leg this adds ONE internal_stations[] entry per (in, out) leg, conn 'bus:<out>', with
n = max over the bus's legs of ceil(d / 405) - 1 FIRM regs (one depth per out bus: every leg of it gets n regs), spaced
evenly on the L path in -> out whose corner is clear of the hard cores.  A reg that lands inside a hard-core box
(+ 8.64 um clearance, scope add 3: ft/station sites in core boxes overflowed M2 in kv3_hg_v3) is moved to the nearest
channel point (schema.tap_clear rings); if a hop then exceeds the reach a reg is added (path re-split) until every hop
<= reach and no reg is in a core box -- else the leg is reported unresolved.  Each lane that STARTS at (partition of
that type, out bus) gets fixed_cycles += n (the forward hop's added depth); the R8 / latency regen that follows folds it.

    fwd_stations_v39f.py PLAN_IN PLAN_OUT --report R.json
"""
import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
T = HERE.parents[3] / "tools" / "die_plan"
sys.path.insert(0, str(T))
import check as C  # noqa: E402
import fwd_reach as FR  # noqa: E402
import schema as S  # noqa: E402

CLEAR = 8.64
EPS = 1e-6


def boxes(t):
    out = []
    for c in t.get("hard_cores") or []:
        (ox, oy), (w, h) = c["origin_um"], c["outline_um"]
        dx, dy = c.get("track_offset_um", [0.0, 0.0])
        out.append((ox + dx - CLEAR, oy + dy - CLEAR, ox + dx + w + CLEAR, oy + dy + h + CLEAR))
    return out


def in_core(p, bx):
    return any(b[0] < p[0] < b[2] and b[1] < p[1] < b[3] for b in bx)


def hop(pts):
    return max(abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(pts, pts[1:]))


def place(t, a, b, n, reach, bx):
    """n regs a -> b (L path, corner off the cores), regs in channels, every hop <= reach; (regs, unresolved)"""
    best = None
    for corner in ((b[0], a[1]), (a[0], b[1])):
        path = [a, corner, b]
        for k in range(n, n + 6):
            L = C.plen(path)
            regs = [tuple(round(v, 3) for v in C.point_at(path, L * (i + 1) / (k + 1))) for i in range(k)]
            regs = [p if not in_core(p, bx) else S.tap_clear(t, p[0], p[1], clear=CLEAR, strict=False) for p in regs]
            regs = [(round(x, 3), round(y, 3)) for x, y in regs]
            ok = hop([a] + regs + [b]) <= reach + EPS and not any(in_core(p, bx) for p in regs)
            cand = (not ok, len(regs), corner != (b[0], a[1]), regs)
            if best is None or cand < best:
                best = cand
            if ok:
                break
    return [list(r) for r in best[3]], best[0]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("out")
    ap.add_argument("--report", required=True)
    a = ap.parse_args()
    tmp = Path(a.report).with_suffix(".audit.json")
    import contextlib
    import io
    with contextlib.redirect_stdout(io.StringIO()):
        FR.main([a.plan, "--json", str(tmp)])
    audit = json.loads(tmp.read_text())
    reach = audit["reach_um"]
    raw = json.loads(Path(a.plan).read_text())
    fail = [r for r in audit["rows"] if r["verdict"] == "FAIL"]
    by_bus = defaultdict(list)
    for r in fail:
        by_bus[(r["type"], r["out_bus"])].append(r)
    added, depth, unresolved = [], {}, []
    for (tn, ob), rows in sorted(by_bus.items()):
        t = raw["partition_types"][tn]
        bx = boxes(t)
        n = max(r["stations"] for r in rows)
        regs_all = []
        for r in rows:
            regs, bad = place(t, tuple(r["in_um"]), tuple(r["out_um"]), n, reach, bx)
            regs_all.append((r, regs, bad))
        nd = max(len(g) for _, g, _ in regs_all)
        for r, regs, bad in regs_all:
            if len(regs) < nd:              # one depth per out bus
                regs, bad2 = place(t, tuple(r["in_um"]), tuple(r["out_um"]), nd, reach, bx)
                bad = bad or bad2
            hp = hop([tuple(r["in_um"])] + [tuple(x) for x in regs] + [tuple(r["out_um"])])
            e = dict(conn=f"bus:{ob}", from_um=r["in_um"], to_um=r["out_um"], regs_um=regs, launch=f"bus {r['in_bus']}",
                     capture=f"face bus {ob}",
                     note=f"KV-PLAN3F v3.9f fwd_reach (KV-KITS 10-25): tap-tree forward leg {r['in_bus']} -> {ob} "
                          f"{r['dist_um']:.0f} um, {len(regs)} FIRM stations in channels, hop {hp:.0f} <= {reach:g}")
            t.setdefault("internal_stations", []).append(e)
            added.append(dict(type=tn, in_bus=r["in_bus"], out_bus=ob, dist_um=r["dist_um"], stations=len(regs),
                              max_hop_um=round(hp, 1), in_core=sum(in_core(tuple(x), bx) for x in regs)))
            if bad:
                unresolved.append(added[-1])
        depth[(tn, ob)] = nd
    ptype = {p["name"]: p["type"] for p in raw["partitions"]}
    ports = {p["id"]: p for p in raw["ports"]}
    lanes = {}
    for ln in raw["lanes"]:
        s = ports[ln["ports"][0]]["src"]
        d = depth.get((ptype.get(s["part"]), s["bus"]))
        if d:
            ln["fixed_cycles"] = int(ln.get("fixed_cycles", 0)) + d
            ln["note"] = ln.get("note", "") + f" | v3.9f fwd_reach +{d} internal forward stations at <= {reach:g} um"
            lanes[ln["id"]] = d
    Path(a.out).write_text(json.dumps(raw, indent=1) + "\n")
    rep = dict(schema="opentallas.die_plan.fwd_stations.v1", reach_um=reach, legs_audited=len(audit["rows"]),
               legs_fail=len(fail), types=sorted({k[0] for k in by_bus}), out_buses=len(by_bus),
               entries_added=len(added), stations_added=sum(x["stations"] for x in added),
               lanes_bumped=len(lanes), lane_cycles_added=sum(lanes.values()), unresolved=unresolved,
               depth={f"{k[0]}:{k[1]}": v for k, v in sorted(depth.items())}, added=added, lanes=lanes)
    Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    tmp.unlink()
    print(f"fwd_stations: {len(fail)}/{len(audit['rows'])} legs over {reach:g} um in {len(rep['types'])} types -> "
          f"{len(added)} entries, {rep['stations_added']} stations, {len(lanes)} lanes +{rep['lane_cycles_added']} cycles, "
          f"unresolved {len(unresolved)}")


if __name__ == "__main__":
    main()
