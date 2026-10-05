import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).parents[1]/'tools'))
import dsrom_retained_WAKE_context_admission as C
import dsrom_PAR2_mapped_q_growth_join as G

@pytest.fixture(scope='module')
def model():return C.build()

def test_real_retention_closes_only_local_gate(model):
    assert model['geometry_G0']['mapped_q_BF_WAKE_G0_PASS']
    assert not model['context_build_gate']['PnR_admitted']
    assert model['retained_WAKE_context']['old_a910_failure_preserved']

def test_full_root_load_counted(model):
    for name,count in [('q',84),('bfcolumn',261)]:
        c=model['retained_WAKE_context']['classes'][name]
        assert c['clock']['ff']['buffer_cells_construction']==count
        assert c['clock']['ff']['actual_clock_nets']==9

def test_no_field_selector_or_retention_doublecount(model):
    old=G.build()[0]
    assert model['field']==old['field'] and model['selector']==old['selector']
    assert model['area']['combined_noncontainment_policy_screen_mm2']==pytest.approx(old['area']['combined_noncontainment_policy_screen_mm2']+model['area']['retained_full_root_clock_buffer_increment_at50pct_mm2'])

def test_actual_local_capacity_replaces_inference(model):
    q=model['retained_WAKE_context']['classes']['q']
    assert q['actual_geometry_cell_capture_capacity_um2']==36522.3168
    assert q['residual_after_clock_floor_at50pct_um2']==pytest.approx(399.3753599547185)
    assert q['PG_growth_strip_DBU']==[0,144720,510840,151200]

def test_SSFF_exception_is_narrow(model):
    p=model['SS_FF_plan']
    assert (p['setup_uncertainty_ps'],p['hold_uncertainty_ps'])==(60,25)
    assert [e['setup_edges'] for e in p['endpoints']]==[1,2,1,1]
    assert p['input_output_zero_delay_not_admitted']

def test_real_source_completion_kept(model):
    assert model['actual_I66_review']['measured_source_edges']['adapter_retire']==422
    assert model['actual_I66_review']['original_wrapper_verdict']=='FAIL'
