"""2-D finite-volume Laplace field solver for per-unit-length wire capacitance (CLOCK-128-R6 extraction lane).

Cross-section in (x, y) um, homogeneous dielectric eps_r, conductors = axis-aligned rectangles (+ optional infinite
ground planes as y-limits), outer boundary = zero-flux (Neumann).  Nonuniform tensor grid, fine (h_fine) around
conductors.  Returns per-unit-length capacitances in fF/um.
"""
import numpy as np

EPS0 = 8.8541878e-3          # fF/um


def _lines(feat, lo, hi, h_fine, grow=1.25, h_max=0.08, pad=0.06):
    """grid lines on [lo, hi]: every feature coordinate, h_fine within `pad` of a feature, geometric growth beyond"""
    feat = sorted(set([lo, hi] + [f for f in feat if lo <= f <= hi]))
    pts = set(feat)
    for a, b in zip(feat[:-1], feat[1:]):
        L = b - a
        if L <= 1e-12:
            continue
        # walk from both ends with growing steps, meet in the middle
        left, right = [a], [b]
        h = h_fine
        x = a
        while True:
            pa = (x - a) < pad
            step = h_fine if pa else min(h_max, h)
            if x + step >= (a + b) / 2:
                break
            x += step
            left.append(x)
            if not pa:
                h *= grow
        h = h_fine
        x = b
        while True:
            pb = (b - x) < pad
            step = h_fine if pb else min(h_max, h)
            if x - step <= (a + b) / 2:
                break
            x -= step
            right.append(x)
            if not pb:
                h *= grow
        pts.update(left)
        pts.update(right)
    xs = np.array(sorted(pts))
    keep = np.concatenate([[True], np.diff(xs) > 1e-9])
    return xs[keep]


def solve(rects, ybot, ytop, xspan, eps_r, target, h_fine=0.004, plane_bot=True, plane_top=False):
    """rects: list of (x0, x1, y0, y1) conductors; target = index driven at 1 V, all others + planes at 0 V.
    ybot / ytop: domain limits (ground plane there when plane_bot / plane_top).  Returns dict of charges (fF/um):
    q[i] on rect i, q_bot, q_top (planes); capacitance target->k = -q[k]."""
    import scipy.sparse as sp
    import scipy.sparse.linalg as spl
    fx = [v for r in rects for v in r[:2]]
    fy = [v for r in rects for v in r[2:]]
    xs = _lines(fx, -xspan, xspan, h_fine)
    ys = _lines(fy, ybot, ytop, h_fine)
    nx, ny = len(xs), len(ys)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    owner = -np.ones((nx, ny), int)            # -1 free, k conductor k, -2 bottom plane, -3 top plane
    for k, (x0, x1, y0, y1) in enumerate(rects):
        m = (X >= x0 - 1e-9) & (X <= x1 + 1e-9) & (Y >= y0 - 1e-9) & (Y <= y1 + 1e-9)
        owner[m] = k
    if plane_bot:
        owner[:, 0] = -2
    if plane_top:
        owner[:, -1] = -3
    V = np.zeros((nx, ny))
    V[owner == target] = 1.0
    # dual cell sizes
    dxc = np.diff(xs)
    dyc = np.diff(ys)
    wx = np.zeros(nx); wx[:-1] += dxc / 2; wx[1:] += dxc / 2
    wy = np.zeros(ny); wy[:-1] += dyc / 2; wy[1:] += dyc / 2
    # edge conductances (dimensionless, x eps later)
    gx = wy[None, :] / dxc[:, None]            # between (i,j) and (i+1,j): shape (nx-1, ny)
    gy = wx[:, None] / dyc[None, :]            # between (i,j) and (i,j+1): shape (nx, ny-1)
    free = owner == -1
    idx = -np.ones((nx, ny), int)
    idx[free] = np.arange(free.sum())
    n = int(free.sum())
    rows, cols, vals = [], [], []
    rhs = np.zeros(n)
    diag = np.zeros(n)

    def add(ia, ja, ib, jb, g):
        fa, fb = free[ia, ja], free[ib, jb]
        a, b = idx[ia, ja], idx[ib, jb]
        # a free
        m = fa
        np.add.at(diag, a[m], g[m])
        mb = m & fb
        rows.append(a[mb]); cols.append(b[mb]); vals.append(-g[mb])
        mc = m & ~fb
        np.add.at(rhs, a[mc], g[mc] * V[ib, jb][mc])
        # b free
        m = fb
        np.add.at(diag, b[m], g[m])
        ma = m & fa
        rows.append(b[ma]); cols.append(a[ma]); vals.append(-g[ma])
        mc = m & ~fa
        np.add.at(rhs, b[mc], g[mc] * V[ia, ja][mc])

    I, J = np.meshgrid(np.arange(nx - 1), np.arange(ny), indexing="ij")
    add(I, J, I + 1, J, gx)
    I, J = np.meshgrid(np.arange(nx), np.arange(ny - 1), indexing="ij")
    add(I, J, I, J + 1, gy)
    A = sp.csr_matrix((np.concatenate(vals + [diag]), (np.concatenate(rows + [np.arange(n)]),
                                                         np.concatenate(cols + [np.arange(n)]))), shape=(n, n))
    V[free] = spl.spsolve(A.tocsc(), rhs)
    # charge on every fixed-potential owner = sum of flux into free nodes from its nodes
    q = {}

    def flux(ia, ja, ib, jb, g):
        oa, ob = owner[ia, ja], owner[ib, jb]
        f = g * (V[ia, ja] - V[ib, jb])         # flow a -> b
        for o in np.unique(np.concatenate([oa[oa != -1], ob[ob != -1]])):
            s = f[(oa == o) & (ob != o)].sum() - f[(ob == o) & (oa != o)].sum()
            q[int(o)] = q.get(int(o), 0.0) + s

    I, J = np.meshgrid(np.arange(nx - 1), np.arange(ny), indexing="ij")
    flux(I, J, I + 1, J, gx)
    I, J = np.meshgrid(np.arange(nx), np.arange(ny - 1), indexing="ij")
    flux(I, J, I, J + 1, gy)
    e = EPS0 * eps_r
    return {k: v * e for k, v in q.items()}, (nx, ny)


def pattern(w, t, s, below=None, above=None, neighbours=True, eps_r=3.0, xspan=None, h_fine=0.004, open_up=1.5,
            open_dn=1.5):
    """OpenRCX-style pattern: target (w x t, bottom at y=0) with two same-size neighbours at edge spacing s (if
    neighbours), ground plane at y = -below (gap from target bottom) and/or y = t + above.  Returns per-side
    (cc, fringe) in fF/um following the rules-file convention: total C = 2 * (cc + fringe)."""
    rects = [(-w / 2, w / 2, 0.0, t)]
    if neighbours:
        for sg in (-1, 1):
            c = sg * (w + s)
            rects.append((c - w / 2, c + w / 2, 0.0, t))
    ybot = -below if below is not None else -open_dn
    ytop = t + above if above is not None else t + open_up
    xspan = xspan or max(2.0, 3 * (w + s) + 1.0)
    q, _ = solve(rects, ybot, ytop, xspan, eps_r, 0, h_fine=h_fine, plane_bot=below is not None,
                 plane_top=above is not None)
    qt = q[0]
    cc = -(q.get(1, 0.0) + q.get(2, 0.0)) / 2 if neighbours else 0.0
    fr = (qt - 2 * cc) / 2
    return cc, fr
