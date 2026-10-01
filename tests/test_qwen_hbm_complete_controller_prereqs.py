"""Independent geometry controls; no actual controller execution."""
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from qwen_hbm_complete_controller_prereqs import model
ROOT=Path(__file__).resolve().parents[1]

def test_full_queue_epoch_and_pending_write_storage_not_free():
    r=model(ROOT);s=r['controller_extension_state']
    assert s['queue_transport_epoch_bits']==8*32*96*32==786432
    assert s['queue_producer_epoch_bits']==8*32*96*64==1572864
    assert s['queue_epoch_bits']==2359296
    assert s['write_pending_bits']==8*4*(16+32+64+34+256+64+1)==14944
    assert s['total_bits']==2374296
    assert not r['hardware_build_ready'] and r['total_token_cycles'] is None
    assert r['source_defaults']['LENW']==5 and r['proposed_geometry']['LENW']==6

def test_queue_scaling_counts_each_physical_PC_and_pending_depth():
    a=model(ROOT);b=model(ROOT,qd=128,rqd=64,write_depth=8)
    assert b['controller_extension_state']['queue_epoch_bits']==2*a['controller_extension_state']['queue_epoch_bits']
    assert b['controller_extension_state']['write_pending_bits']==2*a['controller_extension_state']['write_pending_bits']

@pytest.mark.parametrize('kw',[{'qd':16},{'rqd':0},{'write_depth':0}])
def test_underprovisioned_or_infinite_missing_queue_rejects(kw):
    with pytest.raises(ValueError,match='finite queues'):model(ROOT,**kw)


def test_pending_depth_prices_stalls_and_perPC_not_stack_column_constraint():
    r=model(ROOT);s=r['pending_write_service']
    assert s['column_to_backing_visibility_ps']==7274
    assert s['hypothetical_shared_column_bounds']['single_shared_1024ps']['minimum_pending_before_visibility']==8
    assert s['hypothetical_shared_column_bounds']['hypothetical_shared_fast']['minimum_pending_before_visibility']==9
    assert s['source_unquantized_envelope_pending_per_stack']==256
    assert s['quantized_per_PC_calendar']['source_1000ps']['pending_all32_PC_per_stack']==128
    assert s['quantized_per_PC_calendar']['target_fast_2500over3ps']['pending_all32_PC_per_stack']==160
    assert not s['first_wave_fits']
    assert s['hypothetical_shared_column_bounds']['single_shared_1024ps']['minimum_pending_through_RSP']==17
    assert s['hypothetical_shared_column_bounds']['hypothetical_shared_fast']['minimum_pending_through_RSP']==21
    assert s['depth_candidate_visible_only_ceiling_writes_per_second']==pytest.approx(4e12/7274)
    assert not s['depth_selected']
    assert r['timestamp_scope']['hardware_timer_bits'] is None
    assert not r['timestamp_scope']['wrap_or_counter_credit']


def test_full_fast_visibility_window_storage_is_priced_not_fourentry_screen():
    r=model(ROOT,write_depth=160)
    assert r['pending_write_service']['target_fast_visibility_window_fits']
    assert r['controller_extension_state']['write_pending_bits']==8*160*467
    assert not r['hardware_build_ready']


def test_source_epoch64_is_not_transport_epoch32_or_unpriced_highhalf():
    r=model(ROOT)
    assert r['source_epoch_contract']['producer_epoch_bits']==64
    assert not r['source_epoch_contract']['source_epoch_narrowing_allowed']
    assert r['controller_extension_state']['write_pending_fields']['producer_epoch']==64
    assert r['additional_common36_held_epoch_bits']['total']==1024+512+512+4608
    assert r['source_epoch_contract']['actual_binding'] is None
