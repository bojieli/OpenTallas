#!/usr/bin/env python3
"""Bind measured index geometry to the existing fixed r7 context, before P&R.

This checks one selected target, not a geometry/architecture sweep. It does not
move Claude's floorplan or change original index or collective RTL.
"""
import argparse, ast, hashlib, json, math, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def price(floorplan,source):
    floor=json.loads(floorplan.read_text());src=source.read_text()
    if floor['tool_sha256']!=sha(source):raise ValueError('floorplan/source hashes differ; cannot mix contexts')
    # Literal shared call applies to BOTH kv and ik; refuse an unknown successor.
    if not re.search(r"chain\(f'\{name\}_\{st\}', 'kv_rows', (\d+),",src):raise ValueError('selected ik width source not recognized')
    width=int(re.search(r"chain\(f'\{name\}_\{st\}', 'kv_rows', (\d+),",src)[1])
    model_path=ROOT/'results/uarch/hbm_index_path_20261005/model.json'
    result_path=ROOT/'results/rtl/hbm_index_path_20261005/connected_29a9_r1/result.json'
    model=json.loads(model_path.read_text());result=json.loads(result_path.read_text())
    assert result['exit']==0 and result['source_geometry']['NS']==16 and result['source_geometry']['NK']==4
    assert result['actual_encoded_keys_and_exact_scores']==10928
    dff=model['area']['extra_pipeline_FF_um2']/model['area']['extra_pipeline_FF_allowance']
    area=model['area']['scorer_and_join_cell_estimate_um2']/1e6
    ledger=floor['block_ledger']['index']['mm2']
    quarter_keys=model['canonical_source']['quarter_max_keys']
    beat_keys=16;payload=beat_keys*544;meta=beat_keys*(20+3);total=payload+meta
    paths={n:x for n,x in floor['manhattan_paths'].items() if n.startswith('ik_')}
    assert len(paths)==4 and floor['manhattan_class_bounds']['ik']['paths']==4
    stages=sum(x['stages_430'] for x in paths.values())
    existing_pipe_ff=stages*width
    payload_pipe_ff=stages*payload
    total_pipe_ff=stages*total
    return {
      'schema':'opentallas.hbm_index_selected_context_price.v1',
      'decision':'NOFIT_PREBUILD_CURRENT_R7_BINDING',
      'reason':'Selected latency-cut index cell estimate alone exceeds the existing TOTAL index reservation. The source-selected 1024-bit/quarter key link also does not deliver the native 8704-bit/quarter payload per edge.',
      'scope':'One existing r7 context vs actual measured NS16NK4 rank0 path. Estimates are prebuild screening, not mapped area or routed signoff. No final gather design or block movement is adopted.',
      'selected_source':{'native_index_commit':'29a9e9710','measured_milestone':'9ead9838d','module':'ot_hbm_accel_index_path','ENABLE_default':0,'SOURCE_VM_ENABLE_default':0,'geometry':result['source_geometry'],'measured_keys':10928,'measured_component_edges':1801},
      'area_screen':{'r7_total_index_reservation_mm2':ledger,'r7_source_grade':floor['block_ledger']['index']['grade'],'r7_reservation_per_quarter_mm2':ledger/4,
        'current_scorer_and_join_CELL_estimate_mm2':area,'current_cell_per_quarter_mm2':area/4,'cell_deficit_against_entire_reservation_mm2':area-ledger,
        'cell_area_excludes':['selector/quantiser complete mapped bodies','protected selector macros/codec/receiver','loaded clock and boundary nets','any final ordered gather adapter'],
        'minimum_footprint_at_explicit_50pct_utilization_mm2':area/.5,'minimum_per_quarter_at_50pct_mm2':area/2,
        'footprint_deficit_at_50pct_mm2':area/.5-ledger,'model_cell_estimate_is_not_mapped_area':True,'slot_fit':False},
      'key_boundary':{'r7_existing_payload_wires_per_quarter':width,'native_payload_bits_per_quarter_beat':payload,'native_metadata_bits_per_quarter_beat':meta,
        'native_payload_plus_metadata_bits_per_quarter_beat':total,'metadata':'globalID20 + lv/ref/keep3 per key; last and held job32/gen4/pos20/rank7 additional, not free',
        'quarter_max_keys':quarter_keys,'quarter_max_beats':math.ceil(quarter_keys/beat_keys),
        'old_link_payload_only_lower_bound_edges':math.ceil(quarter_keys*544/width),
        'old_link_payload_metadata_lower_bound_edges':math.ceil(quarter_keys*(544+23)/width),
        'whole_beat_framed_edges_each':math.ceil(total/width),'whole_beat_framed_phase_edges':math.ceil(quarter_keys/beat_keys)*math.ceil(total/width),
        'payload_width_ratio':payload/width,'route_paths':paths,'planned_forward_stages_max':max(x['stages_430'] for x in paths.values()),
        'source_clock_domains':floor['clock_domains'],'CDC_accepted_hold_ready_capacity_source':None,
        'existing_forward_payload_FF':existing_pipe_ff,'native_full_payload_forward_FF_lower_bound':payload_pipe_ff,
        'native_payload_metadata_forward_FF_lower_bound':total_pipe_ff,
        'incremental_payload_metadata_FF':total_pipe_ff-existing_pipe_ff,
        'incremental_payload_metadata_CELL_mm2':(total_pipe_ff-existing_pipe_ff)*dff/1e6,
        'additional_costs_unbound':['clock/reset/mux','ready/accepted debt return','CDC depth/quiet rearm','real loaded route/port receiver'],
        'not_selected_alternatives':'Neither widening nor serialized assembly is adopted: existing design owner must bind ONE source-compatible interface and price its actual exposure.',
        'no_free_overlap':True},
      'candidate_memory_context':{'original_child_AW':10,'logical_original_words':1024,'actual_parent_ingress_bound_blocks_each_quarter':342,'line_capacity_bound':171,
        'rank0_numeric_bound_checked':True,'all_rank_numeric_qualified':False,
        'no_address_truncation':'256-word physical view needs explicit upper-address refusal or priced additive AW successor; do not silently drop address9:8',
        'protected_storage_and_loaded_receiver_installed':False,'existing_response_edges':1},
      'handoff':{'global_ordered_gather_writer':'Claude per latest Rawls b400b585d; Confucius owns final selector boundary slice','index_RTL_writer':'Sagan','combined_config_writer':'Rawls',
        'actual_local_topk':'Q4W16 accepted BF16/globalID20/lv,last streams; globally ordered within each quarter; held tuple through consumer drain. Measured current parent topk uses UNMASKED scores, not full-program candidate-mask feedback.',
        'full_program_dependency':'Canonical global candidate-block selection -> actual candidate-mask publication/feedback -> local masked topk -> final global select must remain causal; the measured simultaneous raw topk is component-only and cannot replace masked localtop in the full program.',
        'approved_collective_sources':['rtl/chip/ot_w15_coll_dma.sv','rtl/chip/ot_coll_topk_merge.sv'],
        'required_final_boundary':'Hardware canonical GLOBALID ordered gather before existing W15 FILTER, or explicitly approved successor. Rank-major TP96 buffers violate tie and ascending output contracts. Never host-sort DUT traffic.',
        'actual_W15_gather_bytes_per_rank':512*8,'actual_W15_gather_bytes_total':96*512*8,
        'prepaid_final_result_words':512//16,'final_output_backpressure':'Existing merger has NO out_ready: reserve all512IDs/32words before GO; actual downstream publication/reverse retains frame.',
        'required_next_design_choice':'Claude fixed-r7 frame/ik interface correction using this source tuple, and actual ordered gather source. Keep original index and collective files byte-identical until opt-in successor is priced.'},
      'period_ps':833,'SS_setup_uncertainty_ps':60,'FF_hold_uncertainty_ps':25,
      'source_pins':{str(floorplan):sha(floorplan),str(source):sha(source),str(model_path.relative_to(ROOT)):sha(model_path),str(result_path.relative_to(ROOT)):sha(result_path),
         **{n:sha(ROOT/n) for n in ['rtl/hbm_accel/index/ot_hbm_accel_index_path.sv','rtl/chip/ot_w15_coll_dma.sv','rtl/chip/ot_coll_topk_merge.sv']}},
      'P_and_R_launch_allowed':False,'SS_FF_closed':False,'adopted':False}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--floorplan',type=Path,required=True);p.add_argument('--floorplan-source',type=Path,required=True);a=p.parse_args()
 print(json.dumps(price(a.floorplan,a.floorplan_source),indent=2))
