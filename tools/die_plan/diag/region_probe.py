"""Diagnostic: re-judge the legal0 single-mesh KV clock arrivals as if the H-tree were cut into 2^D regions
(credit = early/late range at the region's H-tree node; cross-region seam pairs become LANDED crossings)."""
import sys, json, re, collections, math
T, D = sys.argv[1], sys.argv[2]
sys.path.insert(0, T)
import numpy as np
import schema as S, die_clock as DC, die_clock_mesh as DM
P = S.Plan(S.load(f"{D}/../plan.json"))
M = json.load(open(f"{D}/mesh.json"))
xs, ys = np.array(M["xs"]), np.array(M["ys"]); nx, ny = len(xs), len(ys)
tb = collections.defaultdict(list)
for t in M["taps"]:
    tb[t["part"]].append(dict(port=t["port"], part=t["part"], xy=t["xy"]))
seam = DC.seam_pairs(P, tb)                     # {(a,b): bits}
intra = DC.intra_pairs(tb, float(P.budgets.get("tap_pitch_um", 400.0)))
def tag_xy(x, y):
    return DM.htree_tag(int(np.argmin(abs(xs - x))), int(np.argmin(abs(ys - y))), nx, ny)
tagof = {t["port"]: tag_xy(*t["foot"]) for t in M["taps"]}
partof = {t["port"]: t["part"] for t in M["taps"]}
ptag = {}
for p in tb:
    r = P.rect(p); ptag[p] = tag_xy((r[0]+r[2])/2, (r[1]+r[3])/2)
out = {}
for corner in ["TT", "FF"]:
    N = {}
    for l in open(f"{D}/tree_{corner}.txt"):
        f = l.split()
        if len(f) >= 4: N[f[1]] = (float(f[2]), float(f[3]))
    rng = {"h": N["ckm_n0"][0]-N["ckm_n0"][1]}
    for k, (a, b) in N.items():
        m = re.match(r"ckm_n\d+_(h[01]*)$", k)
        if m: rng[m.group(1)] = a-b
    arr = {}
    for l in open(f"{D}/taps_{corner}.txt"):
        f = l.split(); arr[f[1]] = (float(f[2]), float(f[3]))
    def cred(tag):
        while tag not in rng and len(tag) > 1: tag = tag[:-1]
        return rng.get(tag, 0.0)
    res = {}
    for Dp in [0, 1, 2, 3, 4, 5, 6]:
        reg = {p: ptag[partof[p]][:1+Dp] for p in arr}
        def dmg(a, b, c):
            return DC.pair_clock_damage(arr[a][0], arr[a][1], arr[b][0], arr[b][1], c)["max_damage_ps"]
        # credit: common H-tree prefix of the two taps' feeding tags, limited to the region node (mesh below it)
        def pair(a, b):
            ta, tb_ = tagof[a], tagof[b]; k = 0
            while k < min(len(ta), len(tb_)) and ta[k] == tb_[k]: k += 1
            k = min(k, 1+Dp)       # inside a region the mesh shorts drivers: only credit down to region root
            return dmg(a, b, cred(ta[:k]) if k > 1 else rng["h"])
        rel = [(pair(a, b), a, b) for (a, b, _) in seam if reg[a] == reg[b]] + [(pair(a, b), a, b) for a, b, _ in intra]
        landed = {k: v for k, v in seam.items() if reg[k[0]] != reg[k[1]]}
        lports = {k[2] for k in landed}
        lparts = {(partof[a], partof[b]) for a, b, _ in landed}
        vals = sorted(v for v, _, _ in rel)
        w = max(rel)
        res[Dp] = dict(regions=len(set(reg.values())), related_max=round(w[0], 2), p99=round(vals[int(.99*len(vals))], 2),
                       over80=sum(v > 80 for v in vals), worst=[w[1], w[2]], landed_tap_pairs=len(landed),
                       landed_bits=sum(landed.values()), landed_ports=len(lports), ports_total=len({k[2] for k in seam}), landed_part_pairs=len(lparts),
                       region_node_range_ps=[round(min(cred(t) for t in set(reg.values())), 1), round(max(cred(t) for t in set(reg.values())), 1)] if Dp else [rng["h"]]*2)
    out[corner] = res
json.dump(out, open(sys.argv[3], "w"), indent=1)
for c, r in out.items():
    for Dp, v in r.items(): print(c, Dp, {k: v[k] for k in v if k != "worst"}, v["worst"])
