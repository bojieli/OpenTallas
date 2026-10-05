#!/usr/bin/env python3
"""ROM-only user decision, same PAR2 candidate; no physical capacity deletion."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/dsrom_ROM_noECC_candidate_20261002'
def read(n):return json.loads((OUT/'inputs'/n).read_text())
def source_timeline(n):
 if type(n) is not int or n<0:raise ValueError('observed positive source edge required')
 return dict(accepted_main=n,source_capture_postNBA=n+2,original_arithmetic_preedge=n+3,
             earliest_ACK_if_followingedge=n+4,earliest_reuse_if_nextedge_afterACK=n+5,
             source_sampling_delay_added=0,ACK_edges_are_conditional_not_observed=True)
def build():
 p=read('physical.json');g=read('geometry.json');h=read('held.json');w=read('width.json');q=read('Qwen_control.json')
 source=(OUT/'inputs/element.sv').read_text()
 for clause in ('reg  [273:0] cap0, cap1;', 'i1_v <= issue; i2x_v <= i1_v;', 'i3_v <= i2x_v;', 'if (i2x_v && !i2x_bk) cap0 <= rd0;', 'if (i2x_v && i2x_bk) cap1 <= rd1;'):
  if clause not in source:raise ValueError('real source capture binding changed: '+clause)
 candidate='DS4096-TP4-S58-PAR2-NP2048'
 if p['candidate']!=candidate or g['candidate']!=candidate:raise ValueError('one shared candidate only')
 a=p['model_area'];coef=a['FF50_proxy_mm2_per_bit'];named=a['named_logic_allowance_mm2']
 identity=10+12+10+32+11+13+4+1
 rawbits=412*(274+12+identity+1);mainbits=128*(identity+544+16+2)
 if rawbits+mainbits!=a['state_bits']:raise ValueError('state disjoint union mismatch')
 # The old combined gather reserve includes actual main data selection.
 retained_data_mux_bits=128*544
 removed={k:named[k] for k in ('address_bank_arbitration','main_pair_SECDED272_check10','sidecar_leaf_SECDED256_check10')}
 removed['raw_parity_capture_identity_state']=rawbits*coef
 removed['ECC_gather_only']=named['gather_reply_mux']-retained_data_mux_bits*coef
 retained={'main_request_identity_capture_state':mainbits*coef,'main_data_selection_proxy':retained_data_mux_bits*coef,
           'old_area_rounding_policy':a['logic_reserve_rounding_mm2']}
 # Full274-bit held carriers remain a conservative proposed storage option;
 # source cap0/cap1 captures274, while arithmetic payload is272. No282-bit physical macro assumption.
 retained['conservative_carrier_padding_512FF_not_payload_change']=512*coef
 before=a['with_existing_clearances_screen_mm2'];after=before-sum(removed.values())+retained['conservative_carrier_padding_512FF_not_payload_change']
 if abs(after-(a['before_parity_added_logic_mm2']+sum(retained.values())))>1e-8:raise ValueError('area union mismatch')
 topk=read('topk.json');inventory=read('service_inventory.json')
 def find(x):
  if isinstance(x,dict):
   if x.get('name')=='X_SEL_TOPK_STORE':return x
   for v in x.values():
    y=find(v)
    if y:return y
  elif isinstance(x,list):
   for v in x:
    y=find(v)
    if y:return y
 existing=find(inventory)
 if existing is None or existing['gross_mm2']!=topk['slot_binding']['reservation']['area_mm2']:raise ValueError('topk debit containment identity')
 states={x['kind']:x for x in topk['slot_binding']['comparisons'] if x['runtime_n']==2048 and x['kind'] in ('DIG8_balanced_comb','DIG8_staged')}
 staged=states['DIG8_staged'];missing=staged['retained_state_required_core_mm2_at_source_50pct']-existing['gross_mm2']
 t=h['source_legal_local_CE_capacity_witness'];oldhold=t['minimum_slot_reuse_interval_under_retained_checker_and_explicit_ACK']
 conditional_noECC_hold=2+1+1+1;peak=t['independent_pairs']*min(t['consecutive_source_CE_edges'],conditional_noECC_hold)
 return dict(schema='opentallas.ROM.noECC.same-candidate.v1',candidate=candidate,ROM_ECC_required=False,
  authorization='User: remove ECC requirement for all Qwen and DS ROM, including configuration ROM; stop new ECC checker/corrector/sidecar implementation/P&R, preserve evidence/live jobs; retain ownership/handshake and SRAM/HBM/link protection.',
  configuration_scope='Configuration ROM ECC is optional/historical, not mandated. Preserve descriptor payload correctness, address bounds, identity/generation, semantic fault checks, delivery fences and control-state SRAM protection.',
  scope={'ROM_weight_ECC':False,'ROM_configuration_ECC':False,'ROM_configuration_ECC_status':'optional/historical','ROM_sidecar_mirror_ECC':False,'SRAM_protection':True,'HBM_protection':True,'link_protection':True,'transaction_identity_generation_nonce_and_fault_checks':True},
  origins=read('origins.json'),input_sha256={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted((OUT/'inputs').iterdir()) if f.is_file()},generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
  area={'reticle_mm':[26,33],'reticle_area_mm2':858,'old_ECC_local_screen_mm2':before,'removed_unique_ECC_terms_mm2':removed,
        'removed_unique_ECC_total_mm2':sum(removed.values()),'retained_common_main_terms_mm2':retained,'new_conservative_per_shard_screen_mm2':after,'unallocated_margin_before_real_unpriced_terms_mm2':858-after,
        'underlying_field_cfg_return_fixed_service_routes_clockPG_residual_retained_mm2':a['before_parity_added_logic_mm2'],
        'existing_checkers_additional_cell_mm2_not_in_old_screen_not_subtracted_twice':.05513502816,
        'main_and_raw_fullcorrector_floors_removed_once_in_named_terms':True,'no_measured_geometry_fit_claim':True,
        'removed_terms_are_source_priced_proposal_reservations_not_instantiated_area':True,
        'actual_instantiated_ROM_ECC_area_receipt_available':False,'actual_instantiated_ROM_ECC_area_credit_mm2':0,
        'configuration_ROM_ECC_instantiated_cost_not_bound_credit_mm2':0,
        'noECC_screen_is_model_reservation_branch_not_measured_physical_savings':True},
  physical={'compiled_NP_per_shard':2048,'NBF_per_shard':362,'R_per_shard':64,'stages':58,'TP':4,
            'field_macros_per_shard':8192,'cfg_macros_per_shard':14336,'ECC_mirror_role_pairs_removed_shard1':103,'ECC_source_sidecar_role_pairs_removed_shard0':103,
            'original_and_mirror_macros_removed':0,'ROM_macro_body_area_credit_mm2':0,'ROM_macro_halo_area_credit_mm2':0,
            'weight_pair_4096_depth_unchanged':True,'golden_payload_address_and_order_unchanged':True,
            'no_repack_or_new_weights_in_freed_ECC_roles':True,'cfg72bit_carrier_retained_48bit_payload_correctness_semantic_checks_required':True,'configuration_ECC_area_credit_mm2':0,
            'main_macro_carrier_bits':274,'paired_conservative_held_carrier_bits':548,'native_source_paired_capture_bits':548,'paired_main_arithmetic_payload_bits':544,
            'new_protected_checker_input_bits':0,'old_282_checker_width_not_a_physical_macro':True},
  normal_source_path={'relative_edges':source_timeline(0),'source_read_issue_predicate_unchanged':h['actual_source_admission']['predicate'],
                      'capture_to_arithmetic_has_no_ECC_terminal_dependency':True,'source_original_no_ECC_guard_retained':True,
                      'remove_weight_ECC_check_launch_gather_correction_fences_only':True,'retain_cfg_actual_delivery_fence_and_payload_generation':True,
                      'remove_checker_exposed_read_cost_edges_under_old_held_protocol':3,'no_fulltoken_rate_credit':True},
  conditional_held_lease={'feed_is_actual_fullphase_accept_trace':False,'pairs_per_edge':t['independent_pairs'],'consecutive_edges':t['consecutive_source_CE_edges'],
         'ECC_old_reuse_interval':oldhold,'noECC_conditional_reuse_interval':conditional_noECC_hold,'unchanged_128_lease_capacity':128,
         'conditional_peak_if_old_perread_lease_ACK_protocol_retained':peak,'conditional_extra_slots':max(0,peak-128),
         'conditional_extra_state_bits':max(0,peak-128)*(548+16+109+10+2),'conditional_extra_FF50_proxy_mm2':max(0,peak-128)*(548+16+109+10+2)*coef,
         'extra_slots_not_selected_or_added_to_screen':True,'actual_source_perbank_lease_release_must_determine_capacity':True,
         'not_authorized_to_remove_ACK_or_invent_ready_stalls':True},
  full_topk_slot={'source_commit':read('origins.json')['topk.json']['commit'],'shape':'N4/NMAX2048/P64/PF64/LDW4','already_inherited_store_mm2':existing['gross_mm2'],
      'state_models_before_logic':states,'conservative_one_slot_state_reserve_mm2':staged['retained_state_required_core_mm2_at_source_50pct'],
      'additional_state_only_debit_once_mm2':missing,'same_candidate_screen_with_topk_state_only_mm2':after+missing,
      'remaining_before_filter_logic_and_actual_context_mm2':858-after-missing,
      'original_selector_bbox_DBU':topk['slot_binding']['reservation']['bbox_DBU'],
      'state_only_required_height_um_at_same_width':staged['state_only_required_height_um_at_reserved_width_source_50pct'],
      'balanced_filter_quota_prefix_compaction_logic_state_stages_unpriced':True,
      'full_slot_G0':topk['G0'],'adjacent_common_controller_and_corridor_displacement_not_free':True,
      'staged_state_envelope_is_reservation_not_variant_adoption':True,'no_additional_replica_selection':True},
  Qwen={'ROM_ECC_requirement_removed':True,'ECC_debit_in_own_loaded_control_model':0,'own_control_area_credit':0,
        'loaded_control_failure_preserved':q['failure_commit'],'SSFF_failure_still_requires_bank_control_reset_arrival_repair':True,
        'sameedge_capture_observable_arithmetic_unchanged':True},
  coordination={'Nash':'same owner/phase/address map; omit all ROM ECC addresses/dependencies. Configuration ROM ECC is optional/historical; preserve descriptor payload correctness, bounds, identity, semantic faultchecks and delivery fence. Retain payload/scale/cfg/HE/CROM and original ordering; bind accepted maincapture/delivery/ownerACK, not offered phases.',
                'Archimedes':'same NP2048 geometry; remove ECC-only cones/router/roles, retain charged padding macro/OBS/halo and common main capture/control; source clock/macro CLKQ/setup/hold/corridors still mandatory.',
                'Epicurus':'price ONE full selector balanced filter quota/prefix/compaction alongside DIG8 service; original store debit already included, only missing state/logic added once.',
                'parent':'no mandatory ECC on configuration or weight ROM; compose payload-correct noECC cfg/input/root/normalmain dependency edges and actual accepted ownership; SRAM/HBM/link protection unchanged.'},
  admitted={'model_reprice':True,'RTL':False,'physical_job':False,'hardware_fit':False,'fulltoken_latency_measured':False,'no_single_token_loss_proven':False},
  historical_ECC_records_immutable=True,original_RTL_uarch_docs_untouched=True,new_fleet_jobs=0)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--output',type=Path,required=True);x=a.parse_args()
 if x.output.exists():raise ValueError('fresh record required')
 x.output.write_text(json.dumps(build(),sort_keys=True,indent=2)+'\n')
