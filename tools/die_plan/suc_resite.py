"""QC-INT-R2-SUC: re-site SU_C representative station legs into streets (C-STREET, C-LEG405). Plan delta tool.
usage: suc_resite.py PLAN OUT_PLAN REPORT [--types a,b] [--hopmax 360]
Derives every coordinate from the type's own hard cores / outline / pins / existing legs."""
import sys, json, math, collections, argparse
import numpy as np
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_fp_floorplan as fp

GRID = 21.6
HALO = 6.0
OUT = 3.0
WIDE = 12.0   # clearance for lanes whose per-bit banks (about 34 x 20 um) sit on the leg
FTHOP = 400.0
ADD_STAGE = {"cws2"}   # one added FT station (owner-delegated extra cycle), carried through latency by the stock gen tables
CWS2_CLR = False   # 5 um and 8 um clearance leave no 5-hop route in the 34 um su8|ch gap (tried): needs an added stage or a finer street plan
WIDE_LANES = {"x_su_l0_o", "x_su_l0_p1_o", "x_su_l1_p1_o", "x_ctl_o", "x_sc_o", "x_su_l1_o"}
AVOID = {"x_su_l1_p1_i": [(0.0, 60.4, 46.0, 276.6)]}   # left margin (1,249 bit capacity) already carries cws1 516 + x_su_l1_i 438: this lane takes the 26 um bottom-row gap

def man(a, b): return abs(a[0]-b[0]) + abs(a[1]-b[1])

def boxes_of(t):
    return [fp._box(c) for c in t["hard_cores"] if c.get("origin_um") and c.get("outline_um")]

def seg_clear_matrix(P, Q, bxs, shrink=-2.0):
    """bool [len(P), len(Q)] straight segment P->Q avoids every (expanded) box. Liang-Barsky vectorised."""
    ok = np.ones((len(P), len(Q)), bool)
    ax = P[:, 0][:, None]; ay = P[:, 1][:, None]
    dx = Q[:, 0][None, :] - ax; dy = Q[:, 1][None, :] - ay
    for b in bxs:
        x0, y0, x1, y1 = b[0]-shrink*-1, b[1]+shrink, b[2]-shrink*-1+0, b[3]-shrink
        x0, y0, x1, y1 = b[0]+shrink, b[1]+shrink, b[2]-shrink, b[3]-shrink
        t0 = np.zeros_like(dx); t1 = np.ones_like(dx); dead = np.zeros(dx.shape, bool)
        for p, q in ((-dx, ax - x0), (dx, x1 - ax), (-dy, ay - y0), (dy, y1 - ay)):
            par = (p == 0)
            dead |= par & (q < 0)
            with np.errstate(divide="ignore", invalid="ignore"):
                r = np.where(par, 0.0, q / np.where(par, 1, p))
            neg = (p < 0) & ~par; pos = (p > 0) & ~par
            t0 = np.where(neg, np.maximum(t0, r), t0)
            t1 = np.where(pos, np.minimum(t1, r), t1)
        inside = (~dead) & (t0 < t1 - 1e-9)
        L = np.hypot(dx, dy) * (t1 - t0)
        ok &= ~(inside & (L > 0.5))
    return ok

def candidates(t):
    W, H = t["outline_um"]; bxs = boxes_of(t)
    xs = np.arange(GRID, W - GRID/2, GRID/1.0)
    xs = np.concatenate([[GRID], xs[xs > GRID]]) if False else xs
    ys = np.arange(GRID, H - GRID/2, GRID)
    # centre lines of the narrow street gaps between cores (x) so a leg with a wide bank can sit in the middle of a 26-35 um gap
    gx = []
    sb = sorted(bxs)
    for i, a in enumerate(sb):
        for b in sb[i+1:]:
            if 0 < b[0] - a[2] < 100 and min(a[3], b[3]) - max(a[1], b[1]) > 50:
                gx.append(round(((a[2] + b[0]) / 2) / 4.32) * 4.32)
    xs = np.unique(np.concatenate([xs, gx]))
    X, Y = np.meshgrid(xs, ys); C = np.stack([X.ravel(), Y.ravel()], 1)
    free = np.ones(len(C), bool)
    for b in bxs:
        free &= ~((C[:, 0] > b[0]-HALO) & (C[:, 0] < b[2]+HALO) & (C[:, 1] > b[1]-HALO) & (C[:, 1] < b[3]+HALO))
    return C[free], bxs

