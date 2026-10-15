import json, sys, copy
from pathlib import Path
import price_pmh as P          # reuses graph g, base, cost()
from pair_mirror import build, interleave
g, base = P.g, P.base
tp = g.pins['qfd_tile_nk']; orig = {p: tp[p].copy() for p in ('n_a', 'n_b', 'n_y', 't_out')}
S0, B = P.stagemap(base); c0 = P.cost(S0, B)
interleave(tp)
m, geom = build(base, keep_rows=(7, 8))
S1, _ = P.stagemap(m); c1 = P.cost(S1, B)
S2, _ = P.stagemap(base); c2 = P.cost(S2, B)    # interleave alone
print(json.dumps(dict(baseline=c0, pmh_interleave=c1, interleave_only=c2), default=str))
