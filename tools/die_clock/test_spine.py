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


def test_forwarded_delivery_has_no_seed_compensation_and_bounded_fanout():
    g = rt.dct.Grid(6000.0, 6000.0, [(2000.0, 2000.0, 4000.0, 4000.0)])
    xy = {f'dc_root_r{i}': (300.0 + 1300.0 * (i % 4), 300.0 + 1700.0 * (i // 4)) for i in range(8)}
    members = [(dict(name=f'r{i}'), f'dc_root_r{i}') for i in range(8)]
    b = rt.ForwardedBuilder(g, 'forward')
    rec = b.build('g/p0', (100.0, 5900.0), rt.spine_leaves(members, xy))
    pins = [p[1] for _, _, loads in b.nets for p in loads if p[0] == 'pin']
    assert sorted(pins) == sorted(f'{rb}/A' for _, rb in members)
    inputs = [p[1] for _, _, loads in b.nets for p in loads if p[0] == 'buf']
    assert len(inputs) == len(set(inputs)) == len(b.bufs)
    assert all(len(loads) <= 2 for _, _, loads in b.nets)
    assert all(cell != rt.PAD for _, cell, _, _ in b.bufs)
    assert rec['pads'] == 0 and not rec['region_insertion_compensated']
    positions = {n: (x,y) for n,_,x,y in b.bufs}
    positions.update({f'{rb}/A': p for rb,p in xy.items()})
    positions['g/p0'] = (100.0,5900.0)
    for _, driver, loads in b.nets:
        for load in loads:
            p,q=positions[driver[1]],positions[load[1]]
            assert abs(p[0]-q[0])+abs(p[1]-q[1]) <= 405.0


def test_forwarded_route_rejects_unbuffered_macro_escape():
    # The inherited grid's diagnostic fallback would cross 1.2 mm of macro.
    class NoCorridor:
        def _route(self, a, b, max_run):
            raise ValueError('no legal repeater corridor')
        def route(self, a, b):
            raise AssertionError('unsafe diagnostic fallback was called')
    b = rt.ForwardedBuilder(NoCorridor(), 'reject')
    try:
        b.path((0,0),(100,100))
    except ValueError:
        pass
    else:
        raise AssertionError('forwarded route accepted unreachable entry')


if __name__ == '__main__':
    for k, f in list(globals().items()):
        if k.startswith('test_'):
            f()
    print('SPINE TESTS PASS')
