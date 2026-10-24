#!/usr/bin/env python3
"""KV-P3b 10-23: bit-exact audit of the plan's tap-tree lanes (split-bus false PASS check).

census_cov credits a tap-tree destination through forwarding partitions with the widest lane chain, assuming the tree
is a BROADCAST (every destination needs the same bits).  A split bus (bits 0-31 to A, 32-63 to B) needs the SUM on the
shared trunk.  This audit takes the as-built bit-level connectivity (bind/bitcon.py output: per conn src bit -> dst bit)
and, for every lane of every `tap_tree <src>.<bus>` group, the union of source bits that the destinations downstream of
that lane need; a lane narrower than that union under-carries.

    python3 taptree_audit_v32.py BITCON.json.gz die_plan.json census/census_map_v32.json > taptree_audit_v32.json
"""
import gzip
import json
import sys
from collections import defaultdict

bc = json.load(gzip.open(sys.argv[1]))
P = json.load(open(sys.argv[2]))
cmap = json.load(open(sys.argv[3]))["parts"]
ports = P["ports"] if isinstance(P["ports"], dict) else {p["id"]: p for p in P["ports"]}
lanes = P["lanes"] if isinstance(P["lanes"], dict) else {l["id"]: l for l in P["lanes"]}


def dst_parts(c, db):
    """plan partitions of one as-built destination bit (the PHY slices / SerDes halves are split by port / bit)"""
    d, dp = c["d"], c["dp"]
    if d == "serdes_host":
        if dp == "tx_flit":
            return ["sys_SW"] if db < 522 else ["sys_SE"]
        return ["sys_SW", "sys_SE"]
    if d.startswith("phy_") and d.count("_") == 1:
        import re
        m = re.match(r"[a-z]+(\d+)$", dp)
        return [f"{d}_{int(m.group(1)) // 4}"] if m else [f"{d}_{k}" for k in range(8)]
    return [cmap[d]] if d in cmap else []


need = defaultdict(lambda: defaultdict(set))       # (src block, src port) -> dst partition -> src bits
for c in bc["conns"]:
    for sb, db in c["pairs"]:
        for dp in dst_parts(c, db):
            need[(c["s"], c["sp"])][dp].add(sb)

groups = defaultdict(list)
for lid, ln in lanes.items():
    note = ln.get("note", "")
    if note.startswith("tap_tree "):
        groups[note.split()[1]].append(lid)

out, bad = [], 0
for src, lids in sorted(groups.items()):
    sblock, sport = src.rsplit(".", 1)
    edges = {}
    for lid in lids:
        ch = lanes[lid]["ports"]
        a, b = ports[ch[0]]["src"]["part"], ports[ch[-1]]["dst"]["part"]
        edges[lid] = (a, b, min(ports[p]["width"] for p in ch))
    nxt = defaultdict(list)
    for lid, (a, b, w) in edges.items():
        nxt[a].append(lid)
    nd = need.get((sblock, sport), {})

    def reach(part, seen):
        r = {part}
        for l2 in nxt.get(part, []):
            b2 = edges[l2][1]
            if b2 not in seen:
                seen.add(b2)
                r |= reach(b2, seen)
        return r
    for lid, (a, b, w) in sorted(edges.items()):
        down = reach(b, {b})
        bits = set()
        for p in down:
            bits |= nd.get(p, set())
        rec = dict(group=src, lane=lid, src_part=a, dst_part=b, width=w, needed_bits=len(bits),
                   downstream=sorted(p for p in down if p in nd))
        if len(bits) > w:
            rec["deficit"] = len(bits) - w
            bad += 1
        out.append(rec)
summary = dict(schema="opentallas.kv_p3b.taptree_audit.v1", groups=len(groups), lanes=len(out),
               under_carrying_lanes=bad, deficit_bits=sum(r.get("deficit", 0) for r in out),
               worst=sorted((r for r in out if "deficit" in r), key=lambda r: -r["deficit"])[:40])
json.dump(dict(summary=summary, lanes=out), sys.stdout, indent=1)
