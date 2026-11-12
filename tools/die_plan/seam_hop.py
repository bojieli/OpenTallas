"""G0 SEAM-HOP advisory (SEAM-HOP-1, COORD 2026-11-11 17:3x): the distance from the LAST relay station inside one
partition to the FIRST station in the next partition along a lane, across the seam.

check.py `hops` judges each lane against the lane reach through the lane_geometry register list; this module reports
the seam legs on their own, per lane/bus, against the 405-um M4-M7 signal reach (schema.SIGNAL_REACH_UM, owner rule
450-um repeater spacing, 405 practical at 320-ps slew).  The leg is routed through the seam pin:

    hop = |last station - seam pin| + |seam pin - first station of the next partition|     (Manhattan, die frame)

The station points are lane_geometry's (exact ft_full_stage centres of bit 0 when the type has a full-stage
placement, else the slot regs_um hints, else evenly spaced on the slot route); at a lane end the station is the
sink / source type's internal_stations entry for that bus.  Advisory: findings are WARN
check "seam_hop"; they never change an ERROR count.  A geometric lower bound, not a routed length.

    python3 tools/die_plan/seam_hop.py PLAN.json [--limit 405] [--top 10] [--json OUT.json]
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import schema as S  # noqa: E402

EPS = 1e-6


def _man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _internal_legs(P, part, bus, pin):
    """[(leg_um, station_xy, pin_end_xy)] one per internal_stations entry conn 'bus:<bus>' of `part` with stations: the
    pin end is whichever of from_um / to_um lies nearer the seam pin, the station is the end of regs_um on that side,
    leg = Manhattan(station, that pin end).  [] = no declared station (the core flop itself, nothing to measure)."""
    out = []
    for e in P.types[P.parts[part]["type"]].get("internal_stations", []) or []:
        if e.get("conn") != f"bus:{bus}" or not e.get("regs_um"):
            continue
        fr, to = P.to_die(part, tuple(e["from_um"])), P.to_die(part, tuple(e["to_um"]))
        at_from = _man(fr, pin) <= _man(to, pin)
        st = P.to_die(part, tuple(e["regs_um"][0 if at_from else -1]))
        pe = fr if at_from else to
        out.append((_man(st, pe), st, pe))
    return out


def _join(src, dst):
    """worst seam hop of the two sides -> (hop, src_item, dst_item) or None.  A slot side is ONE nominal item (pin None,
    the station -> port point leg); an internal side has one item per bit group.  slot + internal: the slot leg plus
    the worst internal leg.  internal + internal: each item with the item of the other side whose pin end is nearest
    (both ways), hop = leg + leg + the pin-end offset (the pins abut, so ~0)."""
    if not src or not dst:
        return None
    if src[0][2] is None or dst[0][2] is None:
        x = max(src, key=lambda t: t[0])
        y = max(dst, key=lambda t: t[0])
        return (x[0] + y[0], x, y)
    best = None
    for a_, b_ in ((src, dst), (dst, src)):
        for x in a_:
            y = min(b_, key=lambda t: _man(t[2], x[2]))
            h = x[0] + y[0] + _man(x[2], y[2])
            if best is None or h > best[0]:
                best = (h, x, y) if a_ is src else (h, y, x)
    return best


def seam_hops(P, geo, limit=None):
    """[dict(lane, bus, src, dst, hop_um, ...)] for every seam leg of every lane (all legs, not only the long ones).

    Port i of a lane is one seam; hop = (source-side leg) + (sink-side leg) through the seam pin.  The source side is
    the last station of the crossing before the port (slot stations; leg = station -> pin), or, for the lane's first
    port, the source type's internal_stations entries for that bus (per bit group, _internal_legs); the sink side is
    the first station of the crossing after the port, or, for the last port, the sink type's internal_stations (the t19
    NW_io case: the last su01 station sits at the seam pin, NW_io's first station is 719 um inside).  Internal sides
    are joined pin-matched (_join), the worst pair is reported.  A side with no declared station is skipped."""
    limit = S.SIGNAL_REACH_UM if limit is None else float(limit)
    rows = []
    for lid, (_pts, regs, xs) in geo.items():
        cross = P.lane_crossings(lid)
        ports = P.lanes[lid]["ports"]
        if len(cross) != len(xs):
            continue
        first, last, idx = [], [], 1
        for x in xs:
            k = int(x["stations"])
            first.append(idx)
            last.append(idx + k - 1)
            idx += k
        for i, pid in enumerate(ports):
            pr = P.ports[pid]
            sp, dp = pr["src"], pr["dst"]
            if S.DIE_PART in (sp["part"], dp["part"]):
                continue
            pin = P.port_point(pid)
            if i > 0:
                p = regs[last[i - 1]] if 0 <= last[i - 1] < len(regs) else None
                L = [] if p is None else [(_man(p, pin), p, None)]
                slab = f"{cross[i - 1][0]}.{cross[i - 1][1]}[{xs[i - 1]['stations'] - 1}]"
            else:
                L = _internal_legs(P, sp["part"], sp["bus"], pin)
                slab = f"{sp['part']}.bus:{sp['bus']}[internal]"
            if i < len(cross):
                q = regs[first[i]] if 0 <= first[i] < len(regs) else None
                Rr = [] if q is None else [(_man(q, pin), q, None)]
                dlab = f"{cross[i][0]}.{cross[i][1]}[0]"
            else:
                Rr = _internal_legs(P, dp["part"], dp["bus"], pin)
                dlab = f"{dp['part']}.bus:{dp['bus']}[internal]"
            j = _join(L, Rr)
            if j is None:
                continue
            d, (lp, p, pa), (lq, q, pb) = j
            rows.append(dict(lane=lid, port=pid, bus=f"{sp['part']}.{sp['bus']}->{dp['part']}.{dp['bus']}",
                             src=slab, dst=dlab, src_xy=[round(p[0], 1), round(p[1], 1)],
                             dst_xy=[round(q[0], 1), round(q[1], 1)], pin_xy=[round((pa or pb or pin)[0], 1), round((pa or pb or pin)[1], 1)],
                             src_leg_um=round(lp, 1), dst_leg_um=round(lq, 1),
                             hop_um=round(d, 1), limit_um=limit, over=d > limit + EPS))
    return rows


def check_seam_hops(P, R, geo, limit=None, max_msgs=20, top=10):
    """Advisory: one WARN per hop over the limit (first max_msgs, then a count), summary dict for the report."""
    limit = S.SIGNAL_REACH_UM if limit is None else float(limit)
    rows = seam_hops(P, geo, limit)
    over = sorted((r for r in rows if r["over"]), key=lambda r: -r["hop_um"])
    for r in over[:max_msgs]:
        R.warn("seam_hop", f"lane {r['lane']} seam hop {r['src']} -> {r['dst']} (bus {r['bus']}): {r['hop_um']:.0f} um "
               f"> {limit:g} um (last station {r['src_xy']}, first station {r['dst_xy']}) [advisory]", lane=r["lane"])
    if len(over) > max_msgs:
        R.warn("seam_hop", f"... {len(over) - max_msgs} more seam hops over {limit:g} um (summary.seam_hops.worst, "
               "seam_hop.py --json lists all) [advisory]")
    return dict(limit_um=limit, hops=len(rows), over=len(over), lanes_over=len({r["lane"] for r in over}),
                worst=[{k: r[k] for k in ("lane", "bus", "src", "dst", "hop_um")} for r in over[:top]])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--limit", type=float, default=S.SIGNAL_REACH_UM)
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--json", help="write every over-limit hop here")
    a = ap.parse_args(argv)
    import check
    if str(a.plan).endswith('.gz'):
        import gzip
        raw = json.loads(gzip.open(a.plan, 'rt').read())
    else:
        raw = S.load(a.plan)
    P = S.Plan(raw, Path(a.plan).resolve())
    geo = {lid: check.lane_geometry(P, lid) for lid in P.lanes}
    rows = seam_hops(P, geo, a.limit)
    over = sorted((r for r in rows if r["over"]), key=lambda r: -r["hop_um"])
    print(f"{P.name}: {len(rows)} seam hops, {len(over)} over {a.limit:g} um on {len({r['lane'] for r in over})} lanes")
    for r in over[:a.top]:
        print(f"  {r['hop_um']:8.1f} um  lane {r['lane']}  {r['src']} -> {r['dst']}  bus {r['bus']}")
    if a.json:
        Path(a.json).write_text(json.dumps(dict(plan=a.plan, die=P.name, limit_um=a.limit, hops=len(rows), over=over),
                                            indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
