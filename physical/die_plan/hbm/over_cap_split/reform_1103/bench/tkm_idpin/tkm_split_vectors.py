#!/usr/bin/env python3
"""DIE-HBM-61/SPLIT 11-03: short TKM tp192 cases for the tile RE-FORM chain bench (same oracle as
tools/hgi_coll_tkm_tp192_vectors.py: hgi_coll_tkm_vectors.write_case, NumPy lexsort).  full2048 fills every one of the
2048 chain entries (deepest tile / half tile exercised, nout 2048); part700 a partial K with an R pass and ties."""
import argparse, json, sys
from pathlib import Path
import numpy as np
ap = argparse.ArgumentParser(); ap.add_argument('--out', required=True, type=Path); ap.add_argument('--tools', required=True)
a = ap.parse_args(); sys.path.insert(0, a.tools)
from hgi_coll_tkm_vectors import write_case, bf16, owned_ids
a.out.mkdir(parents=True, exist_ok=True); rng = np.random.default_rng(611103); cases = []
g = 8; ids = [owned_ids(q, 1 << 20, g, 512, rng) for q in range(g)]; vals = [bf16(rng.normal(0, 1, 512)) for _ in range(g)]
cases.append(write_case(a.out, 'full2048', g, 512, 2048, 7, vals, ids, True))
g = 16; ids = [owned_ids(q, 1 << 20, g, 256, rng) for q in range(g)]
vals = [bf16(np.round(rng.normal(0, 1, 256) * 4) / 4) for _ in range(g)]          # coarse values: many ties
cases.append(write_case(a.out, 'part700', g, 256, 700, 15, vals, ids, True))
(a.out / 'cases.json').write_text(json.dumps(cases, indent=2) + '\n'); print('TKM_SPLIT_VECTORS', [(x['name'], x['nout'], x['fault']) for x in cases])
