#!/usr/bin/env python3
"""c5 diagnosis (2026-10-13): gcell-level profile of a box (overflow, effective capacity, guide usage) for M6..M9.
  c5diag_grid_probe.py save  <out dir with gcell_ov.txt + phase1.pkl>            -> grid.npz (per layer _use/_cap/_ov)
  c5diag_grid_probe.py probe <out dir> NAME=x0,y0,x1,y1=M6,M8=<axis 0:x 1:y> ...  -> merged overflow runs along the axis"""
import os, pickle, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c5diag_congestion as M

mode, S = sys.argv[1:3]
um = 9.6
if mode == 'save':
    gx, gy, full = M.read_ov(S + '/gcell_ov.txt')
    nx, ny = len(gx), len(gy)
    G = pickle.load(open(S + '/phase1.pkl', 'rb'))['G']
    A = {}
    for ln in M.MAPPED:
        cap, raw = full[ln]
        ug = M.edge_usage(G, M.LAYERS.index(ln), nx, ny)
        val, _, _ = M.unwrap(cap, raw, ug)
        A[ln] = (ug, cap - (val - ug), np.maximum(0, val - cap))
    np.savez_compressed(S + '/grid.npz', **{ln + k: A[ln][n].astype(np.int16) for ln in A for n, k in enumerate(('_use', '_cap', '_ov'))})
    print('saved', S + '/grid.npz')
else:
    Z = np.load(S + '/grid.npz')
    for a in sys.argv[3:]:
        nm, v, ls, ax = a.split('=')
        x0, y0, x1, y1 = (float(t) for t in v.split(','))
        i0, i1, j0, j1 = int(x0 / um), int(x1 / um), int(y0 / um), int(y1 / um)
        axis = int(ax)
        for ln in ls.split(','):
            u, c, o = (Z[ln + k][j0:j1, i0:i1].astype(np.int64) for k in ('_use', '_cap', '_ov'))
            so = o.sum(axis)
            runs = []
            for k in np.nonzero(so)[0]:
                if runs and k == runs[-1][1] + 1:
                    runs[-1][1] = k
                else:
                    runs.append([k, k])
            runs.sort(key=lambda r: -so[r[0]:r[1] + 1].sum())
            base = i0 if axis == 0 else j0
            print('%s %s overflow %d use/cap %d/%d max gcell %d; %d runs along %s (um: overflow, mean cap, mean use):'
                  % (nm, ln, o.sum(), u.sum(), c.sum(), o.max(), len(runs), 'x' if axis == 0 else 'y'))
            print('   ' + ' | '.join('%.0f-%.0f: %d cap %.0f use %.0f' % ((base + a_) * um, (base + b + 1) * um, so[a_:b + 1].sum(),
                                                                       c.sum(axis)[a_:b + 1].sum() / ((b - a_ + 1) * c.shape[axis]),
                                                                       u.sum(axis)[a_:b + 1].sum() / ((b - a_ + 1) * u.shape[axis])) for a_, b in runs[:10]))
