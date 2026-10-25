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
