import hashlib
import json
import math
import sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import dsrom_current4096_field_receipts as R
@pytest.fixture(scope='module')
def receipt():return R.build()
def test_exact_receipt_reproduction(receipt):
    assert receipt==json.loads((R.OUT/'receipt-r4.json').read_text())
    assert receipt['owner_inventory_committed_source']==R.NASH
    assert not receipt['owner_generator_executed']
def test_actual_archived_header_coverage_no_payload(receipt):
    h=receipt['header_census']
    assert h['shards']==48 and h['tensor_keys']==96085
    assert h['routed_expert_count']=={'weight':46080,'scale':46080}
    assert h['backbone_BF16_tensor_count']==231
    assert h['backbone_nonexpert_tensor_count']==1255
    assert h['checkpoint_payload_bytes_read']==0
    assert h['Engram_table_metadata_separated_from_layer_field']['table_role_not_layer_compute']
def test_pair_slot_macro_counts_and_nonuniform_stage_total(receipt):
    i=receipt['current4096_inventory']
    assert i['total_analytical_pairs']==781840
    assert i['total_complete_element_slots']==1563680
    assert i['total_physical4096_macros']==3127360
    assert i['busiest_pairs']==4773 and i['busiest_BF16_column_pairs']==1024
    assert i['busiest_complete_slots']==9546 and i['busiest_physical_macros']==19092
    assert i['total_analytical_pairs']<4773*164
    assert not i['executable_tensor_bank_owner_bound']
def test_return_lower_bound_and_unresolved_provider(receipt):
    r=receipt['full_return']
    assert (r['NP'],r['roots'],r['nodes'])==(8192,128,16256)
    assert r['storage_lower_bound_bits']==138469120
    assert not r['native_area_or_dedup_credit_proven']
    assert r['all_links_bits_per_cycle']==2121600
def test_old_fail_and_hard_abstract_not_transferred(receipt):
    p=receipt['physical'];n=receipt['retained_negative']
    assert p['historical_q_hard_outline_um']==[513.756,131.76]
    assert not p['current_q_and_BF_hard_abstracts_available']
    assert p['additional_service_proxy_debit_mm2']==0
    assert n['historical8192_proposed_hub_collision_count']==2550
    assert n['exact_committed_receipt_located'] and n['not_current4096_collision_measurement']
    assert not receipt['physical_admission'] and not receipt['RTL_PnR']
def test_single_candidate_and_actionable_binding_not_sweep(receipt):
    t=receipt['coordinated_binding_task']
    assert t['candidate_stage_groups']==58 and t['fixed_TP']==4 and t['fixed_depth']==4096
    assert not t['selected_or_proven_minimum']
    assert t['ideal_area_only_lower_bound_stage_groups']==48
    assert t['candidate_total_q_pairs']>=t['reference_total_q_pairs']
    assert 'return_region' in t['exact_owner_atom_fields']
    assert not t['direct_frame_allowance_equivalence_proven']
    assert not t['hardware_admission']
def test_payload_path_is_rejected_before_read():
    with pytest.raises(ValueError,match='Payload forbidden'):
        R.source('model-00001-of-00048.safetensors')


def test_corrected_corridor_forces_same_candidate_capacity_FAIL(receipt):
    n=receipt['current_service_capacity_negative']
    assert n['canonical_candidate_id']=='DS4096-TP4-S58-PAIR1'
    assert n['verdict']=='FAIL_S58_CORRECTED_SERVICE_CAPACITY_SCREEN'
    assert math.isclose(n['corrected_deficit_mm2'],2.4233123538459234)
    assert not n['new_partition_count_selected'] and not n['physical_GO']
    assert n['old_passing_screen_preserved']
    need=sum(n[k] for k in ['native_frame_only_S58_mm2','analytical_field_reservation_beyond_frame_mm2','return_no_credit_mm2','RNE_separate_construction_mm2','WAKE_separate_construction_mm2'])
    assert math.isclose(need,n['unchanged_S58_gross_field_need_mm2'])
    assert not n['frame_plus_repairs_embedded_or_disjoint_reconciliation_proven']
