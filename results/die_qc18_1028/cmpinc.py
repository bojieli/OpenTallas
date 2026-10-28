# DIE-QC-18: per-sink arrival change between two measured runs, split by whether an ECO-rebuilt leg is above the sink
import json, re, sys
built, newb, A, B = sys.argv[1:5]
Bj = json.load(open(built)); Nj = json.load(open(newb))
def legs(d):
    out = {}
    def w(nd, key, path):
        if nd["kind"] != "merge":
            out[nd["name"].replace("\\", "")] = path; return
        for i, (k, lg) in enumerate(zip(nd["kids"], nd["legs"])):
            kk = "%s.%d" % (key, i); w(k, kk, path + [(kk, tuple(map(tuple, lg["pts"])))])
    w(d["tree"], "T", [("R", tuple(map(tuple, d["root_leg"])))]); return out
lb, ln = legs(Bj), legs(Nj)
aff = {s: any(abs(p[0]-q[0]) > 5e-4 or abs(p[1]-q[1]) > 5e-4 for (k1, a), (k2, b) in zip(lb[s], ln[s]) for p, q in ([(0,0),(1,1)] if len(a)!=len(b) else zip(a, b))) for s in lb}
def rd(f):
    R = {}
    for l in open(f):
        p = l.split()
        if p and p[0] == "S":
            m = re.search(r"(a0cl\d+)$", p[3]); i = p[1].rsplit("/", 1)[0].replace("\\", "")
            key = m.group(1) if m else i
            R.setdefault(key, {})[p[1]] = float(p[4])
    return R
ra, rb = rd(A), rd(B)
st = {True: [], False: []}
for s in lb:
    if s not in ra: continue
    d = [abs(rb[s][p] - ra[s][p]) for p in ra[s] if p in rb[s]]
    st[aff[s]].append(max(d))
for k in (False, True):
    v = st[k]; print("affected" if k else "unaffected", len(v), "sinks; max |d| %.3f ps" % max(v) if v else "")
