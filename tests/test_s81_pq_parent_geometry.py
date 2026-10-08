import importlib.util
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]

def module(name):
    s=importlib.util.spec_from_file_location(name,ROOT/f'tools/s81/{name}.py')
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
G=module('pq_parent_geometry');V=module('pq_geometry_views')


def test_actual_macro_bank_layout_and_identity():
    core=G.F.Inst('core','candidate',0,0,1727.976,G.CORE_HEIGHT)
    p=G.core_children(core)
    assert p['legality']['PASS'] and p['SRAM_macros']==36 and p['ROM_macros']==3
    names={x['name']for x in p['children']}
    assert all(f'bb_replica{r}_bank{b}'in names for r in range(4)for b in range(8))
    assert all(f'qb_bank{b}'in names for b in range(4))


def test_historical_core_width_is_rejected():
    with pytest.raises(ValueError):G.core_children(G.F.Inst('core','old',0,0,1015.176,794.904))


def test_macro_overlap_or_escape_does_not_pass():
    a=dict(name='a',x=0,y=0,w=20,h=20);b=dict(name='b',x=19,y=19,w=20,h=20)
    assert G.check_boxes([a,b],(0,0,100,100))['overlaps']==[('a','b')]
    assert G.check_boxes([a],(1,0,100,100))['outside']==['a']


def test_real_sram_view_pins_and_station_reach():
    v=V.load_lef(ROOT/G.SRAM)
    expected={n:p['direction']for n,p in v['pins'].items()}
    slot=dict(x=0,y=0,w=100,h=45)
    stations=[dict(x=-5,y=0,w=5,h=45)]
    r=V.validate(slot,v,expected,stations)
    assert r['geometry_PASS'] and not r['physical_adopted']
    bad=dict(expected,mandatory_fault='OUTPUT')
    assert V.validate(slot,v,bad,stations)['missing_pins']==['mandatory_fault']
    assert not V.validate(slot,v,expected,[dict(x=-150,y=0,w=5,h=45)])['geometry_PASS']


def test_new_root_row_preserves_nine_full_mixed_slots():
    import argparse,json
    p=json.loads((ROOT/G.BASIS).read_text())
    G.F.apply_options(G.F.die_options(argparse.ArgumentParser()).parse_args(p['run_options'].split()))
    G.F.CHS=tuple(G.F.chh(t)+(G.ROOT_ROW if t<6 else 0)for t in range(7))
    G.F.slot_geometry()
    assert G.F.SLOTS8==9 and G.F._frames_fit(G.F.SLOTS8,G.F.SLOT_H8)
    assert G.F.PAIRS==1792 and G.F.BF_PAIRS==512
