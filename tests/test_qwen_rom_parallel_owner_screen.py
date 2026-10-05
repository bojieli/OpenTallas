import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import qwen_rom_parallel_owner_screen as S


def test_one_source_sized_candidate_and_no_new_fill():
    m=S.price()
    assert m['owners_per_stack']==14
    assert m['extra_owner_instances_per_rank']==52
    assert m['extra_owner_macros_per_rank']==1664
    assert m['shared_fill_lanes_unchanged']==1
    assert m['source_command_buses_per_stack_unchanged']==1
    assert m['fill_bits_unchanged']==1048


def test_transport_bytes_once_and_old_negative_preserved():
    m=S.price()
    assert m['selected_read_bytes_rank_token']==150690816
    assert m['selected_closing_write_bytes_rank_token']==156672
    assert m['old_current_owner_lower_bound_s']==pytest.approx(.016498944)
    assert m['resident_literal_overflow_mm2_preserved']==pytest.approx(111.97386816)
    assert m['conditional_perfect_compute_overlap_lower_bound_s']==pytest.approx(.00196224)
    assert m['conditional_candidate_rate_ceiling']<510
    assert not m['final_target_prediction']


def test_source_arrays_and_no_admission_or_baseline_credit():
    m=S.price()
    assert sum(m['owner_array_source_bits'].values())==212992
    assert m['extra_owner_source_state_bits']==52*212992
    assert m['named_baseline_component_debits'] is None
    assert not any(m[k] for k in ('complete_area','complete_floorplan_fit','source_map_admission','PnR'))
    assert m['proposed_service_tail_macro_clocks_rank']==2176
    assert m['additional_readiness_predicate_bits_rank']==988


def test_selected_source_anchors_and_receipt_pins():
    import hashlib
    import json
    src=(S.R.ROOT/S.Q.OUT/'inputs/source/rtl/model_ready_hbm_r14/ot_hbm_r14_tag_owner.sv').read_text()
    for anchor in ('reg [4095:0] live;', 'reg [5:0] remaining_PC[0:4095]',
                   'reg [12:0] cam[0:31][0:127]', 'reg [31:0] seen[0:31][0:127]',
                   'if(delay==11)', 'allocated_tag={alloc_bank,free_tag_slot}'):
        assert anchor in src
    for p,h in json.loads((S.R.ROOT/S.OUT/'sourcepins-r1.json').read_text()).items():
        assert hashlib.sha256((S.R.ROOT/p).read_bytes()).hexdigest()==h
    assert json.loads((S.R.ROOT/S.OUT/'model-r1.json').read_text())==S.price()
