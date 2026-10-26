"""Physical free-site paths must satisfy bounds after row/macro legalization."""
import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location('strict_clock', Path(__file__).with_name('shallow_clock.py'))
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)


def geometry():
    return dict(dbu=1000, core=[0,0,400000,400000], root=[0,200000],
                master='BUF', width=1000, height=1000,
                rows=[[0,y,1000,1000,400,'R0'] for y in range(0,400000,1000)],
                cells=[['rom',100000,100000,300000,300000,1]],
                taps=[dict(name='ot_dtap_0',xy=[80000,200000]),
                      dict(name='ot_dtap_1',xy=[320000,200000])])


def test_wide_macro_uses_bounded_free_site_path():
    g=geometry()
    nav=S.ClockNavigation(g, [[80000,200000],[320000,200000]], 80)
    path=nav.path([80000,200000],[320000,200000])
    assert all(S._man(a,b)<=80000 for a,b in zip(path,path[1:]))
    assert sum(S._man(a,b) for a,b in zip(path,path[1:]))>240000
    assert all(not (100000<x<300000 and 100000<y<300000) for x,y in path)


def test_strict_plan_bounds_actual_edges_and_preserves_equal_stages():
    p=S.plan_legs(geometry(),rmax_um=100,strict_geometry=True)
    S.validate(p)
    assert p['summary']['max_hop_um']<=100
    assert p['summary']['strict_geometry']
    assert p['summary']['added_cycles']==0


def test_strict_cluster_rejects_over_four_starts():
    with pytest.raises(ValueError,match='at most four'):
        S.plan_legs(geometry(),fanout=5,strict_geometry=True)


def test_bisection_depth_enforces_declared_leaf_load():
    g=geometry()
    g['cells']=[]
    g['taps']=[dict(name=f'ot_dtap_{i}',xy=[30000+(i%3)*80000,30000+(i//3)*80000]) for i in range(9)]
    p=S.plan_legs(g,leaf_fanout=2,strict_geometry=True)
    for cl in p['clusters']:
        outgoing=[p['legs'][i] for i in cl['legs']]
        assert len(outgoing)<=4
        if outgoing[0]['child'][0]=='tap':
            assert len(outgoing)<=2
