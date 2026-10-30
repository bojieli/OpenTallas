import sys
p = sys.argv[1]; s = open(p).read()
old = """                        yl = _prov_pg_clear(p[1])
                        bx, bm = track("M9", p[0] + off, ty, yl, nm, f"drop {ld}")
                        add(("M9", bx, min(ty, yl), bx, max(ty, yl)), bm)
"""
new = """                        yl = _prov_pg_clear_ix(p[1], p[0] + off, router, nm) if _PROV_F1 else _prov_pg_clear(p[1])
                        bx, bm = track("M9", p[0] + off, ty, yl, nm, f"drop {ld}")
                        add(("M9", bx, min(ty, yl), bx, max(ty, yl)), bm)
                        if _PROV_F1 and router is not None:
                            _pad = ("M8", nm, "access", yl - .04, yl + .04, bx - .096, bx + .096)
                            _PROV_STATS["f1_pad_hit" if router.ix.hits(_pad, first=True) else "f1_pad_clear"] += 1
                            router.ix.add(_pad)
"""
assert s.count(old) == 1; s = s.replace(old, new)
old2 = "def _prov_pg_clear(y, sp=.32, h=.04, step=.005, lim=8.64):"
new2 = '''# DIE-QC-40 F1 (QC-001 shield class): a far provider M9 drop lands its M8 pad on the nearest PG-clear row whose pad
# (+-0.3 um x around the ideal drop column) is also clear of every reserved tree/shield shape of another net (the own net's
# drawn VSS shield included); the chosen pad is then reserved so later tracks + shields keep clear of it.
_PROV_F1 = _os.environ.get("OT_DQC40_F1", "") == "1"
def _prov_pg_clear_ix(y, x, router, nm, sp=.32, h=.04, step=.005, lim=8.64):
    if router is None: return _prov_pg_clear(y, sp, h, step, lim)
    lo = [a for a, b in _PROV_STRAPS]
    def bad(v):
        j = _bisect.bisect_right(lo, v + sp + h) - 1
        if any(v + h > a - sp and v - h < b + sp for a, b in _PROV_STRAPS[max(0, j - 1):j + 2]): return True
        return bool(router.ix.hits(("M8", nm, "access", v - h, v + h, x - .3, x + .3), first=True))
    k = 0
    while k * step <= lim:
        for v in (y - k * step, y + k * step):
            if not bad(v):
                if k: _PROV_STATS["f1_moved"] += 1
                return round(v, 4)
        k += 1
    _PROV_STATS["f1_none"] += 1
    return _prov_pg_clear(y, sp, h, step, lim)
''' + old2
assert s.count(old2) == 1; s = s.replace(old2, new2)
old3 = "_PROV_MODE=_PROV_MODE, _PROV_NEAR_A=_PROV_NEAR_A, _PROV_STATS=_PROV_STATS, _prov_pg_clear=_prov_pg_clear)"
new3 = "_PROV_MODE=_PROV_MODE, _PROV_NEAR_A=_PROV_NEAR_A, _PROV_STATS=_PROV_STATS, _prov_pg_clear=_prov_pg_clear, _prov_pg_clear_ix=_prov_pg_clear_ix, _PROV_F1=_PROV_F1)"
assert s.count(old3) == 1; s = s.replace(old3, new3)
open(p, "w").write(s)
