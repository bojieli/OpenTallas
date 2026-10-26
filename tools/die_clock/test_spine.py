"""GEN16 spine: member selection fails closed, one spine leaf per regional entry, every entry driven exactly once,
the spine merge compensates each region tree's model insertion (key = tree name)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import regtree as rt


def _trees():
    return [dict(name='r0', root='g/p0', period=833.333333, local_root='median'),
            dict(name='r1', root='g/p1', period=833.333333, local_root='median'),
            dict(name='slow', root='g/p2', period=5000.0, local_root='median'),
            dict(name='nolr', root='g/p3', period=833.333333)]


def test_members_by_period_and_local_root():
    rb = {'g/p0': 'dc_root_r0', 'g/p1': 'dc_root_r1', 'g/p2': 'dc_root_slow', 'g/p3': 'dc_root_nolr'}
    m = rt.spine_members(_trees(), {'r0', 'r1', 'slow', 'nolr'}, rb, dict(source='g/p0'))
    assert [t['name'] for t, _ in m] == ['r0', 'r1']


def test_listed_tree_without_entry_fails_closed():
    rb = {'g/p0': 'dc_root_r0'}
    try:
        rt.spine_members(_trees(), {'r0', 'nolr'}, rb, dict(source='g/p0', trees=['r0', 'nolr']))
    except ValueError as e:
        assert 'nolr' in str(e)
    else:
        raise AssertionError('listed tree without a regional entry was accepted')


def test_spine_drives_every_entry_once_and_compensates():
    g = rt.dct.Grid(6000.0, 6000.0, [(2000.0, 2000.0, 4000.0, 4000.0)])
    xy = {f'dc_root_r{i}': (300.0 + 1300.0 * (i % 4), 300.0 + 1700.0 * (i // 4)) for i in range(8)}
    members = [(dict(name=f'r{i}'), f'dc_root_r{i}') for i in range(8)]
    rmodel = {f'r{i}': (400.0 if i == 0 else 0.0) for i in range(8)}
    b = rt.Builder(g, 'dc_spine', r_of=lambda k: rmodel[k])
    rec = b.build('g/p0', (100.0, 5900.0), rt.spine_leaves(members, xy))
    pins = [l[1] for _, _, ls in b.nets for l in ls if l[0] == 'pin']
    assert sorted(pins) == sorted(f'{rb}/A' for _, rb in members)
    bufs = [l[1] for _, _, ls in b.nets for l in ls if l[0] == 'buf']
    assert len(bufs) == len(set(bufs)) == len(b.bufs)
    assert rec['leaves'] == 8 and rec['model_insertion_ps'] > 400.0


def test_forwarded_spine_has_no_pads():
    # QW-DIECLK 10-19: balance false = forwarded regional spine: no pads even with a 4 ns region-insertion spread
    g = rt.dct.Grid(6000.0, 6000.0, [(2000.0, 2000.0, 4000.0, 4000.0)])
    xy = {f'dc_root_r{i}': (300.0 + 1300.0 * (i % 4), 300.0 + 1700.0 * (i // 4)) for i in range(8)}
    members = [(dict(name=f'r{i}'), f'dc_root_r{i}') for i in range(8)]
    bal = rt.Builder(g, 'dc_spine', r_of=lambda k: 4000.0 if k == 'r0' else 0.0)
    bal.build('g/p0', (100.0, 5900.0), rt.spine_leaves(members, xy))
    fwd = rt.Builder(g, 'dc_spine', pads=False)
    rec = fwd.build('g/p0', (100.0, 5900.0), rt.spine_leaves(members, xy))
    assert sum(1 for b in bal.bufs if b[1] == rt.PAD) > 50
    assert rec['pads'] == 0 and not any(b[1] == rt.PAD for b in fwd.bufs)
    pins = [l[1] for _, _, ls in fwd.nets for l in ls if l[0] == 'pin']
    assert sorted(pins) == sorted(f'{rb}/A' for _, rb in members)


def test_spt_spine_bounded_depth_vs_dme():
    # QW-DIECLK6 10-20: forwarded spine topology 'spt' (shortest-path tree): every entry driven exactly once, no pads,
    # every buffer->buffer hop <= SEG_MAX, and depth/insertion below the zero-skew DME on a hard-column floorplan
    import random
    random.seed(7)
    W, H = 12000.0, 9000.0
    obs = [(x, 600.0, x + 450.0, 8400.0) for x in range(1000, 11000, 1400)]
    g = rt.dct.Grid(W, H, obs)
    xy = {}
    for i in range(96):
        while True:
            x, y = random.uniform(100, W - 100), random.uniform(100, H - 100)
            if g.free(g.cell(x, y)):
                break
        xy[f'dc_root_r{i}'] = (x, y)
    members = [(dict(name=f'r{i}'), f'dc_root_r{i}') for i in range(96)]
    rt.SAFE = True
    try:
        dme = rt.Builder(g, 'dc_spine', pads=False)
        rd = dme.build('g/p0', (W / 2, H / 2), rt.spine_leaves(members, xy))
        spt = rt.Builder(g, 'dc_spine', pads=False, topo='spt')
        rs = spt.build('g/p0', (W / 2, H / 2), rt.spine_leaves(members, xy))
    finally:
        rt.SAFE = False
    pins = [l[1] for _, _, ls in spt.nets for l in ls if l[0] == 'pin']
    assert sorted(pins) == sorted(f'{rb}/A' for _, rb in members)
    loads = [l[1] for _, _, ls in spt.nets for l in ls if l[0] == 'buf']
    assert len(loads) == len(set(loads)) == len(spt.bufs)
    assert rs['pads'] == 0 and rs['topology'] == 'spt' and not spt.violations, spt.violations[:3]
    pos = {b[0]: (b[2], b[3]) for b in spt.bufs}
    hop = max(abs(pos[x][0] - pos[p][0]) + abs(pos[x][1] - pos[p][1]) for x, p in spt.parent.items() if x in pos and p in pos)
    assert hop <= rt.SEG_MAX + rt.GRID, hop
    assert rs['tree_depth'] < rd['tree_depth'] and rs['tree_model_ps'] < rd['tree_model_ps'], (rs, rd)


if __name__ == '__main__':
    for k, f in list(globals().items()):
        if k.startswith('test_'):
            f()
    print('SPINE TESTS PASS')
