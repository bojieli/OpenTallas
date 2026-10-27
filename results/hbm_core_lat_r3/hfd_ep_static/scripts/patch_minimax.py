from pathlib import Path
import sys
p = Path(sys.argv[1]); s = p.read_text()
a = """            if best is None or v < best[0]: best = (v, (i, j))
    return best[1]
"""
assert a in s
s = s.replace(a, """            if best is None or v < best[0]: best = (v, (i, j))
    if best is None:
        # HBM-CORE-LAT-R3: no legal site within the radius (children centroid over a large macro, e.g. a centred SRAM
        # column): widen the search deterministically instead of failing
        if radius >= max(mz.NX, mz.NY):
            raise ValueError('no legal minimax site for children %s' % (children,))
        return minimax_site(mz, children, around, radius=radius * 2, step=step)
    return best[1]
""")
p.write_text(s); print("patched")