class Router:
    def __init__(self, t, hopmax):
        self.t = t; self.hopmax = hopmax
        self.C, self.bxs = candidates(t)
        n = len(self.C)
        D = np.abs(self.C[:, None, 0]-self.C[None, :, 0]) + np.abs(self.C[:, None, 1]-self.C[None, :, 1])
        clear = seg_clear_matrix(self.C, self.C, self.bxs)
        self.D = D; self.allow = (D <= 405.0) & clear
        self.cache = {}
        self.pen = np.zeros(n)
    def route(self, a, b, m, bits, prefix=(), suffix=(), hopmax=None, avoid=(), wide=False):
        """m free stations between fixed a and b (a/b are plan points). returns list of m points or None."""
        C = self.C; n = len(C); hm = hopmax or self.hopmax; D_ = self.D
        BIG = 1e18
        wv = WIDE if wide is True else (wide or 0)
        if wide:
            if wv not in self.cache:
                fw = np.ones(n, bool)
                for bq in self.bxs:
                    fw &= ~((C[:, 0] > bq[0]-wv) & (C[:, 0] < bq[2]+wv) & (C[:, 1] > bq[1]-wv) & (C[:, 1] < bq[3]+wv))
                self.cache[wv] = ((D_ <= 405.0) & seg_clear_matrix(C, C, self.bxs, -wv), fw)
            allow_w, free_w = self.cache[wv]
        sh = -2.0   # fixed pins sit on core edges: only the interior legs take the wide clearance
        Aa = seg_clear_matrix(np.array([a]), C, self.bxs, sh)[0] & (man_arr(C, a) <= hm)
        Bb = seg_clear_matrix(np.array([b]), C, self.bxs, sh)[0] & (man_arr(C, b) <= hm)
        pen = self.pen.copy()
        amask = np.ones((n, n), bool)
        for r in avoid:     # a leg may not run through this strip (segment level, not only its stations)
            amask &= seg_clear_matrix(C, C, [r], 0.0)
            Aa &= seg_clear_matrix(np.array([a]), C, [r], 0.0)[0]
            Bb &= seg_clear_matrix(np.array([b]), C, [r], 0.0)[0]
        if wide:
            pen = pen + np.where(free_w, 0.0, 1e9)
        cost = np.where(Aa, (man_arr(C, a)/100.0)**2 + pen, BIG)
        back = []
        H = np.where((allow_w if wide else self.allow) & (self.D <= hm) & amask, (self.D/100.0)**2, BIG) + pen[None, :]
        for k in range(1, m):
            tot = cost[:, None] + H
            idx = tot.argmin(0); cost = tot[idx, np.arange(n)]; back.append(idx)
        cost = np.where(Bb, cost + (man_arr(C, b)/100.0)**2, BIG)
        j = int(cost.argmin())
        if cost[j] >= BIG/2: return None
        path = [j]
        for idx in reversed(back):
            j = int(idx[j]); path.append(j)
        path.reverse()
        return [[float(C[i, 0]), float(C[i, 1])] for i in path]

def man_arr(C, p): return np.abs(C[:, 0]-p[0]) + np.abs(C[:, 1]-p[1])

def snap_edge(p, bxs):
    """a lane end inside a core box (a pin modeled at the leaf): move it to the nearest box edge, outside the 1 um shrink."""
    for b in bxs:
        if b[0]-0.5 < p[0] < b[2]+0.5 and b[1]-0.5 < p[1] < b[3]+0.5 and (b[2]-b[0])*(b[3]-b[1]) > fp.MIN_CORE_UM2:
            d = [(p[0]-b[0], (b[0]-OUT, p[1])), (b[2]-p[0], (b[2]+OUT, p[1])), (p[1]-b[1], (p[0], b[1]-OUT)), (b[3]-p[1], (p[0], b[3]+OUT))]
            return [round(v, 3) for v in min(d)[1]]
    for b in bxs:   # a pin modeled exactly on a core edge: step OUT um off the edge so the leg starts outside the box
        if b[0]-0.5 <= p[0] <= b[2]+0.5 and b[1]-0.5 <= p[1] <= b[3]+0.5 and (b[0] < p[0] < b[2] or b[1] < p[1] < b[3]):
            pass
    return p

