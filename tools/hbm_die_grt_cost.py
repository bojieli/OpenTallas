#!/usr/bin/env python3
"""GRT-overflow history cost for the HBM die generator (H-DIE 10-14).

The window model (tools/hbm_r25gq_windows.py) passed v14 at worst 0.881 while the k16 die GRT of the same geometry kept
76,137 tracks of overflow (grt21_p2): only 8 % of that overflow lies in windows the model flags even at util 0.50, so
the window PathFinder cannot see it (pin-access / M6 crowding at the slice | SU lane-group faces, not window demand).
This turns the GRT's own overflow map into the generator's route-cell history cost (V['cong'] / OT_HBMDIE_CONG, same
(ny, nx) grid of CELL-um cells as --cost-out of the window tool), so relay chains and stations move off the cells the
global router could not fit.

    python3 tools/hbm_die_grt_cost.py GCELL_USAGE.txt --prev cong_prev.npy --out cong_next.npy [--gain 6] [--cap 24]

cost(cell) = prev + gain * min(1, overflow tracks summed over M4-M9 within the cell and its 8 neighbours / norm),
capped at cap (norm = the 90th percentile of the non-zero smoothed overflow).
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np

W_UM, H_UM, CELL = 32984.288, 25980.528, 100.0


def overflow_grid(path, cell=CELL):
    gx = gy = None
    nx, ny = math.ceil(W_UM / cell), math.ceil(H_UM / cell)
    ov = np.zeros((ny, nx))
    for ln in open(path):
        if ln.startswith('GRIDX'):
            gx = [int(v) / 1000 for v in ln.split()[1].split(',')]
        elif ln.startswith('GRIDY'):
            gy = [int(v) / 1000 for v in ln.split()[1].split(',')]
        elif ln.startswith('L '):
            f = ln.split()
            lay, j = f[1], int(f[2])
            if lay in ('M1', 'M2', 'M3'):
                continue
            y = gy[min(j, len(gy) - 1)]
            jj = min(ny - 1, int(y // cell))
            for n, cu in enumerate(f[3:]):
                c, u = (float(v) for v in cu.split('/'))
                o = u - c
                if o <= 0:
                    continue
                x = gx[min(4 * n, len(gx) - 1)]
                ov[jj, min(nx - 1, int(x // cell))] += o
    return ov


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('gcell', type=Path)
    ap.add_argument('--prev', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--gain', type=float, default=6.0)
    ap.add_argument('--cap', type=float, default=24.0)
    a = ap.parse_args(argv)
    from scipy import ndimage as ndi
    ov = overflow_grid(a.gcell)
    sm = ndi.uniform_filter(ov, size=3, mode='constant') * 9.0
    nz = sm[sm > 0]
    norm = float(np.percentile(nz, 90)) if nz.size else 1.0
    add = a.gain * np.minimum(1.0, sm / max(norm, 1e-9))
    prev = np.load(a.prev) if a.prev else np.zeros_like(add)
    assert prev.shape == add.shape, (prev.shape, add.shape)
    out = np.minimum(prev + add, a.cap)
    np.save(a.out, out)
    print(json.dumps(dict(overflow_total=round(float(ov.sum())), cells_with_overflow=int((ov > 0).sum()),
                          norm=round(norm, 1), cells_charged=int((add > 0).sum()), cost_max=round(float(out.max()), 2),
                          shape=list(out.shape))))


if __name__ == '__main__':
    main()
