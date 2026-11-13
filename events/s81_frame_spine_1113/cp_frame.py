"""cp_why.py TOOLS_DIE_PLAN_DIR <core_place args...> : core_place.py with a seed-legality report (why a seed spot is illegal)."""
import sys
sys.path.insert(0, sys.argv[1])
import core_place as CP
_orig = CP.apply_seed
def apply_seed(M, seed, log):
    want = {}
    for inst, v in seed.items():
        if inst in M.idx and "origin_um" in v:
            i = M.idx[inst]; k = M.cid[i]
            if k not in want:
                ox, oy = M.coff[i]
                want[k] = (CP.snap(v["origin_um"][0] - ox), CP.snap(v["origin_um"][1] - oy), inst)
    n = _orig(M, seed, log)
    for k, (x, y, inst) in want.items():
        cx, cy = M.cpos[k]
        if abs(cx - x) > 1e-3 or abs(cy - y) > 1e-3:
            old = tuple(M.cpos[k]); M.cpos[k] = (x, y)
            w = M.why(k, x, y)
            M.cpos[k] = old
            log("  SEED-MOVED %s seed (%.2f, %.2f) -> (%.2f, %.2f) why %s" % (inst, x, y, cx, cy, w))
    return n
CP.apply_seed = apply_seed
# frame family: the base plan's pair halves (0.54 um) and bf col3_c / half (0.89 um) outlines overlap by construction;
# only overlaps wider than 1 um in both axes count
def overlaps(M):
    out = 0
    for i in range(M.n):
        xi, yi = M.core_origin(i)
        for j in range(i + 1, M.n):
            xj, yj = M.core_origin(j)
            ox = min(xi + M.dim[i, 0], xj + M.dim[j, 0]) - max(xi, xj)
            oy = min(yi + M.dim[i, 1], yj + M.dim[j, 1]) - max(yi, yj)
            if ox > 1.0 and oy > 1.0:
                out += 1
    return out
CP.overlaps = overlaps
# ROM columns are abutted at 3.0 um (pitch 41.04, x on the 0.108 grid the element origins already use), so that a ROM and
# the next-but-one core are >= 43.2 apart; seeds therefore snap to 0.108, not to 4.32
CP.snap = lambda v: round(round(v / 0.108) * 0.108, 4)
sys.exit(CP.main(sys.argv[2:]))
