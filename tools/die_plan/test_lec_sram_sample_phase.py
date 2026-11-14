"""Synchronous SRAM WD uses real Liberty edge and same-instance clock witnesses."""
import json,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import lec

MOD='ot_sram_1r1w_32x128_m1_p192_rc'
PORTS={MOD:[('clk','input',1,0),('wd_in','input',2,0)]}

def _lib(tmp_path,edge='rising',clock='clk',ram=True,module=MOD):
    p=tmp_path/(edge+clock+module+'.lib')
    p.write_text('''library (x) {type (word) {bit_width : 2;}
      cell (MODULE) {MEMORY pin (clk) {direction : input; clock : true;}
      bus (wd_in) {bus_type : word; direction : input;
        timing () {related_pin : "CLOCK"; timing_type : setup_EDGE;}
        timing () {related_pin : "CLOCK"; timing_type : hold_EDGE;}}
      }}'''.replace('MODULE',module).replace('MEMORY','memory () {type : ram;}' if ram else '')
        .replace('CLOCK',clock).replace('EDGE',edge))
    return p

def test_liberty_qualifies_only_real_rising_ram(tmp_path):
    assert lec.synchronous_sram_samples(PORTS,[_lib(tmp_path)])=={MOD:{'wd_in':'clk'}}
    for p in [_lib(tmp_path,edge='falling'),_lib(tmp_path,clock='other'),_lib(tmp_path,ram=False)]:
        assert lec.synchronous_sram_samples(PORTS,[p])=={}
    non='hard_core';assert lec.synchronous_sram_samples({non:PORTS[MOD]},[_lib(tmp_path,module=non)])=={}

def test_disagreeing_views_do_not_qualify(tmp_path):
    assert lec.synchronous_sram_samples(PORTS,[_lib(tmp_path),_lib(tmp_path,edge='falling')])=={}

def test_stub_carries_explicit_module_and_clock_metadata():
    text=lec.stub_verilog(PORTS,sram_samples={MOD:{'wd_in':'clk'}})
    assert 'lec_bb_module = "'+MOD+'"' in text
    assert 'lec_sample_edge = "rising", lec_sample_clock = "clk"' in text
    assert 'lec_sample_edge' not in lec.stub_verilog(PORTS)

def _json(tmp_path,marked=True,edge='rising',clock=2,phase='low',port='wd_in',module=MOD):
    def ff(d,q,c=2):return {'type':'$_DFF_P_','connections':{'C':[c],'D':[d],'Q':[q]},'port_directions':{'C':'input','D':'input','Q':'output'}}
    a={'lec_bb_module':module,'lec_bb_input':port,'lec_sample_edge':edge,'lec_sample_clock':'clk'} if marked else {}
    cells={'src':ff(4,20),'hold':{'type':'$_DLATCH_N_' if phase=='low' else '$_DLATCH_P_',
      'connections':{'E':[2],'D':[20],'Q':[21]},'port_directions':{'E':'input','D':'input','Q':'output'}},
      'macro_wd':ff(21,30,99),'macro_ck':ff(clock,31,99)}
    nets={'src':{'bits':[20]},'u_m.lec_bbi_'+port:{'bits':[30],'attributes':a},
      'u_m.lec_bbi_clk':{'bits':[31],'attributes':{'lec_bb_module':module,'lec_bb_input':'clk'}},'hold':{'bits':[21]}}
    m={'attributes':{'top':'1'},'ports':{n:{'direction':'input','bits':[b]} for n,b in [('clk',2),('other_clk',3),('d',4)]},'cells':cells,'netnames':nets}
    p=tmp_path/'input.json';p.write_text(json.dumps({'modules':{'lec_top':m}}));return p

def test_qualified_sram_data_latch_is_modelled(tmp_path):
    r=lec.latch_to_wire(_json(tmp_path),tmp_path/'out.json','gold')
    assert r['phases']=={'low':1}

@pytest.mark.parametrize('options',[{'marked':False},{'edge':'falling'},{'clock':3},{'phase':'high'},{'port':'w_ce_in'}])
def test_missing_wrong_or_unmatched_witness_is_blocked(tmp_path,options):
    with pytest.raises(lec.Unproven):lec.latch_to_wire(_json(tmp_path,**options),tmp_path/'out.json','gold')

def test_fresh_hard_core_policy_is_preserved(tmp_path):
    r=lec.latch_to_wire(_json(tmp_path,module='kid',edge='none',clock=3),tmp_path/'out.json','gold')
    assert r['phases']=={'low':1}
