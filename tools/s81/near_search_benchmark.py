#!/usr/bin/env python3
"""Compare exact source placement search with its previous prefix implementation."""
import json
import pathlib
import statistics
import sys
import time
from unittest.mock import patch
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import dsrom_s81_fulldie as G
rows = []
for horiz in (False, True):
    for scenario in ('blocked', 'open', 'narrow'):
        placer = G.Placer({'insts': []})
        if scenario == 'blocked':
            placer.occ.add((0., 0., 2000., 2000.))
        allowed = [(0., 0., 2000., 2000.)] if scenario != 'narrow' else [(700., 200., 750., 1800.)]
        args = (700., 800., 34.56, 30.24, allowed)
        kw = dict(prev=(650., 800.), nxt=(750., 900.), reach=400., nreach=500.,
                  horiz=horiz, span=1200., rows=120)
        out = {}
        for name, fn in [('prefix', G._near_reachable_prefix), ('axis', G._near_reachable_candidates)]:
            times = []
            for _ in range(5):
                with patch.object(G, '_near_reachable_candidates', fn):
                    start = time.perf_counter()
                    hit = placer.near(*args, **kw)
                    times.append(time.perf_counter() - start)
            out[name] = dict(median_seconds=statistics.median(times), hit=hit)
        assert out['prefix']['hit'] == out['axis']['hit']
        out.update(scenario=scenario, horiz=horiz,
                   speedup=out['prefix']['median_seconds'] / out['axis']['median_seconds'])
        rows.append(out)
print(json.dumps(dict(scope='Exact first-placement equivalence and CPU microbenchmark; no die closure claim', cases=rows), indent=2))
