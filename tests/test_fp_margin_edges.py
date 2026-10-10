"""s81-gen: fp_margin_lint.die_margin(edges=True) gives the chain walk's verdict and violation sets."""
import random
import sys
from pathlib import Path
from types import SimpleNamespace as N

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import fp_margin_lint as FPL  # noqa: E402


def _die(seed):
    rnd = random.Random(seed)
    insts, buses = [], []
    for i in range(60):
        insts.append(N(name=f'i{i}', kind=rnd.choice(['rly', 'rly', 'blk']), x=rnd.uniform(0, 3000),
                       y=rnd.uniform(0, 3000), w=10.0, h=10.0))
    for j in range(80):
        a, b = rnd.sample(range(60), 2)
        buses.append((f'b{j}', 'x', 8, [(f'i{a}', 'o'), (f'i{b}', 'i')]))
    return insts, buses


def test_edges_mode_matches_chain_walk():
    for seed in range(30):
        insts, buses = _die(seed)
        a = FPL.die_margin(insts, buses, ('rly',), reach_um=700.0)
        b = FPL.die_margin(insts, buses, ('rly',), reach_um=700.0, edges=True)
        assert a['verdict'] == b['verdict'], seed
        assert {r['seg'] for r in a['reach_examples']} <= {r['seg'] for r in FPL.die_margin(
            insts, buses, ('rly',), reach_um=700.0, edges=True, limit=10 ** 6)['reach_examples']}, seed
        fa = {r['relay'] for r in FPL.die_margin(insts, buses, ('rly',), reach_um=700.0, limit=10 ** 6)['far_side_examples']}
        fb = {r['relay'] for r in FPL.die_margin(insts, buses, ('rly',), reach_um=700.0, edges=True,
                                                 limit=10 ** 6)['far_side_examples']}
        assert fa <= fb, seed
