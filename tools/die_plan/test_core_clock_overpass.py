"""Opt-in clock-resource control preserves default/data/child/hook contracts."""
from pathlib import Path
import pytest
from core_clock_overpass import stage_clock_overpass


def setup(kit,obs=5,data='M5'):
    (kit/'macros').mkdir()
    (kit/'macros/child.lef').write_text(f'MACRO child\n CLASS BLOCK ;\n OBS\n  LAYER M{obs} ;\n  RECT 0 0 10 10 ;\n END\nEND child\n')
    text=f'export MAX_ROUTING_LAYER = {data}\nexport PRE_GLOBAL_ROUTE_TCL = /work/old_grt.tcl\nexport PRE_DETAIL_ROUTE_TCL = /work/old_drt.tcl\nexport POST_DETAIL_ROUTE_TCL = /work/old_post.tcl\n'
    (kit/'config.mk').write_text(text)
    return text


def test_default_is_byte_identical(tmp_path):
    text=setup(tmp_path)
    before={p.name:p.read_bytes() for p in tmp_path.iterdir() if p.is_file()}
    assert stage_clock_overpass(tmp_path,None,None,None,[]) is None
    assert before=={p.name:p.read_bytes() for p in tmp_path.iterdir() if p.is_file()}
    assert (tmp_path/'config.mk').read_text()==text


def test_explicit_clock_m6_preserves_data_child_and_previous_hooks(tmp_path):
    original=setup(tmp_path);leaf=(tmp_path/'macros/child.lef').read_bytes()
    receipt=stage_clock_overpass(tmp_path,'M6','M6','M6',[{'master':'child'}])
    assert receipt['child_obs']=={'child':'M5'} and receipt['added_signal_cycles']==0
    assert (tmp_path/'config.mk').read_text().startswith(original)
    for kind,old in (('grt','old_grt'),('drt','old_drt')):
        assert (tmp_path/f'clock_overpass_{kind}_pre.tcl').read_text()==f'source /work/{old}.tcl\nsource /work/clock_overpass.tcl\n'
    assert (tmp_path/'clock_overpass_drt_post.tcl').read_text()=='source /work/old_post.tcl\nsource /work/clock_overpass_audit.tcl\n'
    hook=(tmp_path/'clock_overpass.tcl').read_text()
    assert 'set_routing_layers -clock "$::env(MIN_CLK_ROUTING_LAYER)-M6"' in hook
    assert 'set_routing_layers -signal' not in hook
    assert (tmp_path/'macros/child.lef').read_bytes()==leaf


@pytest.mark.parametrize('top,parent,pg,obs,data,children',[
 ('M7','M6','M6',5,'M5',[{'master':'child'}]),
 ('M6','M5','M6',5,'M5',[{'master':'child'}]),
 ('M6','M6',None,5,'M5',[{'master':'child'}]),
 ('M6','M6','M6',6,'M5',[{'master':'child'}]),
 ('M6','M6','M6',5,'M6',[{'master':'child'}]),
 ('M6','M6','M6',5,'M5',[]),
])
def test_unreviewed_contract_is_refused(tmp_path,top,parent,pg,obs,data,children):
    original=setup(tmp_path,obs,data)
    with pytest.raises(ValueError):stage_clock_overpass(tmp_path,top,parent,pg,children)
    assert (tmp_path/'config.mk').read_text()==original
