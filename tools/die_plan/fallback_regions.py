#!/usr/bin/env python3
"""Bottom-up landed fallback (IF.FALLBACK, OWNER 10-26 16:5x): clock-region partition + landed-crossing table + lane price.

    fallback_regions.py plan PLAN --lat LAT --out DIR [--block G] [--mode class|partition] [--cycles 3]

Region model (fallback, NOT the 12.7 master plan):
  * every partition closes its OWN local clock tree from one partition root (its existing cores kept as they are; a
    type with CP2 early core taps instead feeds its cores from the partition's own CTS, so its boundary flops sit at
    the core-led latency class of that type);
  * a clock REGION = partitions of ONE latency class (the max signed/declared core insertion of the type, else the
    250-ps standard class) that are geometrically inside one G x G block of the partition lattice and connected
    through plan ports; inside a region one equal-leg local tree feeds the partition roots (related pairs timed);
  * every plan port whose src and dst partitions sit in different regions is a LANDED crossing: forwarded clock
    beside the bus, ot_dp_clk_landing ring at the sink (DEPTH4/OFFSET2/RDREG1 = +3 cycles, fixed static latency,
    no credits).  mode=partition: G=0, one region per partition (every port lands).
  * a HARD partition (PHY macro) cannot host a ring: it shares one region with all its port neighbours (merge_hard).
  * two FT readings are priced: `face` = ft stations run on the crossed partition's local clock, so a lane lands at
    every landed face (+3 each); `fwd` = ft stations of a lane run on the lane's forwarded clock (half-cycle
    forwarded hops), so a lane lands ONCE at its sink if any of its faces is landed (+3 per lane).
Outputs (DIR): regions.json, landed_crossings.json (die_clock_mesh write_landed format, one box per partition so
clock_landing_plan.compose resolves each part's region exactly), lat_face.json / lat_fwd.json (s81_latency with the
added cycles), summary.json.  Analysis only: no plan, RTL or calendar edit.
"""
import argparse
import collections
import json
from pathlib import Path


def part_class(t):
    c = [x.get("insertion_ps", 0) for x in t.get("clock", {}).get("taps", []) if x.get("kind") == "core"]
    return f"core{int(round(max(c), -1))}" if c else "std"


