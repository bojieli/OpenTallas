"""B3 capacity proof: soft regions (contents with a box, not hard) grouped into connected components of overlapping
boxes; free = union(boxes) minus union(all hard cores of the partition, track offset applied); need
sum(cells)*A_CELL <= UMAX * free.  A_CELL = 0.20 um2/cell (measured 0.122-0.161 pure-logic synth on 4 HBM cores, +25%)."""
import json, sys, collections
A_CELL, UMAX = float(sys.argv[2]) if len(sys.argv) > 2 else 0.20, 0.65
d = json.load(open(sys.argv[1])); T = d["partition_types"]
used = sorted({p["type"] for p in d["partitions"]})
def R(c):
    x, y = c["origin_um"]; w, h = c["outline_um"]; dx, dy = c.get("track_offset_um", [0, 0])
    return (x + dx, y + dy, x + dx + w, y + dy + h)
def ov(a, b): return min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])
def own(s, h): return h == s or h.startswith(s + "_") or h.startswith(s + ".")
def area_union_minus(boxes, holes):
    xs = sorted({v for b in boxes + holes for v in (b[0], b[2])}); ys = sorted({v for b in boxes + holes for v in (b[1], b[3])})
    tot = 0.0
    for i in range(len(xs) - 1):
        cx = (xs[i] + xs[i + 1]) / 2
        bi = [(b[1], b[3]) for b in boxes if b[0] < cx < b[2]]
        if not bi: continue
        hi = [(b[1], b[3]) for b in holes if b[0] < cx < b[2]]
        for j in range(len(ys) - 1):
            cy = (ys[j] + ys[j + 1]) / 2
            if any(a < cy < b for a, b in bi) and not any(a < cy < b for a, b in hi):
                tot += (xs[i + 1] - xs[i]) * (ys[j + 1] - ys[j])
    return tot
worst = []; nfail = 0; ncomp = 0; centre_in_hard = []
for tn in used:
    t = T[tn]
    hc = [(c["inst"], R(c)) for c in t.get("hard_cores", []) if "origin_um" in c]
    hn = {n for n, _ in hc}
    soft = [(c["inst"], R(c), int(c.get("cells", 0) or 0)) for c in t.get("contents", [])
            if "origin_um" in c and "outline_um" in c and c["inst"] not in hn and not c.get("lef")]
    for n, r, _ in soft:
        cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
        hit = [h for h, b in hc if b[0] < cx < b[2] and b[1] < cy < b[3]]
        if hit: centre_in_hard.append((tn, n, hit[0]))
    # components
    par = list(range(len(soft)))
    def f(i):
        while par[i] != i: par[i] = par[par[i]]; i = par[i]
        return i
    for i in range(len(soft)):
        for j in range(i + 1, len(soft)):
            if ov(soft[i][1], soft[j][1]): par[f(i)] = f(j)
    comps = collections.defaultdict(list)
    for i in range(len(soft)): comps[f(i)].append(soft[i])
    for mem in comps.values():
        boxes = [m[1] for m in mem]
        holes = [b for h, b in hc if any(ov(b, x) for x in boxes)]
        free = area_union_minus(boxes, holes)
        need = sum(m[2] for m in mem) * A_CELL
        u = need / free if free > 0 else float("inf")
        ncomp += 1
        if u > UMAX: nfail += 1
        worst.append((u, tn, len(mem), [m[0] for m in mem][:4], round(free), round(need)))
worst.sort(reverse=True)
print(f"A_CELL {A_CELL} UMAX {UMAX}: components {ncomp}, over {UMAX}: {nfail}")
for w in worst[:25]: print(f"  u={w[0]:.3f} {w[1]} n={w[2]} {w[3]} free={w[4]} need={w[5]}")
print("soft box centre inside a hard core:", len(centre_in_hard), centre_in_hard[:12])
