import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import uarch_model as U
import qwen_hbmacc_core_admission_emit as C
import qwen_rom_rt_core_emit_w12 as E
import pytest

@pytest.mark.parametrize('tp,groups', [(2,96),(4,48)])
def test_composed_advance_price(tp,groups):
    m=U.qwen_hbm_registered_admission_model(tp,100,4)
    assert m['gross_added_engine_service_cycles']==200
    assert m['added_token_cycles'] is None and m['added_token_ns'] is None
    assert m['current_source_full_token_slowdown_upper_bound'] is None
    assert m['current_source_layer_slowdown_upper_bound'] is None
    assert m['candidate_verdict']=='REJECTED_AS_SPEED_OPTIMIZATION'
    assert m['token_speedup'] is None
    assert m['engine_advance_ii']==3
    assert m['added_ff_bits_per_die']==20
    assert m['result_enable_fanout']==groups
    assert m['token_rate'] is None and not m['adoption']

@pytest.mark.parametrize('bad',[True,-1,1.5])
def test_count_contract(bad):
    with pytest.raises(ValueError): U.qwen_hbm_registered_admission_model(engine_advances=bad)

def test_default_off_inverse_and_same_edge_issue():
    emitted=C.emit()
    restored=emitted.replace('module ot_qwen_rom_core_admission #(', 'module ot_qwen_rom_core #(')
    restored=restored.replace('    parameter integer ME_ADMISSION_PIPE = 0,\n','')
    restored=restored.replace('wire me_issue_ok = (ME_ADMISSION_PIPE != 0) ? (me_en && !me_rd_presented) : ((ME_ISSUE_RE != 0) ? !me_rd_presented : me_en);', 'wire me_issue_ok = (ME_ISSUE_RE != 0) ? !me_rd_presented : me_en;')
    restored=restored.replace((ROOT/'rtl/hdc/ot_hdc_isa.svh').read_text(),'`include "ot_hdc_isa.svh"')
    src=(ROOT/'results/rtl/qwen_hbm_registered_admission_20261005/sources/ot_hdc_core_vector_weight_f12.sv').read_text()
    expected=E.emit(src.replace('module ot_hdc_core_vector_weight_f12 #(', 'module ot_hdc_core_vector_weight #('))
    assert restored==expected
    assert 'assign me_go = issue && (d_unit == 2\'d1);' in emitted
    assert 'assign vw_me_we = me_o_we &' in emitted
