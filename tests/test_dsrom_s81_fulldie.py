import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import dsrom_s81_fulldie as F  # noqa: E402


def _build(die):
    F.configure(die)
    return F.build()


def test_layer_die_inventory_and_legality():
    m = _build('layer')
    k = Counter(it.kind for it in m['insts'])
    assert k['q'] + k['bf'] == 2417 and k['bf'] == 519
    assert k['cfg'] == 2417 * 7
    assert k['node'] == 2 * 2417 - 128            # ragged RD64 return sized to the active pairs
    assert len(m['frames']) == 128
    lg = F.legality(m)
    assert lg['overlaps'] == 0 and lg['outside'] == 0
    assert all(max(c['rect'][2] - c['rect'][0], c['rect'][3] - c['rect'][1]) <= 5250 for c in m['cregions'])
    assert F.pin_clashes(m) == []                  # generated pins: no overlap / spacing fault (DRT-0073 r4)
    sp = sorted((it.y, it.y + it.h) for it in m['insts'] if it.name.startswith('sp_') and it.x < m['x_vch'])
    assert all(b[0] - a[1] >= F.SPINE_GAP - F.GY for a, b in zip(sp, sp[1:]))   # routing gaps between spine slabs


def test_head_die_inventory_and_legality():
    m = _build('head')
    k = Counter(it.kind for it in m['insts'])
    assert k['q'] + k['bf'] + k['bf_nv'] == 1682 and k['bf_nv'] == k['nvx'] == 211
    lg = F.legality(m)
    assert lg['overlaps'] == 0 and lg['outside'] == 0
    assert F.pin_clashes(m) == []
    F.configure('layer')


def test_return_tree_is_binary_over_all_leaves():
    for n in (36, 38, 2):
        nodes, root = F.return_tree(n)
        assert len(nodes) == n - 1
        kids = [c for _, a, b in nodes for c in (a, b)]
        assert sorted(c for c in kids if c.startswith('L')) == sorted(f'L{i}' for i in range(n))
