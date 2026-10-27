#!/usr/bin/env python3
"""QC-SU-F4B calibration census (F4A points 6/7): per clock-tree net routed length by layer, via count, and the
GRT->RCX change of that net's stage (child input arrival delta minus driver input arrival delta), TT.
Inputs: ck_wires_prehold.txt (ck_wires.py on the pre-hold 6_final), nodes_grt_TT.tsv, nodes_rcx_TT.tsv. Data only, no fit."""
import sys, collections, json
kit = sys.argv[1]
W = collections.defaultdict(lambda: collections.Counter()); V = collections.Counter()
for l in open(f"{kit}/ck_wires_prehold.txt"):
    f = l.split()
    if f[0] == "W":
        x0, y0, x1, y1 = map(float, f[3:7]); W[f[1]][f[2]] += max(x1 - x0, y1 - y0)
    elif f[0] == "VIA":
        V[f[1]] += 1
def ld(fn):
    d = {}
    for l in open(fn):
        f = l.rstrip("\n").split("\t"); d[f[0]] = dict(cell=f[1], xy=(float(f[2]), float(f[3])), t=float(f[4]), net=f[5])
    return d
g, r = ld(f"{kit}/nodes_grt_TT.tsv"), ld(f"{kit}/nodes_rcx_TT.tsv")
drv = {}
for n in g:
    base = n[:-3] if n.endswith("_nd") else n
    drv[base + "_n"] = n
rows = []
for n, v in g.items():
    net = v["net"]
    if not net.startswith("ot_ms_"):
        continue
    p = drv.get(net)
    dn = r[n]["t"] - v["t"]; dp = (r[p]["t"] - g[p]["t"]) if p else 0.0
    L = W[net]; tot = sum(L.values())
    rows.append(dict(node=n, net=net, driver=p, cell=v["cell"], len_um=round(tot, 1),
                     layers={k: round(x, 1) for k, x in sorted(L.items())}, vias=V[net],
                     vias_per_um=round(V[net] / tot, 3) if tot else None,
                     grt=v["t"], rcx=r[n]["t"], d_node=round(dn, 2), d_stage=round(dn - dp, 2)))
seen = set(); out = []
for x in sorted(rows, key=lambda x: -x["vias"]):
    out.append(x)
json.dump(out, open(sys.argv[2], "w"), indent=1)
print("%-20s %-18s %6s %5s %6s %7s %7s  %s" % ("node", "net", "len", "vias", "v/um", "d_node", "d_stage", "layers"))
for x in out[:25]:
    print("%-20s %-18s %6.1f %5d %6.3f %+7.2f %+7.2f  %s" % (x["node"][6:], x["net"][6:], x["len_um"], x["vias"], x["vias_per_um"] or 0, x["d_node"], x["d_stage"], x["layers"]))
