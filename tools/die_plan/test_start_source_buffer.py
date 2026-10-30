"""Shared DATA cuts must not reuse hidden/unused native bit or instance identity."""
import copy,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import start_source_buffer as B

def fixture():
    cells={'ff':dict(type='DFFHQNx1_ASAP7_75t_R',connections={'CLK':[1],'D':['0'],'QN':[2]}),
           'inv':dict(type='INVx1_ASAP7_75t_R',connections={'A':[2],'Y':[3]}),
           'capture':dict(type='DFFHQNx1_ASAP7_75t_R',connections={'CLK':[1],'D':[3],'QN':[4]})}
    m={'modules':{'ot_die_start_stages':dict(cells=cells,ports={'clk':dict(direction='input',bits=[1]),'unused_native':dict(direction='output',bits=[100000])},netnames={'unconsumed_native_name':dict(bits=[200000],attributes={})})}}
    s=dict(region='st:h',signal='start',instance='inv',master='INVx1_ASAP7_75t_R',output_bit=3,all_output_sinks=[dict(kind='iterm',instance='capture',pin='D')])
    return {'source_records':[s]},m

def test_allocate_after_unused_native_ports_and_names():
    i,m=fixture();old=copy.deepcopy(m);new,receipt=B.insert(i,m)
    assert m==old
    assert receipt['heads'][0]['output_bit']==200001
    assert new['modules']['ot_die_start_stages']['ports']==old['modules']['ot_die_start_stages']['ports']
    assert receipt['added_cycles']==receipt['added_flops']==0

def test_existing_head_name_is_refused():
    i,m=fixture();_,receipt=B.insert(i,m);name=receipt['heads'][0]['instance'];m['modules']['ot_die_start_stages']['cells'][name]=dict(type=B.BUF,connections={'A':[7],'Y':[8]})
    with pytest.raises(ValueError,match='namespace'):B.insert(i,m)

def test_inverted_head_cannot_pass_state_bridge():
    i,m=fixture();new,r=B.insert(i,m);p=new['modules']['ot_die_start_stages'];p['cells'][r['heads'][0]['instance']]['type']='INVx1_ASAP7_75t_R'
    with pytest.raises(ValueError,match='Boolean'):B.check_bridge(m['modules']['ot_die_start_stages'],p,r['heads'])
