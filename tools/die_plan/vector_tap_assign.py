"""Opt-in vector implementation of taps.assign on finite plan coordinates.

Keeps nearest-index ties, capacity iteration order, candidate tuple order and
scalar weight accumulation unchanged. No geometry or mutable assignment cache.
The normal taps.assign remains the default until a caller explicitly opts in.
"""
import numpy as np


def assign(taps, sinks, cap, max_extra_um, max_distance_um=None):
    if not taps:
        if sinks:
            raise ValueError('min() arg is an empty sequence')
        return [], [], []
    k, n = len(taps), len(sinks)
    if not n:
        return [0.0] * k, [0.0] * k, []
    xy = np.asarray([(t[1], t[2]) for t in taps], dtype=float)
    ss = np.asarray(sinks, dtype=float)
    a = np.empty(n, dtype=np.int64)
    for lo in range(0, n, 1024):
        z = ss[lo:lo+1024, :2]
        d = np.abs(z[:, None, 0] - xy[None, :, 0]) + np.abs(z[:, None, 1] - xy[None, :, 1])
        a[lo:lo+len(z)] = d.argmin(axis=1)
    # Preserve the reference's exact floating-point addition order, including
    # fractional weights; vector sums may choose a different reduction tree.
    load = [0.0] * k
    for s, j in zip(sinks, a):
        load[int(j)] += s[2]
    stuck = set()
    for _ in range(8*k):
        over = next((j for j in range(k) if j not in stuck and load[j] > cap), None)
        if over is None:
            break
        ids = np.flatnonzero(a == over)
        available = np.asarray([j != over and load[j] < cap for j in range(k)])
        cand = []
        for lo in range(0, len(ids), 1024):
            ii = ids[lo:lo+1024]
            z = ss[ii, :2]
            d = np.abs(z[:, None, 0] - xy[None, :, 0]) + np.abs(z[:, None, 1] - xy[None, :, 1])
            allowed = np.broadcast_to(available, d.shape)
            if max_distance_um is not None:
                allowed = allowed & (d <= max_distance_um)
            best = np.where(allowed, d, np.inf).argmin(axis=1)
            valid = allowed[np.arange(len(ii)), best]
            for row in np.flatnonzero(valid):
                j = int(best[row])
                extra = float(d[row, j] - d[row, over])
                if extra <= max_extra_um:
                    cand.append((extra, int(ii[row]), j))
        if not cand:
            stuck.add(over)
            continue
        cand.sort()
        tgt = cand[0][2]
        for _, i, j in cand:
            if load[over] <= cap or load[tgt] >= cap:
                break
            if j != tgt:
                continue
            a[i] = tgt
            load[over] -= sinks[i][2]
            load[tgt] += sinks[i][2]
    far = np.zeros(k)
    dist = np.abs(ss[:, 0]-xy[a, 0]) + np.abs(ss[:, 1]-xy[a, 1])
    np.maximum.at(far, a, dist)
    return load, far.tolist(), a.tolist()
