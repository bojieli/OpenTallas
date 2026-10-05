import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from qwen_hbm_lookup_banking_model_r18 import model

def test_shared_output_and_hot_PC_limit_survive_banking():
    b=model()
    assert b['service_bounds']['uniform_optimistic_bytes_per_second_at_1GHz']==16e9
    assert b['service_bounds']['hot_single_PC_bytes_per_second_at_1GHz']==b['retained_original']['optimistic_bytes_per_second_at_1GHz']
    assert b['service_bounds']['32PC_uniform_lookup_sector_ceiling_per_edge']>.5
    assert not b['service_bounds']['measured_or_guaranteed_bandwidth']

def test_no_free_storage_or_slot_credit():
    b=model()
    assert b['extra_FF_bits_per_stack']==25120
    assert b['replacement_credit_mm2']==0
    assert b['slot_margin_after_extra_mm2']<0
    assert not b['slot_fit']
    assert b['ports']['root_retire_transactions_per_edge']==1
    assert not any(b['qualification'].values())
