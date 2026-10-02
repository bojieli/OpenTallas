import importlib.util
from pathlib import Path
import pytest,sys
import copy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
s=importlib.util.spec_from_file_location('r2',ROOT/'tools/qwen_rom_fulltile_mapped_gate_r2.py');g=importlib.util.module_from_spec(s);s.loader.exec_module(g)
def net():
 cells={}
 for m in range(10):
  bits=list(range(1000+m*266,1000+(m+1)*266));cells[f'rom{m}']={'type':'ot_rom_4096x266_m8','connections':{'rd_out':bits,'clk':[1]}}
  for b in range(256):cells[f'ff{m}_{b}']={'type':'DFFHQNx1_ASAP7_75t_R','connections':{'D':[bits[b]],'CLK':[1]}}
 return {'cells':cells}
def test_all_payload_pins_have_distinct_same_clock_drivers():assert sum(map(len,g.capture_drivers(net()).values()))==2560
@pytest.mark.parametrize('mutant',['missing','wrong_clock','cross_macro_alias'])
def test_incomplete_or_wrong_capture_driver_refused(mutant):
 n=net()
 if mutant=='missing':del n['cells']['ff0_0']
 elif mutant=='wrong_clock':n['cells']['ff0_0']['connections']['CLK']=[2]
 else:n['cells']['rom1']['connections']['rd_out'][0]=n['cells']['rom0']['connections']['rd_out'][0]
 with pytest.raises(ValueError):g.capture_drivers(n)

def joined_fixture():
 witnesses=g.capture_drivers(net())
 proof={'raw_mapped_sha256':'a'*64,'source_commit':'b'*40,'ROM_payload_bit_to_direct_capture_FF_D':witnesses}
 parent={'map_SHA256':'a'*64,'source_commit':'b'*40,'macros':[{'macro':k,'first256_direct_capture_FF_D':v,'macro_output_width':266} for k,v in witnesses.items()], 'distinct_direct_capture_FFs':2560,'scopeinfo_metadata_cells':2319,'scopeinfo_has_electrical_ports':False,'original_FAIL_preserved':True}
 return proof,parent

def test_independent_witness_join_keeps_scope_partial():
 proof,parent=joined_fixture();result=g.compare_parent_witness(proof,parent)
 assert result['capture_FFs']==2560 and not result['full_control_enable_downstream_qualified']

@pytest.mark.parametrize('mutant',['map','source','order','duplicate_macro','metadata_ports'])
def test_parent_identity_or_order_mutant_refused(mutant):
 proof,parent=joined_fixture();parent=copy.deepcopy(parent)
 if mutant=='map':parent['map_SHA256']='c'*64
 elif mutant=='source':parent['source_commit']='c'*40
 elif mutant=='order':parent['macros'][0]['first256_direct_capture_FF_D'].reverse()
 elif mutant=='duplicate_macro':parent['macros'][1]=parent['macros'][0]
 else:parent['scopeinfo_has_electrical_ports']=True
 with pytest.raises(ValueError):g.compare_parent_witness(proof,parent)
