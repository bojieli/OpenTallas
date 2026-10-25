#!/usr/bin/env python3
"""KV-KITS 10-25: intra-partition FORWARD legs of tap-tree lanes (plan R3-INTERNAL gap).

A tap_tree lane (lanes[].note 'tap_tree <net>') that passes THROUGH a partition enters on an in bus and leaves on one
or more out buses of the same tree.  The bind realises that as ONE register hop inside the partition
(u_bin_<in> -> u_bout_<out>), from the in-bus face window to the out-bus face window.  check.py R3-INTERNAL only
measures bus -> hard-core boxes, so a soft partition (no boxes) with a 1-2 mm forward leg passes G0/G0C and the
kit then fails post-route (GEOM-REVIEW-2 04:43 kv3_io_cor host_fdi 1258 um, kv3_hroot host_hbm_rst_n 1953 um).

This audit lists every (type, in bus -> out bus) forward leg whose type-frame window distance (Manhattan, window
mid-points, check._bus_targets) exceeds the station reach, with the number of FIRM internal stations it needs
(internal_stations[] conn 'bus:<out>', regs_um on the L path at <= reach) unless the type already declares them.
Exit 1 when any leg is over reach.  usage: fwd_reach.py PLAN.json [--json OUT] [--reach UM]"""
import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check as C  # noqa: E402
import schema as S  # noqa: E402


def stations_on_L(a, b, n):
    """n FIRM sites evenly spaced on the x-then-y Manhattan path a -> b"""
    L = abs(a[0] - b[0]) + abs(a[1] - b[1])
    out = []
    for k in range(1, n + 1):
        s = L * k / (n + 1)
        dx = abs(b[0] - a[0])
        if s <= dx:
            out.append([round(a[0] + math.copysign(s, b[0] - a[0]), 3), round(a[1], 3)])
        else:
            out.append([round(b[0], 3), round(a[1] + math.copysign(s - dx, b[1] - a[1]), 3)])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--json")
    ap.add_argument("--reach", type=float)
    a = ap.parse_args(argv)
    raw = json.loads(Path(a.plan).read_text())
    P = S.Plan(raw, path=Path(a.plan).resolve())
    reach = a.reach or C.station_max(P)
    tree = {}
    for lid, ln in P.lanes.items():
        nt = str(ln.get("note", ""))
        if nt.startswith("tap_tree"):
            tree[lid] = nt.split("|")[0].strip()
    ins, outs = defaultdict(lambda: defaultdict(set)), defaultdict(lambda: defaultdict(set))
    for pid, pr in P.ports.items():
        lid = pid.rsplit("_", 1)[0]
        if lid not in tree:
            continue
        for side, acc in (("src", outs), ("dst", ins)):
            e = pr[side]
            if e["part"] in P.parts:
                acc[P.parts[e["part"]]["type"]][tree[lid]].add(e["bus"])
    rows = []
    for tn in sorted(set(ins) & set(outs)):
        t = P.types[tn]
        if t.get("hard"):
            continue
        have = {e.get("conn") for e in t.get("internal_stations", [])}
        bt = C._bus_targets(P, tn)
        for net in sorted(set(ins[tn]) & set(outs[tn])):
            for ib in sorted(ins[tn][net]):
                for ob in sorted(outs[tn][net]):
                    if ib.startswith("ft") or ob.startswith("ft") or ib not in bt or ob not in bt:
                        continue   # ft slots carry their own stations (hops check)
                    pa, pb = bt[ib][1], bt[ob][1]
                    d = abs(pa[0] - pb[0]) + abs(pa[1] - pb[1])
                    n = max(0, math.ceil(d / reach) - 1)
                    rows.append(dict(type=tn, tree=net, in_bus=ib, out_bus=ob, in_um=[round(v, 3) for v in pa],
                                     out_um=[round(v, 3) for v in pb], dist_um=round(d, 1), stations=n,
                                     declared=f"bus:{ob}" in have,
                                     verdict="PASS" if d <= reach or f"bus:{ob}" in have else "FAIL",
                                     proposed_regs_um=stations_on_L(pa, pb, n) if n else []))
    bad = [r for r in rows if r["verdict"] == "FAIL"]
    for r in rows:
        print(f"{r['verdict']:4} {r['type']:16} {r['tree']:28} {r['in_bus']:24} -> {r['out_bus']:26} "
              f"{r['dist_um']:7.1f} um  +{r['stations']} st")
    print(f"FWD_REACH {'FAIL' if bad else 'PASS'} {len(bad)}/{len(rows)} forward legs over {reach:g} um")
    if a.json:
        Path(a.json).write_text(json.dumps(dict(schema="opentallas.die_plan.fwd_reach.v1", plan=str(a.plan),
                                                reach_um=reach, rows=rows), indent=1))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