def lane_crosses(t, pts):
    bs = boxes_of(t)
    return any(fp._inside_um(a, b, bx) >= fp.CROSS_MIN_UM for a, b in zip(pts, pts[1:]) for bx in bs
               if (bx[2]-bx[0])*(bx[3]-bx[1]) > fp.MIN_CORE_UM2)

def resite_type(t, R, hopmax, log):
    bs = R.bxs
    changed = []
    for s in t["internal_stations"]:
        pts = [q for q in [s.get("from_um"), *(s.get("regs_um") or []), s.get("to_um")] if q]
        key = (s.get("conn") or "").replace("bus:", "")
        if not lane_crosses(t, pts) and key not in AVOID: continue
        regs = s["regs_um"]; m = len(regs)
        a = snap_edge(s["from_um"], bs); b = snap_edge(s["to_um"], bs)
        new = R.route(a, b, m, s.get("bits", 1), hopmax=400.0, avoid=AVOID.get(key, ()), wide=bool(s.get("bit_sites_um") or key in WIDE_LANES))
        if new is None:
            log.append(dict(conn=s["conn"], status="NO-ROUTE")); continue
        old = [list(r) for r in regs]
        s["regs_um"] = new
        if a != s["from_um"]: s["from_um"] = a
        if b != s["to_um"]: s["to_um"] = b
        full = [a] + new + [b]
        log.append(dict(conn=s["conn"], bits=s.get("bits"), m=m, old=old, new=new, from_um=a, to_um=b,
                        max_hop=round(max(man(p, q) for p, q in zip(full, full[1:])), 1)))
    for s in t["ft_slots"]:
        regs = s["regs_um"]
        pts = list(regs)
        w, h = t["outline_um"]
        if s.get("out_face") and s.get("out_window_um"):
            pts.append(fp._face_center(s["out_face"], s["out_window_um"], w, h))
        if not lane_crosses(t, pts): continue
        m = len(regs) - 2 + (1 if s["name"] in ADD_STAGE else 0)
        new = R.route(regs[0], regs[-1], m, s["width"], hopmax=FTHOP, avoid=AVOID.get(s["name"], ()), wide=True)
        if new is None:
            log.append(dict(ft=s["name"], status="NO-ROUTE")); continue
        old = [list(r) for r in regs]
        s["regs_um"] = [regs[0]] + new + [regs[-1]]
        if s["name"] in ADD_STAGE: s["stations"] = int(s["stations"]) + 1
        full = s["regs_um"]
        log.append(dict(ft=s["name"], bits=s["width"], old=old, new=s["regs_um"],
                        max_hop=round(max(man(p, q) for p, q in zip(full, full[1:])), 1)))

def report(t):
    w = fp.street_worst(t); cr = fp.core_crossings(t)
    agg = collections.Counter()
    for nm, cn, b, d, _ in cr: agg[(nm, cn)] += b
    return dict(street=w, crossbits=sum(agg.values()))

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("plan"); ap.add_argument("out"); ap.add_argument("rep")
    ap.add_argument("--types", default="sle_su_c,slw_su_c__cl19bb38ef,slw_su_c__cl92142dac"); ap.add_argument("--hopmax", type=float, default=360)
    a = ap.parse_args()
    P = json.load(open(a.plan)); out = {}
    R = None
    for n in a.types.split(","):
        t = P["partition_types"][n]; log = []
        if R is None: R = Router(t, a.hopmax)
        before = report(t)
        resite_type(t, R, a.hopmax, log)
        after = report(t)
        out[n] = dict(before=before, after=after, lanes=log)
        print(n, "before", before["street"][:6] if before["street"] else None, before["crossbits"], "after", after["street"][:6] if after["street"] else None, after["crossbits"], flush=True)
        for l in log: print("  ", {k: v for k, v in l.items() if k not in ("old", "new")}, flush=True)
    json.dump(P, open(a.out, "w"), indent=1); json.dump(out, open(a.rep, "w"), indent=1)
