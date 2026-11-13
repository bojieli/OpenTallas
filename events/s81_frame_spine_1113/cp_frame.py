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
            if w.startswith("rule8"):
                w += " rects %s" % [r for r in M.FR if not (r[2] <= x or r[0] >= x + M.cbb[k, 2] or r[3] <= y or r[1] >= y + M.cbb[k, 3])][:3]
            if w.startswith("rule7"):
                w += " points %s" % [(round(float(a_), 1), round(float(b_), 1)) for (a_, b_), h_ in zip(M.FP, M.FPH) if x - h_ < a_ < x + M.cbb[k, 2] + h_ and y - h_ < b_ < y + M.cbb[k, 3] + h_][:6]
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
# seeds are on the 8.64 lattice (G0C hard_cores); core_place snaps to 4.32, which keeps them
# Link limits (family override, reported, never silent): core_place keeps every direct link <= max(base, 405 um).
# (a) 'bus' links (type window -> core pin) are relayed in the frame soft logic (dsfd_rly_masters); the E pair moves
#     ~270 um east into the former empty strip by design, so these grow; the kit r2r check judges them.
# (b) the two bf_col3_c cores share 4 bits over the front-roots core; opening its 25 um pin slots to 43.2 adds 26 um.
_il = CP.TypeModel.init_limits
def init_limits(self):
    _il(self)
    n = 0
    for q in range(len(self.L)):
        a, b, bits, kind = self.L[q][:4]
        mods = [self.C[e[0]]["module"] for e in (a, b) if e[0] is not None]
        if kind == "bus" or (len(mods) == 2 and all(m == "ot_v41_bf_col3_c" for m in mods)):
            self.maxlen[q] = max(self.maxlen[q], 1e9 if kind == "bus" else self.maxlen[q] + 30.0); n += 1
    print("  FRAME-OVERRIDE: %d bus / col3 links exempt from the base-length limit" % n, flush=True)
CP.TypeModel.init_limits = init_limits
sys.exit(CP.main(sys.argv[2:]))
