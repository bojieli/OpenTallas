import collections, statistics as st, re
loc = {}; mac = []
for l in open("q0v3_loc.txt"):
    f = l.split()
    if f[0] == "#MACRO": mac.append((f[1], *map(float, f[2:]))); continue
    loc[f[0]] = (f[1], float(f[2]), float(f[3]))
A = []; drv = collections.defaultdict(list)
for l in open("q0v3_lat_TT.txt"):
    p, a, d = l.split()
    inst = p.rsplit("/", 1)[0].replace("\\", "")
    if a in ("", "NaN"): continue
    A.append((float(a), inst, d)); drv[d.rsplit("/",1)[0].replace("\\","")].append((float(a), inst))
ar = sorted(x[0] for x in A)
print("ffs", len(A), "arr min/p5/med/p95/max", [round(ar[int(q*(len(ar)-1))],1) for q in (0,.05,.5,.95,1)])
print("macros", mac)
def grp(rx):
    g = [x for x in A if re.search(rx, x[1])]
    v = sorted(x[0] for x in g)
    xs = [loc.get(x[1], (0, 0, 0))[1:] for x in g]
    return len(g), [round(v[0],1), round(st.median(v),1), round(v[-1],1)] if v else None, (round(min(p[0] for p in xs),1), round(max(p[0] for p in xs),1), round(min(p[1] for p in xs),1), round(max(p[1] for p in xs),1)) if xs else None
for rx in (r"sc_data_i", r"lmax_i", r"u_tsm", r"ident", r"x3\["):
    print(rx, grp(rx))
# leaf drivers: count, mean arrival, location
L = []
for d, v in drv.items():
    a = [x[0] for x in v]; xy = loc.get(d, ("?", 0, 0))
    L.append((round(st.mean(a),1), len(v), d, xy[0], xy[1], xy[2]))
L.sort()
print("leaf drivers", len(L)); print("earliest", L[:4]); print("latest", L[-6:])
# late leaves: which register groups
late = [x for x in A if x[0] > ar[int(.95*(len(ar)-1))]]
c = collections.Counter(re.sub(r"\[\d+\]", "[]", x[1].split(".")[-1].split("$")[0])[:30] for x in late); print("late p95 groups", c.most_common(8))
early = [x for x in A if x[0] < ar[int(.05*(len(ar)-1))]]
c = collections.Counter(re.sub(r"\[\d+\]", "[]", x[1].split(".")[-1].split("$")[0])[:30] for x in early); print("early p5 groups", c.most_common(8))
