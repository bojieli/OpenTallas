"""Exact die occupancy searches with local summed-area windows."""
import math
import numpy as np

CELL = 5.4  # occupancy grid (um), unchanged

class Occ:
    """occupancy grid with an integral image for O(1) rectangle-free tests."""

    def __init__(self, W, H):
        self.nx, self.ny = int(W / CELL) + 1, int(H / CELL) + 1
        self.g = np.zeros((self.ny, self.nx), np.uint8)
        self.W, self.H = W, H
        self._ii = None

    def mark(self, x, y, w, h, halo=0.0):
        i0 = max(0, int((x - halo) / CELL)); j0 = max(0, int((y - halo) / CELL))
        i1 = min(self.nx, int(math.ceil((x + w + halo) / CELL))); j1 = min(self.ny, int(math.ceil((y + h + halo) / CELL)))
        self.g[j0:j1, i0:i1] = 1
        self._ii = None

    def ii(self):
        if self._ii is None:
            a = np.zeros((self.ny + 1, self.nx + 1), np.int32)
            a[1:, 1:] = self.g.cumsum(0).cumsum(1)
            self._ii = a
        return self._ii

    def find(self, cx, cy, w, h, halo=0.0, region=None, rmax=None):
        """lower-left (x, y) of a free w x h rect (+halo) nearest to centre (cx, cy); region = (x0, y0, x1, y1) limits it."""
        nw = int(math.ceil((w + 2 * halo) / CELL)); nh = int(math.ceil((h + 2 * halo) / CELL))
        # Most free homes lie within a few cells. Recomputing a full-die summed
        # area image for each placed tile costs minutes. Keep the exact original
        # spiral and tie order, but build only the requested occupancy window.
        window = None
        ci = int((cx - w / 2 - halo) / CELL); cj = int((cy - h / 2 - halo) / CELL)
        lo_i, lo_j, hi_i, hi_j = 0, 0, self.nx - nw, self.ny - nh
        if region:
            lo_i = max(lo_i, int(math.ceil(region[0] / CELL))); lo_j = max(lo_j, int(math.ceil(region[1] / CELL)))
            hi_i = min(hi_i, int(region[2] / CELL) - nw); hi_j = min(hi_j, int(region[3] / CELL) - nh)
        if hi_i < lo_i or hi_j < lo_j:
            return None
        R = rmax or max(self.nx, self.ny)
        for r in range(0, R):
            ii_ = np.concatenate([np.arange(ci - r, ci + r + 1), np.full(2 * r - 1 if r else 0, ci - r),
                                  np.full(2 * r - 1 if r else 0, ci + r), np.arange(ci - r, ci + r + 1)]) if r else np.array([ci])
            jj_ = np.concatenate([np.full(2 * r + 1, cj - r), np.arange(cj - r + 1, cj + r),
                                  np.arange(cj - r + 1, cj + r), np.full(2 * r + 1, cj + r)]) if r else np.array([cj])
            ok = (ii_ >= lo_i) & (ii_ <= hi_i) & (jj_ >= lo_j) & (jj_ <= hi_j)
            if not ok.any():
                if r > max(abs(ci - lo_i), abs(ci - hi_i), abs(cj - lo_j), abs(cj - hi_j)) + 1:
                    return None
                continue
            i, j = ii_[ok], jj_[ok]
            if self._ii is not None:
                ii = self._ii
                s = ii[j + nh, i + nw] - ii[j, i + nw] - ii[j + nh, i] + ii[j, i]
            else:
                x0, y0, x1, y1 = int(i.min()), int(j.min()), int(i.max()) + nw, int(j.max()) + nh
                if window is None or x0 < window[0] or y0 < window[1] or x1 > window[2] or y1 > window[3]:
                    if window is not None:
                        wx0, wy0, wx1, wy1, _ = window
                        x0 = min(x0, wx0 - (wx1-wx0)//2); y0 = min(y0, wy0 - (wy1-wy0)//2)
                        x1 = max(x1, wx1 + (wx1-wx0)//2); y1 = max(y1, wy1 + (wy1-wy0)//2)
                    x0, y0 = max(0, x0-32), max(0, y0-32)
                    x1, y1 = min(self.nx, x1+32), min(self.ny, y1+32)
                    ii = np.zeros((y1-y0+1, x1-x0+1), np.int32)
                    ii[1:,1:] = self.g[y0:y1,x0:x1].cumsum(0).cumsum(1)
                    window = (x0,y0,x1,y1,ii)
                x0,y0,_,_,ii = window
                ix,jy = i-x0,j-y0
                s = ii[jy+nh,ix+nw]-ii[jy,ix+nw]-ii[jy+nh,ix]+ii[jy,ix]
            free = np.nonzero(s == 0)[0]
            if len(free):
                d = (i[free] - ci) ** 2 + (j[free] - cj) ** 2
                k = free[int(np.argmin(d))]
                return round(i[k] * CELL + halo, 3), round(j[k] * CELL + halo, 3)
        return None


