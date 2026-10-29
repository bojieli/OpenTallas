"""Exact, opt-in geometry cache for the existing physical clock model.

MSTs and RC trees depend on geometry and pin capacitances, not clock arrival.
Reuse those pure results during pre-build master sizing. The numerical kernel,
edge order and pin-capacitance insertion order are preserved exactly.
"""
from contextlib import contextmanager
from functools import lru_cache


@contextmanager
def geometry_cache(kernel):
    mst_original, rc_original = kernel.mst_edges, kernel.rc_tree

    @lru_cache(maxsize=None)
    def mst(points):
        return tuple(mst_original(points))

    @lru_cache(maxsize=None)
    def rc(points, edges, pin_capacitances, resistance, capacitance):
        cw, cp, elmore, rw = rc_original(points, edges, dict(pin_capacitances), resistance, capacitance)
        return cw, cp, tuple(elmore.items()), rw

    def mst_cached(points):
        return list(mst(tuple(tuple(p) for p in points)))

    def rc_cached(points, edges, pin_capacitances, resistance, capacitance):
        # Do not sort pincap: preserving its insertion order preserves float sums.
        cw, cp, elmore, rw = rc(tuple(tuple(p) for p in points), tuple(tuple(e) for e in edges),
                                tuple(pin_capacitances.items()), resistance, capacitance)
        return cw, cp, dict(elmore), rw

    kernel.mst_edges, kernel.rc_tree = mst_cached, rc_cached
    try:
        yield dict(mst=mst.cache_info, rc=rc.cache_info)
    finally:
        kernel.mst_edges, kernel.rc_tree = mst_original, rc_original
        mst.cache_clear()
        rc.cache_clear()
