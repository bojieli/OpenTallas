#!/usr/bin/env python3
"""S81-DIEPLACE legal reset tree: caps, exact R0 pin reach, calendar delivery, refusal (tools/s81_dv/reset_legal.py)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / 's81_dv'))
import reset_legal as RL


def die():
    rects = [[1000, 0, 1400, 2600], [2000, 400, 2600, 3000], [200, 2900, 3900, 3000]]   # blocks + a horizontal band
    return RL.LegalTree(4000.0, 4000.0, dict(rects=rects, reset_size=[17.28, 17.28]))


def test_slots_legal_and_disjoint():
    t = die()
    occ = RL.Occ(4000.0, 4000.0)
    for r in [[1000, 0, 1400, 2600], [2000, 400, 2600, 3000], [200, 2900, 3900, 3000]]:
        occ.add(r)
    for x, y in t.S:
        assert not occ.hits((x, y, x + 17.28, y + 17.28)), (x, y)
        assert abs(x / RL.GRID_O - round(x / RL.GRID_O)) < 1e-6 and abs(y / RL.GRID_O - round(y / RL.GRID_O)) < 1e-6
    S = sorted(t.S)
    for i, a in enumerate(S):
        for b in S[i + 1:i + 40]:
            assert not (abs(a[0] - b[0]) < 17.78 and abs(a[1] - b[1]) < 17.78), (a, b)


def test_tree_caps_reach_and_delivery():
    t = die()
    t.build((2000.0, 0.0))
    for xy in [(300, 300), (3800, 3800), (1500, 1500), (2700, 2000)]:
        assert t.serve(xy) is not None
    m = t.min_dep((3800, 100), 0)
    k = t.deliver_slack(m + 5, (3800, 100), 0.0, 'calendar')
    assert t.dep[k] == m + 5 and RL.sink_um(t.S[k], (3800, 100)) <= RL.REACH
    c = t.check()
    assert c['n_over_reach'] == 0 and c['max_children'] <= RL.CHILD_CAP and c['max_sink_loads'] <= RL.SINK_CAP, c
    assert c['chain_stations'] >= 1 and c['max_hop_um'] <= RL.REACH


def test_refuses_shallower_than_physical():
    t = die()
    t.build((2000.0, 0.0))
    m = t.min_dep((3800, 3800), 0)
    try:
        t.deliver_slack(m - 1, (3800, 3800), 0.0, 'too early')
    except ValueError:
        return
    raise AssertionError('a release earlier than any station in reach must be refused')


if __name__ == '__main__':
    for f in (test_slots_legal_and_disjoint, test_tree_caps_reach_and_delivery, test_refuses_shallower_than_physical):
        f(); print('PASS', f.__name__)
