"""plan_hb: balanced binary H-tree over 2^n fixed islands (KV-KVSCTL-4)."""
import random, sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import core_infra_htree as H


def _geo(tmp, W=86.4, n=400, entry=(43.2, 43.2)):
    random.seed(3); L = ['CORE 0 0 %g %g' % (W, W), 'PIN ck %g %g' % entry]
    for i in range(n):
        L.append('SINK %.3f %.3f DFFHQNx1_ASAP7_75t_R r%d CLK' % (random.uniform(1, W - 1), random.uniform(1, W - 1), i))
    p = tmp / 'g.geo'; p.write_text('\n'.join(L) + '\n'); return str(p)


def test_hb_4x2_binary_equal_legs(tmp_path):
    xs = (10.8, 32.4, 54.0, 75.6); ys = (21.6, 64.8)
    isl = [(x, y) for x in xs for y in ys]
    P = H.plan_hb(_geo(tmp_path), isl, [0, 1, 0], [2], leaf_n=2, smax=200.0)
    # every internal node above the islands has exactly 2 children; islands are the fixed plan sites
    for g in P['groups']:
        if len(g) < 3:
            assert (g + (0,)) in P['groups'] and (g + (1,)) in P['groups'] and (g + (2,)) not in P['groups']
    assert sorted(P['mz'].xy(P['site'][g]) for g in P['isl_groups']) == sorted(isl)
    # mirrored islands -> equal legs per level (spread 0) above the islands, hubs exactly at the midpoints
    for lv in (1, 2, 3):
        assert P['level_spread_um'][lv] == 0.0
    assert all(v == 0.0 for v in P['hub_snap_um'].values())
    # buffer per branch: no net drives two far branches
    assert H.shared_wire(P)['nets_with_shared_branches'] == 0


def test_hb_rejects_wrong_island_count(tmp_path):
    with pytest.raises(AssertionError):
        H.plan_hb(_geo(tmp_path), [(10.8, 21.6)] * 6, [0, 1, 0], [2])
