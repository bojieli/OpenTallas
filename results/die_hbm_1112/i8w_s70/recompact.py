import json, collections, hashlib, sys, os
SRC = "/srv/opentallas-scratch2/claude/hbm-vsn-xtap-t39w/plan_t39w/cores/ot_hbm_sm_i8w_front__1391.04x233.28__smab1108_i8w8.json"
OUT = sys.argv[1]
OW, OH = 1391.04, 233.28
NW, NH = 829.44, 138.24
d = json.load(open(SRC))


def face(p):
    x, y = p["x"], p["y"]
    return "W" if x < 1 else "E" if x > OW - 1 else "S" if y < 1 else "N" if y > OH - 1 else "I"


GRID = {"M4": (0.048, 0.024), "M5": (0.048, 0.024)}


def phase_of(vals, pitch):
    c = collections.Counter(round(v % pitch, 4) for v in vals)
    return c.most_common(1)[0][0]


groups = collections.defaultdict(list)
for i, p in enumerate(d):
    f = face(p)
    if f == "I":
        continue
    groups[(f, p["layer"])].append(i)
out = [dict(p) for p in d]
margin = 2.184
for (f, lay), idx in groups.items():
    alongkey = "x" if f in "NS" else "y"
    L = NW if f in "NS" else NH
    idx.sort(key=lambda i: (d[i][alongkey], d[i]["name"]))
    if lay in GRID:
        pitch, ph = GRID[lay]
    else:
        pitch = 0.064
        ph = phase_of([d[i][alongkey] for i in idx], pitch)
    lo, hi = margin, L - margin
    n = len(idx)
    kmin = int((lo - ph) / pitch + 0.999999)
    kmax = int((hi - ph) / pitch)
    nt = kmax - kmin + 1
    assert nt >= 2 * n or lay in ("M6", "M7"), (f, lay, nt, n)
    prev = None
    for r, i in enumerate(idx):
        k = kmin + round(r * (nt - 1) / (n - 1))
        if prev is not None and k <= prev:
            k = prev + 1
        prev = k
        out[i][alongkey] = round(ph + k * pitch, 4)
    acr = {"S": 0.019, "W": 0.019, "N": round(NH - 0.019, 3), "E": round(NW - 0.019, 3)}[f]
    for i in idx:
        out[i]["y" if f in "NS" else "x"] = acr
for i, p in enumerate(d):
    if face(p) == "I":
        out[i]["x"] = round(0.024 + round((NW / 2 - 0.024) / 0.048) * 0.048, 4)
        out[i]["y"] = NH / 2
names = [p["name"] for p in out]
assert len(names) == len(set(names)) == len(d)
for p in out:
    assert 0 <= p["x"] <= NW and 0 <= p["y"] <= NH
json.dump(out, open(OUT, "w"))
print(hashlib.sha256(open(OUT, "rb").read()).hexdigest())
