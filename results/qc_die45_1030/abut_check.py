#!/usr/bin/env python3
"""DIE-QC-45 physical pin-abutment check on the materialized QC die ODB (abut_dump.py output) against plan ports.
Per plan port bit (src part/bus[k] -> dst part/bus[k]): both master pins exist, same layer, and the two pin rects in
the die frame TOUCH or overlap (gap <= 1 nm) with equal centre lines (|d| <= 1 nm) = ABUTTED.  Then a geometric scan of
every boundary pin: pins of two different instances that touch but are NOT a plan bit pair = UNPLANNED contact (short
risk).  usage: abut_check.py INSTS.json MASTERS.json PLAN.json OUT.json"""
import sys, json, collections
fi, fm, fp, fo = sys.argv[1:5]
I = json.load(open(fi))["insts"]; M = json.load(open(fm)); P = json.load(open(fp))
inst = {d["name"]: d for d in I}
EPS = 1e-3
def xf(d, r):
    w, h = M[d["master"]]["size"]; bx, by = d["bbox"][:2]; o = d["orient"]
    x0, y0, x1, y1 = r
    if o in ("MY", "R180"): x0, x1 = w - x1, w - x0
    if o in ("MX", "R180"): y0, y1 = h - y1, h - y0
    if o not in ("R0", "MX", "MY", "R180"): raise SystemExit("orient " + o)
    return (bx + x0, by + y0, bx + x1, by + y1)
pins = {}   # master -> name -> [(layer, rect)]
for m, v in M.items():
    dct = collections.defaultdict(list)
    for nm, L, *r in v["pins"]:
        dct[nm].append((L, tuple(r)))
    pins[m] = dct
def get(part, name):
    d = inst.get(part)
    if d is None: return None
    s = pins[d["master"]].get(name)
    return None if s is None else [(L, xf(d, r)) for L, r in s]
def touch(a, b):
    ax0, ay0, ax1, ay1 = a; bx0, by0, bx1, by1 = b
    gx = max(bx0 - ax1, ax0 - bx1); gy = max(by0 - ay1, ay0 - by1)
    return gx <= EPS and gy <= EPS
def aligned(a, b):
    # centre line across the shared edge: vertical-contact pins share x centre, horizontal share y centre
    cx = abs((a[0] + a[2]) - (b[0] + b[2])) / 2; cy = abs((a[1] + a[3]) - (b[1] + b[3])) / 2
    return min(cx, cy) <= EPS
cnt = collections.Counter(); ex = collections.defaultdict(list); planned = set(); kinds = collections.Counter()
for pr in P["ports"]:
    s, t = pr["src"]["part"], pr["dst"]["part"]; w = int(pr.get("width", 1))
    if s not in inst or t not in inst:
        cnt["port_bits_off_die_or_no_inst"] += w; continue
    for k in range(w):
        names = [f"{pr['src']['bus']}[{k}]", f"{pr['dst']['bus']}[{k}]"]
        if w == 1:
            a_ = get(s, names[0]) or get(s, pr["src"]["bus"]); b_ = get(t, names[1]) or get(t, pr["dst"]["bus"])
        else:
            a_ = get(s, names[0]); b_ = get(t, names[1])
        if not a_ or not b_:
            c = "missing_pin"; cnt[c] += 1; len(ex[c]) < 8 and ex[c].append([pr["id"], k, bool(a_), bool(b_)]); continue
        ok = None; why = "not_touching"
        for La, ra in a_:
            for Lb, rb in b_:
                if touch(ra, rb):
                    if La != Lb: why = "layer_mismatch"; continue
                    if not aligned(ra, rb): why = "touch_misaligned"; continue
                    ok = (La, ra, rb)
        if ok:
            cnt["abutted"] += 1; kinds[pr["kind"]] += 1
            planned.add((s, a_[0][1][0], a_[0][1][1], t)); planned.add((t, b_[0][1][0], b_[0][1][1], s))
        else:
            cnt[why] += 1
            if len(ex[why]) < 8: ex[why].append([pr["id"], k, a_[:1], b_[:1]])
# geometric scan for unplanned contacts between instances (boundary pins only)
grid = collections.defaultdict(list)
for d in I:
    bb = d["bbox"]
    for nm, s in pins[d["master"]].items():
        for L, r in s:
            R = xf(d, r)
            if min(R[0] - bb[0], bb[2] - R[2], R[1] - bb[1], bb[3] - R[3]) > EPS: continue   # not on the boundary
            grid[(L, round((R[0] + R[2]) / 2, 2), round((R[1] + R[3]) / 2, 0) // 1)].append((d["name"], nm, R))
pairs = set()
unpl = 0; unex = []
by_layer = collections.defaultdict(list)
for (L, cx, cy), v in grid.items():
    pass
# index boundary pins per layer by rounded centre x and y for touch search
idx = collections.defaultdict(list)
for key, v in grid.items():
    for e in v: idx[(key[0], round((e[2][0] + e[2][2]) / 2, 3))].append(e); idx[(key[0], "y", round((e[2][1] + e[2][3]) / 2, 3))].append(e)
touch_pairs = 0
seen = set()
for k, v in idx.items():
    if len(v) < 2: continue
    v.sort(key=lambda e: (e[2][0], e[2][1]))
    for i in range(len(v)):
        for j in range(i + 1, min(len(v), i + 6)):
            a, b = v[i], v[j]
            if a[0] == b[0] or not touch(a[2], b[2]): continue
            key2 = tuple(sorted([(a[0], a[1]), (b[0], b[1])]))
            if key2 in seen: continue
            seen.add(key2); touch_pairs += 1
plan_names = set()
for pr in P["ports"]:
    s, t = pr["src"]["part"], pr["dst"]["part"]; w = int(pr.get("width", 1))
    for k in range(w):
        a = (s, f"{pr['src']['bus']}[{k}]" if w > 1 else pr["src"]["bus"]); b = (t, f"{pr['dst']['bus']}[{k}]" if w > 1 else pr["dst"]["bus"])
        plan_names.add(tuple(sorted([a, b])))
        if w == 1: plan_names.add(tuple(sorted([(s, f"{pr['src']['bus']}[0]"), (t, f"{pr['dst']['bus']}[0]")])))
unplanned = [p for p in seen if p not in plan_names]
r = dict(plan=fp, ports=len(P["ports"]), port_bits=sum(int(p.get("width", 1)) for p in P["ports"]), verdicts=dict(cnt),
         abutted_by_kind=dict(kinds), examples=dict(ex), geometric_touch_pairs=touch_pairs, unplanned_touch_pairs=len(unplanned),
         unplanned_examples=sorted(unplanned)[:10])
json.dump(r, open(fo, "w"), indent=1); print(json.dumps({k: v for k, v in r.items() if k != "examples"}, indent=1))
