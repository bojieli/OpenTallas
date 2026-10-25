"""Physical mechanism check: independent L-corner bands retain coherent pipeline depth and ordered bits."""
import numpy as np
from tools.die_plan import ft_corridor as F
from tools.die_trial.legal_sites import RowAllocator


def test_l_corner_split_depth_reach_and_legal_nonoverlap():
    width = 33
    a = np.column_stack((np.linspace(20, 100, width), np.full(width, 240.0)))
    b = np.column_stack((np.zeros(width), np.linspace(30, 110, width)))
    alloc = RowAllocator((4.32, 4.32, 235.68, 235.68), blocked=[], cell_size=F.CELL,
                         column_pitch=2.16, row_pitch=.27, origin=(4.32, 4.32))
    original_a, original_b = a.copy(), b.copy()
    sites, centres, path, ledger = F.place_split_slot({"name": "test", "stations": 4},
        a, b, "N", "W", 240.0, 240.0, [], alloc, 115.0, split_bits=8)
    assert len(sites) == 3
    assert all(stage.shape == (width, 2) for stage in sites)
    assert np.array_equal(a, original_a) and np.array_equal(b, original_b)
    assert max(ledger["hops_um"]) <= 115.0
    assert ledger["groups"] == 5
    all_sites = np.concatenate(sites)
    assert len({tuple(x) for x in all_sites}) == len(all_sites)
