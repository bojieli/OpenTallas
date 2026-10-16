import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import regtree as rt


def test_balanced_tree_covers_every_sink_once():
    g = rt.dct.Grid(3000.0, 3000.0, [(1000.0, 1000.0, 1600.0, 1600.0)])
    sinks = [(f'u{i}/ck', 'm', 100.0 + 37.0 * i % 2800, 100.0 + 53.0 * i % 2800, 'm/ck') for i in range(200)]
    leaves = rt.cluster(sinks)
    b = rt.Builder(g, 'dc_t')
    rec = b.build('pll/ck', (1500.0, 2900.0), leaves)
    loads = [l for _, _, ls in b.nets for l in ls]
    pins = [l[1] for l in loads if l[0] == 'pin']
    assert sorted(pins) == sorted(s[0] for s in sinks)
    bufs = [l[1] for l in loads if l[0] == 'buf']
    assert len(bufs) == len(set(bufs)) == len(b.bufs)          # every buffer driven exactly once
    drivers = [d for _, d, _ in b.nets]
    assert len(drivers) == len(set(map(tuple, drivers)))
    assert rec['model_insertion_ps'] > 0
    for n, cell, x, y in b.bufs:                                  # no cell inside the blockage
        assert not (1000.0 < x < 1600.0 and 1000.0 < y < 1600.0)


def test_cluster_respects_key_and_size():
    s = [(f'a{i}/ck', 'm1', 10.0, 10.0, 'k1') for i in range(30)] + [('b/ck', 'm2', 10.0, 10.0, 'k2')]
    L = rt.cluster(s)
    assert all(len(l) <= rt.LEAF_MAX for l in L)
    assert all(len({x[4] for x in l}) == 1 for l in L)
    assert sum(len(l) for l in L) == 31
