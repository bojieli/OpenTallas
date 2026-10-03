import importlib.util,json
from pathlib import Path
import pytest
spec=importlib.util.spec_from_file_location('mapped',Path(__file__).resolve().parents[1]/'tools/w2_full_controller_mapped_census.py');M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
F='DFFASRHQNx1_ASAP7_75t_R'
def fixture():
 facts={'cells':{F:dict(area_um2=.5184,sequential=True,latch=False,pins={'QN':{'direction':'output'},'D':{'direction':'input'},'CLK':{'direction':'input','cap_fF':.434}},leakage_W=1e-9)},'libraries':{'TEST_ONLY':{}}}
 cells={f'ff{i}':{'type':F,'connections':{'QN':[100+i],'D':[3],'CLK':[2]}} for i in range(15768)}
 nets={f'cw[{i}]':{'bits':list(range(100+i*72,100+(i+1)*72))} for i in range(219)}
 return {'modules':{'TEST_ONLY':{'attributes':{'top':1},'cells':cells,'netnames':nets}}},facts

def test_full_unique_bit_trace_and_area_replication():
 net,facts=fixture();d=M.census(net,facts)
 assert d['full219_storage_census_PASS'] and d['cw_distinct_flop_cells']==15768
 assert d['actual_flop_cells']==15768
 assert d['area_um2']==pytest.approx(15768*.5184)
 assert d['replication1280']['mapped_body_mm2']==pytest.approx(15768*.5184/1e6*1280)
 assert d['latency']['actual_service_cycles_or_whole_token_delta'] is None

def test_full_total_flop_count_does_not_mask_CW_alias():
 net,facts=fixture();net['modules']['TEST_ONLY']['netnames']['cw[0]']['bits'][0]=172
 d=M.census(net,facts)
 assert d['actual_flop_cells']==15768 and d['cw_logical_bits']==15768
 assert not d['full219_storage_census_PASS'] and d['cw_distinct_flop_cells']==15767

def test_pruned_CW_constant_is_not_a_storage_bit():
 net,facts=fixture();net['modules']['TEST_ONLY']['netnames']['cw[0]']['bits'][0]='0'
 d=M.census(net,facts);assert not d['full219_storage_census_PASS'];assert d['cw_nonstate_or_constant_bits']==1

def test_unmapped_or_foreign_cell_rejected():
 net,facts=fixture();net['modules']['TEST_ONLY']['cells']['ff0']['type']='$adff'
 with pytest.raises(ValueError,match='nonproduction/unmapped'):M.census(net,facts)

def test_QN_restore_traces_actual_ff_without_counting_INV_as_storage():
 net,facts=fixture();facts['cells']['INV_TEST']=dict(area_um2=.07,sequential=False,latch=False,pins={'A':{'direction':'input'},'Y':{'direction':'output'}},leakage_W=1e-10)
 net['modules']['TEST_ONLY']['cells']['restore']={'type':'INV_TEST','connections':{'A':[100],'Y':[50000]}}
 net['modules']['TEST_ONLY']['netnames']['cw[0]']['bits'][0]=50000
 d=M.census(net,facts);assert d['full219_storage_census_PASS'];assert d['actual_flop_cells']==15768

def test_actual_liberty_units_and_ff_group(tmp_path):
 p=tmp_path/'TEST_ONLY.lib';p.write_text('library(TEST) { leakage_power_unit : "1nW"; capacitive_load_unit(1,pf); cell(DFF) { area : 0.5184; cell_leakage_power : 2.5; ff(IQ,IQN) { next_state : "D"; clocked_on : "CLK"; } pin(CLK) { direction : input; capacitance : 0.000434; } pin(QN) { direction : output; function : "IQN"; } } }')
 d=M.liberty_facts([p]);assert d['cells']['DFF']['sequential'];assert d['cells']['DFF']['pins']['CLK']['cap_fF']==pytest.approx(.434);assert d['cells']['DFF']['leakage_W']==pytest.approx(2.5e-9)
