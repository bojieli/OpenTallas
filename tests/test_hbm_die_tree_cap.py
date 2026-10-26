"""Capacity-aware clock / reset tree routing of the HBM R25GQ die generator (tree_cap, hbmdie 10-13).

The die-level acceptance is `hbm_accel_die_fp.py check --ds-var r25gqn_v12` / `r25gqn_v10_hclegal` (0 overlaps, 0 pin
clashes, 0 reach violations; ~6 minutes each, run on the fleet).  These tests pin the two helpers the tree builder
routes on, on a geometry of the failing class: a 121-um channel between two blocks with an open detour above it."""
import sys
from pathlib import Path

import numpy as np
from scipy.sparse.csgraph import dijkstra

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import hbm_accel_die_fp as H
import hbm_r25gq_plan as RP

W, HH = 3000.0, 2800.0
# two blocks 1,800 um long, a 121-um channel between them at y 700-821 (the attention equator channel class); the band
# above the upper block (y 2,300-2,800) is open, the lower block reaches the die edge
BLOCKS = [(600.0, 0.0, 2400.0, 700.0), (600.0, 821.0, 2400.0, 2300.0)]


class _B:
    kind = 'hub'

    def __init__(self, n, b):
        self.name, self._b = n, b

    def box(self):
        return self._b


def _grid():
    return RP.Grid(dict(geo=dict(W=W, H=HH), insts=[_B(f'b{i}', b) for i, b in enumerate(BLOCKS)]))


def _route(G, cost, a, b):
    d, pr = dijkstra(G.graph(cost), indices=[G.idx(*a)], min_only=True, return_predecessors=True)[:2]
    p = [G.idx(*b)]
    while pr[p[-1]] >= 0:
        p.append(pr[p[-1]])
    return [(k % G.nx, k // G.nx) for k in p[::-1]]


def test_wide_mask_separates_the_narrow_channel_from_open_space():
    G = _grid()
    wide, widef = H.tree_wide_mask(BLOCKS, W, HH, G.nx, G.ny, RP.CELL)
    assert not wide[76, 150]            # (x 1,500, y 760): inside the 121-um channel
    assert wide[255, 150]               # (x 1,500, y 2,550): the open band above
    assert wide[76, 30]                 # (x 300, y 760): W of the blocks, open
    assert not wide[40, 150]            # inside a block
    assert widef[7, 15] < 0.3 and widef[25, 15] > 0.9
    # the mouth of the channel is open space, its inside is not
    assert wide[76, 50] and not wide[76, 70]


def test_a_full_channel_is_routed_around_and_a_stall_closes_it():
    G = _grid()
    _, widef = H.tree_wide_mask(BLOCKS, W, HH, G.nx, G.ny, RP.CELL)
    occ, stall = np.zeros((G.ny, G.nx)), np.zeros((G.ny, G.nx))
    a, b = (3, 7), (27, 7)                # W and E of the blocks, on the channel row (j 7 = y 700-800)
    chan = [(i, 7) for i in range(7, 23)]

    def through(cost):
        p = _route(G, cost, a, b)
        return sum(1 for c in p if c in chan), p

    n0, p0 = through(H.tree_cap_cost(G.free, occ, stall, widef, 400.0))
    assert n0 == len(chan) and len(p0) == 25          # empty: straight through the channel
    # 40 % of the channel's free area holds pairs (the measured v12 state: 236 pairs): the next edge detours
    for i, j in chan:
        occ[j, i] = 0.40 * G.free[j, i]
    n1, p1 = through(H.tree_cap_cost(G.free, occ, stall, widef, 400.0))
    assert n1 == 0 and len(p1) > 25
    assert all(G.free[j, i] >= 0.2 for i, j in p1)      # and never through a block
    # a lightly used channel is still taken (no detour for a few pairs)
    occ[:] = 0.0
    for i, j in chan:
        occ[j, i] = 0.10 * G.free[j, i]
    assert through(H.tree_cap_cost(G.free, occ, stall, widef, 400.0))[0] == len(chan)
    # one stall is a charge, ten close the cell like a block
    c1 = H.tree_cap_cost(G.free, occ * 0, stall, widef, 400.0)
    stall[7, 12] = 1.0
    c2 = H.tree_cap_cost(G.free, occ * 0, stall, widef, 400.0)
    assert c2[7, 12] - c1[7, 12] == 400.0 * H.TREE_STALL_COST
    stall[7, 12] = 10.0
    assert through(H.tree_cap_cost(G.free, occ * 0, stall, widef, 400.0))[0] < len(chan)


def test_tree_cap_is_on_for_the_contract_presets_only():
    assert H.variant_arg('r25gqn_v12').get('tree_cap') and H.variant_arg('r25gqn_v10_hclegal').get('tree_cap')
    assert not H.variant_arg('r25gqn_v10').get('tree_cap')      # the v10 / v11 geometry replays unchanged
