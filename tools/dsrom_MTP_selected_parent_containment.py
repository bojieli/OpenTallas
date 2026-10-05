#!/usr/bin/env python3
"""Exact selected-parent refusal, not a second architecture or physical launcher."""
import argparse,gzip,hashlib,json,math,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/dsrom_MTP_selected_parent_containment_20261003'

def inputs():
 for row in json.loads((OUT/'inputs/origins.json').read_text()):
  if hashlib.sha256((OUT/'inputs'/row['copy']).read_bytes()).hexdigest()!=row['sha256']:raise ValueError('changed Arch receipt '+row['copy'])
 return json.loads((OUT/'inputs/arch_reply.json').read_text()),json.loads((OUT/'inputs/cell_prices.json').read_text())['facts']

def tree(sinks,leaf,upper=8):
 levels=[math.ceil(sinks/leaf)]
 while levels[-1]>1:levels.append(math.ceil(levels[-1]/upper))
 return levels

def generate():
 m,facts=inputs();slot=m['requested_slot'];c=m['local_clock_reset'];ch=m['signal_channels']
 if (slot['width_um'],slot['height_um'],m['kernel']['total_raw'],m['kernel']['protected_FF_sinks'])!=(128,191.7,716,2016):raise ValueError('not selected corrected caller')
 if c['total_clock_reset_buffers']!=578 or ch['leaf_signals']!=636 or ch['producer_signals_each']!=52 or ch['producer_cut_instances']!=2:raise ValueError('changed counted union')
 parent=json.loads((OUT/'inputs/prospective_field_parent.json').read_text())
 d={'tracks.txt':(OUT/'inputs/tracks.txt').read_text(),'tech.lef':gzip.decompress((OUT/'inputs/tech.lef.gz').read_bytes()).decode()}
 services=json.loads((OUT/'inputs/services.json').read_text());su=next(x for x in services if x['name']=='HUB_SU_VECTOR')
 track=re.search(r'make_tracks M4[^\n]*-y_offset ([\d.]+)[^\n]*-y_pitch ([\d.]+)',d['tracks.txt'])
 offset,pitch=map(float,track.groups())
 tech=re.search(r'LAYER M4\b(.*?)END M4',d['tech.lef'],re.S)
 if not tech or 'HORIZONTAL' not in tech[1]:raise ValueError('source directional channel')
 # The complete existing parent load screen fixes5.76fF, not the cell's
 #184.32fF library max. Keep that construction constraint; no relaxation.
 ceiling=5.76;resetpin=c['FF_RESETN_eight_sink_fF']/8
 leaf=math.floor(ceiling/resetpin)
 if leaf*resetpin>=ceiling:leaf-=1 # positive wire capacity mandatory
 levels=tree(2016,leaf);extra=sum(levels)-c['buffers_per_tree']
 area=facts['BUFx4_ASAP7_75t_R']['SS']['area_um2'];rc=json.loads((OUT/'inputs/RC_screen.json').read_text())
 gross=slot['rectangle_mm2'];scalar=m['scalar_source']['width_only_50pct_mm2']
 core_text=(OUT/'inputs/tile.sv').read_text();die_text=(OUT/'inputs/die.sv').read_text()
 core_text=re.sub(r'//[^\n]*|/\*.*?\*/','',core_text,flags=re.S)
 if len(re.findall(r'ot_hdc_core_v41x\s*#\(',core_text))!=1 or 'u_tile' not in die_text:raise ValueError('source wrapper identity')
 return {
 'schema':'DS_MTP_SELECTED_PARENT_CONTAINMENT_R1','candidate':parent['candidate'],
 'Arch_source_commit':'686c552854d62db3ce051483e8a73ee8180484bf','reviewed_main_MTP_origin':'7b4509c23a8a67891f250bef78d7459e6050883c','field_parent_snapshot_proposal_only':'06f7c9590e9a0a7737fdca782f2264fab5f1abba',
 'outcome':'REFUSE_CURRENT_COMPOSED_CONTAINMENT','architectural_impossibility':False,
 'named_instance':'die.u_tile.u_core / u_xu.u_sel','source_cores_per_wrapper':1,
 'selected_actual_stage_rank_shard_core_home':None,'fleet_replica_count':None,
 'no_N_TP_or_PAR2_implicit_core_multiplier':True,
 'requested_leaf_slot':{'width_um':128,'height_um':191.7,'rectangle_mm2':gross,'charged_body_um2':slot['body_um2'],'gross50pct_mm2':slot['gross50pct_mm2'],'geometric_spare_um2':slot['spare_geometric_um2'],'actual_bbox_DBU':None,'spare_is_not_available_tracks':True},
 'separate_scalar_width':{'K':512,'IW_before':16,'IW_after':21,'added_FF':7690,'gross50pct_mm2':scalar,'included_in_leaf_slot':False,'extra_compute_selector_replicas':0,'measured_zero_added_edges':False},
 'accounting':{'leaf_rectangle_plus_scalar_reservation_mm2':gross+scalar,'scalar_exceeds_entire_leaf_rectangle_mm2':scalar-gross,'combined_min_area_height_at128um':(gross+scalar)*1e6/128,'old_containment_credit':0,'extra_charge_for_existing578_buffers':0,'existing578_retained_once':True,'additional_repair_not_inside578':True,'fleet_total_mm2':None},
 'selected_parent_regions':{'serial_service_envelope':su,'prospective_field_reader_home_not_intaken_or_containment_credit':parent['new_home']['new_identical_home_per_shard_DBU'],'all_services':services,'not_free_region_proof':'HUB_SU_VECTOR has a coarse service reservation, not named current core/selector cell containment. No box within it is assigned or borrowed here.','rectangle_only_not_placed_fit':True},
 'channel_union':{'separate_cuts':[{'name':'serial_core_leaf','signals':636,'M4_wire_pitch_floor_um':636*pitch},{'name':'XU_origin_terminal_holder','signals':52,'M4_wire_pitch_floor_um':52*pitch},{'name':'ME_origin_terminal_holder','signals':52,'M4_wire_pitch_floor_um':52*pitch}],'shared_cut_if_explicitly_routed_signals':740,'shared_cut_floor_um':740*pitch,'M4_direction':'HORIZONTAL','M4_y_offset_um':offset,'M4_y_pitch_um':pitch,'named_escapes_PG_OBS_vias_clock_union':None,'actual_available_tracks':None,'free_track_credit':0,'52_signal_holders_not_automatic_FIFO':True},
 'clock_reset_load_union':{'serial_GHz':.9,'SS_setup_uncertainty_ps':60,'FF_hold_uncertainty_ps':25,'leaf_protected_FF':2016,'scalar_added_FF':7690,'existing_K512_baseline_retained':True,'leaf_CLK_SS_fF':c['SS_CLK_pin_fF'],'leaf_CLK_FF_fF':c['FF_CLK_pin_fF'],'scalar_added_CLK_SS_fF':c['scalar_added_CLK_SS_fF'],'scalar_added_CLK_FF_fF':c['scalar_added_CLK_FF_fF'],'leaf_plus_scalar_CLK_SS_fF':c['SS_CLK_pin_fF']+c['scalar_added_CLK_SS_fF'],'leaf_plus_scalar_CLK_FF_fF':c['FF_CLK_pin_fF']+c['scalar_added_CLK_FF_fF'],'bridge2936_FF_separate_not_in2016_or7690':m['prospective_CDC']['state_bits'],'bridge_spatial_clock_reset_not_contained':True,'578_local_CLK_RESET_buffers_already_charged':578,'parent_serial_clock_ingress_and_reset_release_routes':None,'reset_retirement':'Preserve holders/debt until positive provider/result/packet/visibility fence; synchronized domain release does not certify retirement.'},
 'reset_branch_refusal':{'selected_load_ceiling_fF':ceiling,'library_max_is_not_selected_slew_load_budget':True,'old_eight_pin_load_fF':8*resetpin,'old_eight_pin_excess_before_wire_fF':8*resetpin-ceiling,'largest_pin_only_positive_wire_fanout':leaf,'minimum_count_levels':levels,'additional_BUF_lower_bound':extra,'additional_body_um2_lower_bound':extra*area,'additional50pct_mm2_lower_bound':2*extra*area/1e6,'pin_only_repaired_wire_budget_fF':ceiling-leaf*resetpin,'wire_length_ceiling_um_screen':(ceiling-leaf*resetpin)/rc['C_fF_per_um'],'actual_branch_sites_and_samecount_routes_selected':False,'spare_after_minimum_gross_repair_um2_not_track_credit':slot['spare_geometric_um2']-2*extra*area},
 'latency':{'protected_accept_min_serial_edges':3,'added_min_serial_edges':2,'added_min_ns':2/.9,'source_K512_last_input_to_result_serial_edges':1026,'source_K512_tail_ns':1026/.9,'full_single_user_MTP_delta':None,'new_edge_or_slow_domain_not_adopted':True,'scalar_scan_input_output_bytes_per_edge':4,'nominal_leaf_II2_not_full_selector_throughput':True},
 'next_binding':{'Russell':'Emit exact selected stage/rank/shard core namespace(s), NSLOT8/NW21 caller and K512 IW21 instance map; no implicit per-PAR2 clone. Bind two origin holders and positive allcopies completion fences.','Maxwell':'Once that instance map exists, allocate leaf AND independent scalar delta against occupied named parent cells; use no old-frame or PG/corridor containment credit.','Archimedes':'Construct native CLK/reset/SETN and 636/52/52 pin escapes for those named instances. 8-reset-sink branch fails selected5.76fF ceiling; >=41 additionalBUF is a count lower bound, not a routed repair or permission to relax ceiling.'},
 'admission':{'source_bound_containment_outcome_ready':True,'slot_reserved':False,'physical_G0':False,'engine_RTL_GO':False,'new_jobs':0,'original_sources_changed':False,'global_live_solver_changed':False,'reason':'No actual selected core/home/replica map or disjoint scalar placement; reset8-sink load fails selected ceiling before wire; channel availability and full clock/PG union unbound.'}}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path);p.add_argument('--verify',action='store_true');a=p.parse_args()
 if a.verify:
  for name in ('source_pins.json','manifest.json'):
   for f,h in json.loads((OUT/name).read_text()).items():
    if hashlib.sha256((ROOT/f).read_bytes()).hexdigest()!=h:raise ValueError('changed '+f)
  if json.dumps(generate(),sort_keys=True,indent=2)+'\n'!=(OUT/'model.json').read_text():raise ValueError('containment regeneration differs')
  print('PASS exact containment refusal; NO BUILD ADMISSION')
 else:
  if a.out is None:p.error('--out required')
  a.out.write_text(json.dumps(generate(),sort_keys=True,indent=2)+'\n')
