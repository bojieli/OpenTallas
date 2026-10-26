"""Diagnostic: complete-coverage (clock_phase_lp pair_set 'complete') related-pair bound for 2^D regional meshes using
legal0 arrivals; credit = early/late range at the region H-tree node; cross-region connected partitions -> landed."""
import sys, json, re, collections, itertools
T, D = sys.argv[1], sys.argv[2]
sys.path.insert(0, T)
import numpy as np
import schema as S, die_clock as DC, die_clock_mesh as DM
P = S.Plan(S.load(f"{D}/../plan.json")); M = json.load(open(f"{D}/mesh.json"))
xs, ys = np.array(M["xs"]), np.array(M["ys"]); nx, ny = len(xs), len(ys)
tb = collections.defaultdict(list)
for t in M["taps"]: tb[t["part"]].append(t["port"])
tag = lambda x, y: DM.htree_tag(int(np.argmin(abs(xs-x))), int(np.argmin(abs(ys-y))), nx, ny)
ptag = {p: tag((P.rect(p)[0]+P.rect(p)[2])/2, (P.rect(p)[1]+P.rect(p)[3])/2) for p in tb}
conn = collections.Counter()
for pr in P.ports.values():
    a, b = pr["src"]["part"], pr["dst"]["part"]
    if a in tb and b in tb and a != b: conn[tuple(sorted((a, b)))] += pr["width"]
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
    L = {p: v[0] for p, v in arr.items()}; E = {p: v[1] for p, v in arr.items()}
    for Dp in [0, 2, 3, 4, 5]:
        reg = {p: ptag[p][:1+Dp] for p in tb}
        groups = [list(tb[p]) for p in tb] + [None]
        worst = (0, None); floor = (0, None); npairs = 0
        def scan(A, B, cr):
            global worst, floor, npairs
        res_w = []; res_f = []; n = 0
        def chk(ua, ub, cr):
            la = np.array([L[u] for u in ua]); ea = np.array([E[u] for u in ua])
            lb = np.array([L[u] for u in ub]); eb = np.array([E[u] for u in ub])
            ra, rb = la-ea, lb-eb
            c = np.minimum(np.minimum(cr, ra[:, None]), rb[None, :])
            dmg = np.maximum(la[:, None]-eb[None, :], lb[None, :]-ea[:, None]) - c
            fl = (ra[:, None]+rb[None, :])/2 - c
            return dmg, fl
        landed = 0; lbits = 0; mx = -1; mf = -1; wp = None; per = []
        for p in tb:
            cr = rng.get(reg[p], 0.0) if Dp else rng["h"]
            d, f = chk(tb[p], tb[p], cr); np.fill_diagonal(d, 0); np.fill_diagonal(f, 0)
            n += len(tb[p])*(len(tb[p])-1)//2
            per.append((float(d.max()), 'intra', p))
            if d.max() > mx: mx = d.max(); wp = ("intra", p)
            mf = max(mf, f.max())
        for (a, b), w in conn.items():
            if reg[a] != reg[b]: landed += 1; lbits += w; continue
            cr = rng.get(reg[a], 0.0) if Dp else rng["h"]
            d, f = chk(tb[a], tb[b], cr); n += d.size
            per.append((float(d.max()), a, b))
            if d.max() > mx: mx = d.max(); wp = ("cross", a, b)
            mf = max(mf, f.max())
        out.setdefault(corner, {})[Dp] = dict(regions=len(set(reg.values())), pairs=n, bound_ps=round(float(mx), 2),
            uncredited_floor_ps=round(float(mf), 2), worst=wp, top=[(round(x[0],1),)+x[1:] for x in sorted(per,reverse=True)[:6]], ex_sysc=round(max(x[0] for x in per if 'sys_c' not in x[1:]),2), landed_part_pairs=landed, landed_bits=lbits,
            region_credit_ps=[round(min(rng.get(r, 0) for r in set(reg.values())), 1), round(max(rng.get(r, 0) for r in set(reg.values())), 1)] if Dp else [round(rng["h"], 1)]*2)
        print(corner, Dp, out[corner][Dp], flush=True)
json.dump(out, open(sys.argv[3], "w"), indent=1)