def regions(P, block, mode):
    T = P["partition_types"]
    parts = {p["name"]: p for p in P["partitions"]}
    rect = {}
    for n, p in parts.items():
        w, h = T[p["type"]]["outline_um"]
        x, y = p["origin_um"]
        rect[n] = (x, y, x + w, y + h)
    if mode == "partition":
        return merge_hard(P, {n: n for n in parts}), rect, {n: part_class(T[p["type"]]) for n, p in parts.items()}
    xs = sorted({round(p["origin_um"][0], 3) for p in parts.values()})
    ys = sorted({round(p["origin_um"][1], 3) for p in parts.values()})
    cw = min(T[p["type"]]["outline_um"][0] for p in parts.values() if part_class(T[p["type"]]) != "std")
    ch = min(T[p["type"]]["outline_um"][1] for p in parts.values() if part_class(T[p["type"]]) != "std")
    cls = {n: part_class(T[p["type"]]) for n, p in parts.items()}

    def blk(n):
        x0, y0, x1, y1 = rect[n]
        return (int(((x0 + x1) / 2) // (block * cw)), int(((y0 + y1) / 2) // (block * ch)))
    key = {n: (cls[n], blk(n)) for n in parts}
    # connected components of same-key partitions through plan ports (a region is one connected local tree)
    par = {n: n for n in parts}

    def find(a):
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a
    for pr in P["ports"]:
        a, b = pr["src"]["part"], pr["dst"]["part"]
        if a in parts and b in parts and key[a] == key[b]:
            par[find(a)] = find(b)
    comp = {}
    out = {}
    for n in sorted(parts):
        r = find(n)
        if r not in comp:
            c, (bx, by) = key[n]
            comp[r] = f"{c}_b{bx}_{by}_{len([k for k in comp.values() if k.startswith(f'{c}_b{bx}_{by}_')])}"
        out[n] = comp[r]
    del xs, ys
    return merge_hard(P, out), rect, cls


def merge_hard(P, reg):
    """a HARD partition (e.g. the PHY macro) cannot host a landing ring: it shares ONE region with every partition it
    has a port to (its existing pin contract stays synchronous), so none of its ports is landed."""
    T = P["partition_types"]
    for p in P["partitions"]:
        if not T[p["type"]].get("hard"):
            continue
        nb = {q["dst"]["part"] if q["src"]["part"] == p["name"] else q["src"]["part"]
              for q in P["ports"] if p["name"] in (q["src"]["part"], q["dst"]["part"])}
        old = {reg[n] for n in nb | {p["name"]} if n in reg}
        tag = "hard_" + p["name"]
        for n, r in reg.items():
            if r in old:
                reg[n] = tag
    return reg


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    a = sp.add_parser("plan")
    a.add_argument("plan")
    a.add_argument("--lat", required=True)
    a.add_argument("--out", required=True)
    a.add_argument("--block", type=int, default=2)
    a.add_argument("--mode", choices=("class", "partition"), default="class")
    a.add_argument("--cycles", type=int, default=3)
    g = ap.parse_args()
    P = json.load(open(g.plan))
    L = json.load(open(g.lat))
    d = Path(g.out)
    d.mkdir(parents=True, exist_ok=True)
    reg, rect, cls = regions(P, g.block, g.mode)
    parts = set(reg)
    lane_of = {pid: ln["id"] for ln in P["lanes"] for pid in ln["ports"]}
    rows, pairs = [], collections.defaultdict(lambda: dict(ports=0, bits=0))
    for pr in sorted(P["ports"], key=lambda p: p["id"]):
        s, t = pr["src"]["part"], pr["dst"]["part"]
        if s not in parts or t not in parts or reg[s] == reg[t]:
            continue
        rows.append(dict(port=pr["id"], lane=lane_of.get(pr["id"]), src=s, dst=t, src_region=reg[s], dst_region=reg[t],
                         width=pr["width"], kind=pr.get("kind"), added_cycles=g.cycles))
        k = f"{cls[s]}->{cls[t]}"
        pairs[k]["ports"] += 1
        pairs[k]["bits"] += int(pr["width"])
    tags = sorted(set(reg.values()))
    boxes = [dict(k=i, tag=reg[n], box_um=[round(v, 3) for v in rect[n]], parts=[n]) for i, n in enumerate(sorted(reg))]
    table = dict(schema="opentallas.fallback_landed.v1", mode=g.mode, block=g.block, regions_count=len(tags),
                 regions=boxes, added_cycles_per_crossing=g.cycles, crossings=len(rows),
                 bits=sum(int(r["width"]) for r in rows), lanes=len({r["lane"] for r in rows if r["lane"]}),
                 by_class_pair=dict(sorted(pairs.items())), ports=rows)
    (d / "landed_crossings.json").write_text(json.dumps(table, indent=1) + "\n")
    rsum = collections.Counter(reg.values())
    (d / "regions.json").write_text(json.dumps(dict(part_region=reg, part_class=cls,
                                                    region_parts=dict(sorted(rsum.items()))), indent=1) + "\n")
    landed_per_lane = collections.Counter(r["lane"] for r in rows if r["lane"])
    for m in ("face", "fwd"):
        e = json.loads(json.dumps(L))
        for ln, v in e["lanes"].items():
            n = landed_per_lane.get(ln, 0)
            add = g.cycles * (n if m == "face" else (1 if n else 0))
            v["cycles"] += add
            v["natural"] += add
            v["fallback_landed_faces"] = n
        e["fallback"] = dict(mode=g.mode, block=g.block, ft=m, cycles_per_landing=g.cycles)
        (d / f"lat_{m}.json").write_text(json.dumps(e, indent=1) + "\n")
    summ = dict(mode=g.mode, block=g.block, regions=len(tags),
                largest_region_parts=max(rsum.values()), landed_ports=len(rows), landed_bits=table["bits"],
                lanes_with_landing=len(landed_per_lane), lanes_total=len(L["lanes"]),
                added_lane_cycles_face=g.cycles * sum(landed_per_lane.values()),
                added_lane_cycles_fwd=g.cycles * len(landed_per_lane),
                ring_live_ff=sum(5 * (int(r["width"]) + 1) for r in rows),
                by_class_pair=table["by_class_pair"])
    (d / "summary.json").write_text(json.dumps(summ, indent=1) + "\n")
    print(json.dumps(summ))


if __name__ == "__main__":
    main()
