"""One candidate ledger; no source-calibrated rate or hardware credit."""
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from qwen_rom_pc_local_service_proposal import proposal

def test_shared_reverse_grants_are_not_free_payload_bandwidth():
 r=proposal();a=r['conditional_ceiling_floors_s']
 assert r['candidate']['shared_output_slots_per_sector']==2
 assert a['shared_data_plus_credit_output']==pytest.approx(2*a['column_commands'])
 assert a['perfect_overlap_minimum']==pytest.approx(.002356992)
 assert a['qualified_overlap']==0
 assert a['final_latency'] is a['adopted_rate'] is None

def test_two_windows_keep_backing_bytes_and_existing_macro_count():
 r=proposal();c=r['candidate']
 assert c['tile_rows_required']==2*c['layer_window_rows']==108
 assert c['rows_spare']==20 and c['existing_depth']==128
 assert c['additional_tile_KV_macros']==c['additional_context_SRAmacros']==0
 assert r['traffic']['read_rank_B']==150690816
 assert r['traffic']['incremental_second_full_read_B']==0
 assert c['fill_lanes']==1 and c['fill_tracks_before_clock_reset']==1048

def test_complete_positive_floor_accounts_for_credit_masks_and_clock_sinks():
 r=proposal();a=r['source_area_floor']
 assert a['additional_clock_and_reset_sinks_per_stack']==sum(a[k] for k in ('extra_local_FF_bits_per_stack','extra_output_pipeline_bits_per_stack','new_credit_mask_bits_per_stack'))
 assert a['new_credit_mask_bits_per_stack']==32*128*32
 expected=a['additional_clock_and_reset_sinks_per_stack']*a['FF_area_um2']+a['mux_NAND2_count_per_stack']*a['NAND2_area_um2']+a['mux_INV_count_per_stack']*a['INV_area_um2']
 assert a['known_increment_um2_per_stack']==pytest.approx(expected)
 assert a['complete_fit'] is False and a['complete_area'] is None
 assert r['hardware_admitted'] is r['new_RTL'] is r['new_map'] is False

def test_baseline_throughput_bound_is_not_subtracted_from_compute_cycles():
 r=proposal();d=r['debit_join']
 assert d['old_KV_bound_subtracted_from_compute']==0
 assert d['baseline_uarch_changed'] is False
 assert d['named_747_65_baseline_components'] is None
 assert d['inherited66_4063488_service_reservation_is_credit'] is False

def test_archived_proposal_cold_replay_preserves_failed_parser_record():
 import json
 archive=Path(__file__).resolve().parents[1]/'results/uarch/qwen_rom_global_ready_service_g0_20261002'
 assert proposal()==json.loads((archive/'pc_local_service_proposal_r3.json').read_text())
 assert (archive/'historical_proposal_r1.json').read_bytes()==b''
 assert json.loads((archive/'historical_parser_failure.json').read_text())['hardware_failure'] is False
