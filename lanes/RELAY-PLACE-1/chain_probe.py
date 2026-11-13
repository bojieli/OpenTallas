"""probe: classify relay_metrics chains of a geom.tsv dump. usage: chain_probe.py GEOM_RULES_DIR geom.tsv"""
import sys, re, collections
sys.path.insert(0, sys.argv[1])
import geom_rules as G

D = G.Design(sys.argv[2])
src = {}
for cid, c in D.cells.items():
    if c[0] != "S":
        continue
    ins = [n for n, isc in D.cell_in.get(cid, []) if not isc]
    if len(ins) != 1:
        continue
    cur, depth, prev = ins[0], 0, None
    while depth <= G.PINREG_DEPTH:
        dr = D.nets[cur][1]
        if not dr or dr[0] != "i":
            break
        k = D.kind(dr[1])
        if k == "S":
            prev = dr[1]
            break
        if k != "B" or not D.cell_in.get(dr[1]):
            break
        cur = D.cell_in[dr[1]][0][0]
        depth += 1
    if prev is not None and prev != cid:
        src[cid] = prev
has = set(src.values())
heads = [c for c in src if c not in has]
cls = collections.Counter(); ex = {}
status = D.extra.get("status", {})
def kindof(nm):
    for k, r in (("ft", r"u_ft_|u_ft\d|u_fx"), ("rst_relay", r"u_srl|u_rrl|u_rst"), ("cland", r"u_cland"),
                 ("bin/bout", r"u_bin_|u_bout_"), ("relay_y", r"u_y_"), ("station", r"stn|station|u_st_")):
        if re.search(k and r, nm):
            return k
    return "other"
hopsall = []
for t in heads:
    chain, cur, seen = [t], t, {t}
    while cur in src and src[cur] not in seen and len(chain) < 4096:
        cur = src[cur]; chain.append(cur); seen.add(cur)
    if len(chain) < 3:
        continue
    pts = [G.ctr(D.cells[c]) for c in chain]
    hops = [abs(a[0]-b[0]) + abs(a[1]-b[1]) for a, b in zip(pts, pts[1:])]
    mh = max(hops)
    if mh <= G.R2R_MAX:
        continue
    i = hops.index(mh)
    a, b = D.cells[chain[i]][6], D.cells[chain[i+1]][6]
    k = kindof(a) + ">" + kindof(b)
    cls[k] += 1
    hopsall.append(mh)
    if k not in ex or mh > ex[k][0]:
        ex[k] = (round(mh), b, a, len(chain))
RELAY = {"ft", "rst_relay", "relay_y", "station"}
nrel = sum(n for k, n in cls.items() if set(k.split(">")) & RELAY)
nft = sum(n for k, n in cls.items() if "ft" in k.split(">"))
mrel = max([ex[k][0] for k in cls if set(k.split(">")) & RELAY] or [0])
print("SUMMARY collapsed %d relay %d ft %d other %d maxhop %d maxrelayhop %d" % (sum(cls.values()), nrel, nft, sum(cls.values()) - nrel, round(max(hopsall)) if hopsall else 0, mrel))
for k, n in cls.most_common():
    print(n, k, ex[k])
