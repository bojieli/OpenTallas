import copy
import hashlib
import json
from pathlib import Path
import pytest
import signoff
from test_signoff import record


def library(path, marker=True, macro=True, values='170.0', master='child'):
    clock='''pin(clk) { clock : true; timing() { timing_type : max_clock_tree_path; cell_rise(scalar) { values("VALUE"); } } }'''.replace('VALUE',values) if marker else ''
    text='library(x) { time_unit : "1ps"; cell("MASTER") { is_macro_cell : MACRO; CLOCK pin(Q) { direction : output; timing() { related_pin : "clk"; timing_type : rising_edge; cell_rise(scalar) { values("300"); } } } } }'
    path.write_text(text.replace('MASTER',master).replace('MACRO',str(macro).lower()).replace('CLOCK',clock))
    return path


def test_actual_marker_blocks_expanded_admission_but_preserves_raw_pairs(tmp_path):
    lib=library(tmp_path/'child_tt.lib')
    coverage=signoff.clock_model_coverage([lib],['child'])
    assert coverage['status']=='UNEXPANDED_CHILD_ETM' and coverage['verdict']=='NOT RUN'
    assert coverage['models'][0]['master']=='child'
    assert coverage['models'][0]['liberty_sha256']==hashlib.sha256(lib.read_bytes()).hexdigest()
    rec=record();raw=copy.deepcopy(rec['corners']['tt']['pair_skew'])
    rec['corners']['tt']['clock_endpoint_coverage']=coverage
    result=signoff.evaluate(rec)
    assert result['checks']['clock']['verdict']=='NOT RUN'
    assert result['verdict']=='NOT SIGNED'
    assert result['corners']['tt']['pair_skew']==raw
    assert raw['checks']['max']['worst_abs_ps']<80  # would otherwise pass


@pytest.mark.parametrize('marker,macro,values',[(False,True,'170'),(True,True,'0'),(True,False,'170')])
def test_ordinary_sram_and_native_controls_remain_admitted(tmp_path,marker,macro,values):
    lib=library(tmp_path/'sram_tt.lib',marker,macro,values,'sram')
    coverage=signoff.clock_model_coverage([lib],['sram'])
    assert coverage['status']=='NO_UNEXPANDED_CHILD_ETM'
    rec=record()
    for c in ('tt','ff'):rec['corners'][c]['clock_endpoint_coverage']=coverage
    result=signoff.evaluate(rec)
    assert result['checks']['clock']['verdict']=='PASS'
    assert result['verdict']=='SIGNED'


def test_unused_etm_does_not_block_actual_native_endpoint(tmp_path):
    lib=library(tmp_path/'unused_tt.lib')
    assert signoff.clock_model_coverage([lib],['DFFHQNx1_ASAP7_75t_R'])['verdict']=='PASS'


def test_invalid_or_unavailable_model_inventory_fails_closed(tmp_path):
    lib=library(tmp_path/'child_tt.lib',values='NaN')
    assert signoff.clock_model_coverage([lib],['child'])['status']=='UNAVAILABLE'
    assert signoff.clock_model_coverage([lib],None)['verdict']=='NOT RUN'


def test_consumed_receipt_is_exact_hash_and_master_bound(tmp_path):
    lib=library(tmp_path/'child_tt.lib')
    receipt=tmp_path/'libraries.json'
    row={'path':'/work/child_tt.lib','sha256':hashlib.sha256(lib.read_bytes()).hexdigest()}
    receipt.write_text(json.dumps({'status':'LOADED','libraries':[row]}))
    found=signoff.consumed_clock_model_coverage(receipt,{'kit':str(tmp_path)},['child'])
    assert found['status']=='UNEXPANDED_CHILD_ETM'
    assert found['models'][0]['consumed_liberty']=='/work/child_tt.lib'
    row['sha256']='bad';receipt.write_text(json.dumps({'status':'LOADED','libraries':[row]}))
    assert signoff.consumed_clock_model_coverage(receipt,{'kit':str(tmp_path)},['child'])['status']=='UNAVAILABLE'


def test_characterized_native_library_only_case(tmp_path):
    receipt=tmp_path/'libraries.json'
    receipt.write_text(json.dumps({'status':'LOADED','libraries':[{'path':'/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib','sha256':'native'}]}))
    result=signoff.consumed_clock_model_coverage(receipt,{'kit':str(tmp_path)},['DFFHQNx1_ASAP7_75t_R'])
    assert result['status']=='NO_UNEXPANDED_CHILD_ETM'
    assert signoff.consumed_clock_model_coverage(receipt,{'kit':str(tmp_path)},['DFF'],1)['verdict']=='NOT RUN'
