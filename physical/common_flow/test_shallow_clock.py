import importlib.util
from pathlib import Path
import pytest

P=Path(__file__).resolve().parent/'shallow_clock.py'
spec=importlib.util.spec_from_file_location('shallow_clock',P)
S=importlib.util.module_from_spec(spec);spec.loader.exec_module(S)


def geometry(n=35):
    return dict(dbu=1000,core=[0,0,400000,400000],root=[4000,4000],root_name='clk',
                master='BUFx24',width=1600,height=270,
                rows=[[0,270*j,54,270,7400,'MX' if j%2 else 'R0'] for j in range(1480)],
                cells=[['logic',180000,190080,210000,190350,0]],
                taps=[dict(name=f'ot_dtap_{i}',xy=[20000+i%11*30000,20000+i//11*30000]) for i in range(n)])


@pytest.mark.parametrize('n',[1,8,35,122])
def test_every_tap_has_one_equal_depth_driver_on_free_legal_rows(n,tmp_path):
    g=geometry(n);p=S.plan(g,max_hop_um=1000)
    S.validate(p)
    assert p['summary']['trunk_levels']<=5
    assert p['summary']['added_cycles']==0
    for node in p['nodes']:
        x,y=node['ll']
        assert x%54==0 and y%270==0
        assert node['orient']==('MX' if y//270%2 else 'R0')
        assert not (x<210000 and x+1600>180000 and y<190350 and y+270>190080)
    S.emit_apply(p,tmp_path/'apply.tcl')
    assert (tmp_path/'apply.tcl').read_text().count('ot_dtsh::leaf ')==n


def test_uncovered_clock_endpoint_and_cycle_are_rejected():
    p=S.plan(geometry())
    p['edges'].pop()
    with pytest.raises(ValueError,match='missing root or tap'):S.validate(p)
    p=S.plan(geometry());p['edges'].append([p['nodes'][-1]['name'],p['nodes'][0]['name']])
    with pytest.raises(ValueError):S.validate(p)


def test_no_free_site_fails_instead_of_displacing_data_flops():
    g=geometry();g['cells']=[['filled',0,0,400000,400000,0]]
    with pytest.raises(ValueError,match='no free row'):S.plan(g)


@pytest.mark.parametrize('n',[1,8,35,122])
def test_balanced_plan_is_legal_equal_depth_and_covers_every_tap(n,tmp_path):
    g=geometry(n);p=S.plan_balanced(g,fanout=3,leaf_fanout=4,max_hop_um=1000)
    S.validate(p)
    assert p['summary']['mode']=='balanced' and p['summary']['added_cycles']==0
    for node in p['nodes']:
        x,y=node['ll']
        assert x%54==0 and y%270==0
        assert not (x<210000 and x+1600>180000 and y<190350 and y+270>190080)
    S.emit_apply(p,tmp_path/'apply.tcl')
    assert (tmp_path/'apply.tcl').read_text().count('ot_dtsh::leaf ')==n


def test_balanced_plan_beats_count_median_on_a_far_tap_cluster():
    # a dense cluster near the port plus a sparse far edge band: the count-median plan() mixes them
    g=geometry(0)
    g['taps']=[dict(name=f'ot_dtap_{i}',xy=[150000+i%6*8000,30000+i//6*8000]) for i in range(36)]
    g['taps']+=[dict(name=f'ot_dtap_{36+i}',xy=[20000+i*30000,380000]) for i in range(12)]
    m=S.model_arrivals(S.plan(g,max_hop_um=1000));spread0=max(m.values())-min(m.values())
    m=S.model_arrivals(S.plan_balanced(g,fanout=3,leaf_fanout=4,max_hop_um=1000));spread1=max(m.values())-min(m.values())
    assert spread1<spread0


def test_geo_split_respects_capacity():
    pts=[dict(name=f't{i}',xy=[i*1000,0]) for i in range(10)]
    gs=S.split_geo(pts,3,4)
    assert sum(len(x) for x in gs)==10 and max(len(x) for x in gs)<=4
