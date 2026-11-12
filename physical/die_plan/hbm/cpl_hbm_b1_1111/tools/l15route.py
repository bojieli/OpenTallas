"""CPL-HBM-B1 L15_o station re-route (bank sum_out/fault -> W face) out of the bank-row/idx-row street.
Each row: bank pin (sum_out = E-face pin centroid, fault = S-face centroid of the CAPTURED pair, from the pins file)
-> horizontal at a per-row y over its own bank row (upper layers) -> W channel -> its own anchor in the L15_o window.
Registers: depth = row depth + EXTRA, sited by DP on free points of that path (max hop minimised, every hop <= 405 L1).
usage: l15route.py TYPE_IN.json TYPE_OUT.json PLANDIR EXTRA [BUS]"""
import json, sys, re, math, gzip, os
tin, tout, pdir, extra = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]); BUS = sys.argv[5] if len(sys.argv) > 5 else "L15_o"
T = json.load(open(tin)); W, H = T["outline_um"]; R = 405.0
boxes = {h["inst"]: (h["origin_um"][0], h["origin_um"][1], h["origin_um"][0] + h["outline_um"][0], h["origin_um"][1] + h["outline_um"][1]) for h in T["hard_cores"]}
def free(p, m=1.5):
    if not (2.0 < p[0] < W - 2.0 and 2.0 < p[1] < H - 2.0): return False
    return not any(b[0] - m < p[0] < b[2] + m and b[1] - m < p[1] < b[3] + m for b in boxes.values())
def pins_of(h):
    f = h["pins_file"]
    for d in [pdir, os.path.join(pdir, "..")]:
        if os.path.exists(os.path.join(d, f)): return json.load(open(os.path.join(d, f)))
    raise SystemExit("no pins " + f)
bank = {}
for h in T["hard_cores"]:
    m = re.search(r"bank128_(pair\d+)$", h["inst"])
    if m:
        pl = pins_of(h); o = h.get("orient", "R0"); w, hh = h["outline_um"]
        def pt(x, y): return (h["origin_um"][0] + (w - x if o in ("MY", "R180") else x), h["origin_um"][1] + (hh - y if o in ("MX", "R180") else y))
        g = {}
        for bn in ("sum_out", "fault"):
            ps = [pt(p["x"], p["y"]) for p in pl if p["name"].split("[")[0] == bn]
            g[bn] = (sum(p[0] for p in ps) / len(ps), sum(p[1] for p in ps) / len(ps), min(p[1] for p in ps), max(p[1] for p in ps))
        bank[m.group(1)] = (boxes[h["inst"]], g)
win = next(b["window_um"] for b in T["buses"] if b["name"] == BUS)
rows = [s for s in T["internal_stations"] if s.get("conn") == "bus:" + BUS]
# bank rows by y
ys = sorted({round(b[0][1]) for b in bank.values()})
rowsets = []
for pn, (bx, g) in sorted(bank.items(), key=lambda kv: (kv[1][0][1], kv[1][0][0])):
    if rowsets and abs(bx[1] - rowsets[-1][0]) < 60: rowsets[-1][1].append(pn)
    else: rowsets.append([bx[1], [pn]])
row_of = {pn: i for i, (_, l) in enumerate(rowsets) for pn in l}
# channel x per bank row: midway between W face and its leftmost bank
chx = {i: max(4.32, min(bank[p][0][0] for p in l) / 2) for i, (_, l) in enumerate(rowsets)}
# anchors: rows sorted by (bank row, x); spread over the window, in bank-row order (lower bank rows low)
order = sorted(rows, key=lambda s: (row_of[re.search(r"(pair\d+)", s["capture"]).group(1)], bank[re.search(r"(pair\d+)", s["capture"]).group(1)][0][0], s["bits"]))
nb = sum(s["bits"] for s in order); acc = 0; anchor = {}
for s in order:
    anchor[id(s)] = round(win[0] + (win[1] - win[0]) * (acc + s["bits"] / 2) / nb, 3); acc += s["bits"]
# per-row lane y over its bank row: spread over the pin span of the row's banks, in x order
lane = {}
for i, (_, l) in enumerate(rowsets):
    rs = [s for s in order if row_of[re.search(r"(pair\d+)", s["capture"]).group(1)] == i]
    y0 = min(bank[p][0][1] for p in l) + 20; y1 = max(bank[p][0][3] for p in l) - 20
    for k, s in enumerate(rs): lane[id(s)] = y0 + (y1 - y0) * (k + 0.5) / len(rs)
def path_pts(s):
    pn = re.search(r"(pair\d+)", s["capture"]).group(1); bx, g = bank[pn]; kind = "fault" if s["capture"].endswith("fault") else "sum_out"
    px, py = g[kind][0], g[kind][1]
    yl = lane[id(s)]; xc = chx[row_of[pn]]; ya = anchor[id(s)]
    if kind == "sum_out": start = (px + 2.16, yl)       # E-face pin band (pins span the face), leave at the lane y
    else: start = (px, py - 2.16)
    corners = [start, (xc, start[1]), (xc, ya), (0.0, ya)]
    pts = []
    for a, b in zip(corners, corners[1:]):
        n = max(1, int(math.ceil((abs(a[0] - b[0]) + abs(a[1] - b[1])) / 4.32)))
        for k in range(n): pts.append((a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n))
    pts.append(corners[-1])
    return pts, (px, py)
L1 = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])
CAP = int(sys.argv[6]) if len(sys.argv) > 6 else 8
nused = {}
def solve(pts, pin, n):
    face = pts[-1]; seq = pts[::-1]
    cand = [i for i, p in enumerate(seq) if free(p)]
    layers = [{i: (L1(face, seq[i]), None) for i in cand if L1(face, seq[i]) <= R}]
    for k in range(1, n):
        nxt = {}; prev = layers[-1]
        for j in cand:
            bj = None
            for i, (v, _) in prev.items():
                if i >= j: continue
                d = L1(seq[i], seq[j])
                if d > R: continue
                c = max(v, d)
                if bj is None or c < bj[0]: bj = (c, i)
            if bj: nxt[j] = bj
        layers.append(nxt)
    fin = [(max(v, L1(seq[j], pin)), j) for j, (v, _) in layers[-1].items() if L1(seq[j], pin) <= R]
    if not fin: return None
    c, j = min(fin); sel = [j]
    for k in range(n - 1, 0, -1): j = layers[k][j][1]; sel.append(j)
    return c, [[round(seq[i][0], 3), round(seq[i][1], 3)] for i in reversed(sel)]
bad = []
for s in rows:
    pts, pin = path_pts(s); n0 = len(s["regs_um"]) + extra
    for n in range(n0, max(n0, CAP) + 1):
        res = solve(pts, pin, n)
        if res: break
    if not res: bad.append((s["capture"][-24:], n0)); continue
    c, regs = res; nused[s["capture"][-28:]] = (n0 - extra, n)
    s["from_um"] = [0.0, anchor[id(s)]]; s["regs_um"] = regs; s["to_um"] = [round(pin[0], 3), round(pin[1], 3)]
    s["note"] = (s.get("note", "") + f" | CPL-HBM-B1 L15 re-route 1112: lane y {lane[id(s)]:.1f}, anchor {anchor[id(s)]:.1f} in window, plan regs {n0 - extra} -> {n} (bound depth {CAP}), max hop {c:.0f}").lstrip(" |")
print(json.dumps(dict(rows=len(rows), bad=bad, depth=nused, rowsets=[[round(y), l] for y, l in rowsets], chx=chx)))
json.dump(T, open(tout, "w"), indent=1)
