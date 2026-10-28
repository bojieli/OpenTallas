# HBM-CORES-REBAL-3: estimate for option B. Start from an RTLMP macro placement (2_2 odb), move only the macros that
# overlap a planned island rect, by the smallest shift (x or y, multiples of 0.054/0.27 grid) that clears every island
# rect by >= margin and keeps macro+halo clear of every other macro+halo and inside the fence. Prints a plan.
import json, sys, itertools
import odb
odbf, planf, cfgf, outf = sys.argv[1:5]
db = odb.dbDatabase.create(); odb.read_db(db, odbf); b = db.getChip().getBlock(); u = b.getDbUnitsPerMicron()
cfg = {l.split("=")[0].split()[-1]: l.split("=", 1)[1].strip() for l in open(cfgf) if l.startswith("export") and "=" in l}
halo = float(cfg.get("MACRO_PLACE_HALO", "4.32").split()[0])
core = b.getCoreArea()
fx0 = float(cfg.get("RTLMP_FENCE_LX", core.xMin() / u)); fy0 = float(cfg.get("RTLMP_FENCE_LY", core.yMin() / u))
fx1 = float(cfg.get("RTLMP_FENCE_UX", core.xMax() / u)); fy1 = float(cfg.get("RTLMP_FENCE_UY", core.yMax() / u))
isl = sorted({tuple(c["rect_um"]) for c in json.load(open(planf))["cells"]})
M = []
for i in b.getInsts():
    if i.getMaster().isBlock():
        bb = i.getBBox(); M.append([i.getName(), bb.xMin() / u, bb.yMin() / u, bb.xMax() / u, bb.yMax() / u, i.getOrient()])
def ov(a, r, m=0.0):
    return a[0] < r[2] + m and a[2] > r[0] - m and a[1] < r[3] + m and a[3] > r[1] - m
def ok(k, r, margin):
    if r[0] < fx0 - 1e-6 or r[1] < fy0 - 1e-6 or r[2] > fx1 + 1e-6 or r[3] > fy1 + 1e-6: return False
    if any(ov(r, s, margin) for s in isl): return False
    for j, o in enumerate(M):
        if j != k and ov(r, o[1:5], 2 * halo - 1e-6): return False
    return True
moved = []; fail = []
for margin in (halo, 0.0):
    pass
for k, m in enumerate(M):
    r = m[1:5]
    if not any(ov(r, s) for s in isl): continue
    best = None
    for margin in (halo, 0.0):
        for step in range(1, 4000):
            for dx, dy in ((0.054 * step, 0), (-0.054 * step, 0), (0, 0.27 * (step // 5)), (0, -0.27 * (step // 5))):
                if dx == dy == 0: continue
                c = [r[0] + dx, r[1] + dy, r[2] + dx, r[3] + dy]
                if ok(k, c, margin):
                    best = (abs(dx) + abs(dy), dx, dy, margin, c); break
            if best: break
        if best: break
    if not best:  # 2D: nearest valid origin on a 0.54 x 0.27*4 grid over the fence
        w_, h_ = r[2] - r[0], r[3] - r[1]; cands = []
        x = fx0
        while x + w_ <= fx1 + 1e-6:
            y = fy0
            while y + h_ <= fy1 + 1e-6:
                cands.append((abs(x - r[0]) + abs(y - r[1]), x, y)); y += 1.08
            x += 0.54
        for d, x, y in sorted(cands):
            c = [x, y, x + w_, y + h_]
            if ok(k, c, halo): best = (d, x - r[0], y - r[1], halo, c); break
    if best:
        m[1:5] = best[4]; moved.append((m[0], round(best[1], 3), round(best[2], 3), best[3]))
    else:
        fail.append(m[0])
left = sum(1 for m in M for s in isl if ov(m[1:5], s))
json.dump({"odb": odbf, "fence": [fx0, fy0, fx1, fy1], "halo": halo, "islands": len(isl), "macros": len(M),
           "moved": moved, "fail": fail, "overlaps_left": left,
           "macro_placement": [{"inst": m[0], "xy_um": [round(m[1], 3), round(m[2], 3)], "orient": str(m[5])} for m in M]},
          open(outf, "w"), indent=1)
print("LEGAL", odbf.split("/")[-4] if "/results/" in odbf else odbf, "macros", len(M), "islands", len(isl),
      "moved", len(moved), "maxshift_um", max([abs(a) + abs(c) for _, a, c, _ in moved] or [0]),
      "margin0", sum(1 for x in moved if x[3] == 0.0), "fail", len(fail), "overlaps_left", left)
