"""DIE-HEAD: make a {part: region} map box-clean for clock_landings (centre-in-box: each region box = bbox of its partitions
must hold exactly its own partition centres). A region R whose box holds a foreign centre c is SPLIT by an axis cut through
c (x or y, the cut that keeps more of R's internal port bits); repeat until clean. Never merges (a merge would put a
large-|d| feed hop inside a region).  usage: box_fix.py PLAN MAP_IN MAP_OUT"""
import json, sys, collections
plan = json.load(open(sys.argv[1])); M = json.load(open(sys.argv[2])); m = dict(M["part_region"])
T = plan["partition_types"]; B = {}
for p in plan["partitions"]:
    w, h = T[p["type"]]["outline_um"]
    if p.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"):
        w, h = h, w
    x, y = p["origin_um"]; B[p["name"]] = (x, y, x + w, y + h)
cen = {n: ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2) for n, b in B.items()}
bits = collections.Counter()
for pr in plan["ports"]:
    a, b = pr["src"]["part"], pr["dst"]["part"]
    if a in B and b in B:
        bits[tuple(sorted((a, b)))] += int(pr["width"])
log = []
for it in range(500):
    regs = collections.defaultdict(list)
    for n, r in m.items():
        regs[r].append(n)
    box = {r: (min(B[n][0] for n in ns), min(B[n][1] for n in ns), max(B[n][2] for n in ns), max(B[n][3] for n in ns)) for r, ns in regs.items()}
    bad = None
    for n, c in cen.items():
        for r, b in box.items():
            if r != m[n] and b[0] <= c[0] < b[2] and b[1] <= c[1] < b[3]:
                bad = (r, n); break
        if bad:
            break
    if not bad:
        break
    r, n = bad
    c = cen[n]; best = None
    for ax in (0, 1):
        lo = [q for q in regs[r] if cen[q][ax] < c[ax]]; hi = [q for q in regs[r] if cen[q][ax] >= c[ax]]
        if not lo or not hi:
            continue
        sl, sh = set(lo), set(hi)
        cut = sum(w for (a, b), w in bits.items() if (a in sl and b in sh) or (a in sh and b in sl))
        if best is None or cut < best[0]:
            best = (cut, ax, lo, hi)
    if best is None:
        raise SystemExit(f"cannot split {r} around {n}")
    for q in best[3]:
        m[q] = f"{r}{'xy'[best[1]]}"
    log.append(dict(region=r, foreign=n, axis="xy"[best[1]], cut_bits=best[0], moved=len(best[3])))
M["part_region"] = m; M["box_fix"] = log
json.dump(M, open(sys.argv[3], "w"), indent=1)
print(len(set(m.values())), "regions after", len(log), "splits:", log)
