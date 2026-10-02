#!/usr/bin/env python3
"""Join existing native noECC requests to retained macro proposals and source fences."""
import argparse,gzip,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'results/uarch/dsrom_noECC_source_geometry_join_20261002';I=BASE/'inputs'
def read(n):return json.loads((I/n).read_text())
def pin_box(row,pin):
 if row['orientation']!='R0':raise ValueError('unpriced orientation')
 x,y=row['origin_DBU'];a,b,c,d=pin['bbox_DBU'];return [x+a,y+b,x+c,y+d]
def root(shard,local_pair,mb):
 if shard not in (0,1) or not 0<=local_pair<2048 or mb not in (0,1):raise ValueError('source local pair/MB')
 return 64*shard+(2*local_pair+mb)//64

def build():
 n=read('native.json');p=read('physical.json');b=read('budget.json');t=read('templates.json')['ROM']
 field=(I/'field.sv').read_text();spine=(I/'spine.sv').read_text();core=(I/'core.sv').read_text()
 for literal,s in [('localparam integer LS = L - LR;',field),('rows_left <= rows_left - 19\'($countones(r_v));',spine),('rows_left == 19\'d0 && !sm_run && !ld_run',spine),('S_COLL_WAIT: if (!coll_busy)',core)]:
  if literal not in s:raise ValueError('source fence changed '+literal)
 placement=json.loads(gzip.decompress((I/'placement.json.gz').read_bytes()));macros={(x['source_pair'],x['slot'],x['PP']):x for x in placement if x['template']=='ROM'}
 pins={x['pin']:x for x in t['pins']};summaries=[];endpoints={};request_count=0;MBcount=0
 for case in n['source_cases']:
  alias=case['alias'].replace('.','_');rs=[json.loads(x) for x in gzip.decompress((I/(alias+'.jsonl.gz')).read_bytes()).splitlines()]
  phases=set();pairs=set();regions=set()
  for r in rs:
   stage,rank,shard,phase,key,era,lease=r['owner_context'];pair=r['main_word_address']['local_pair'];pp=r['main_word_address']['PP'];row=r['main_word_address']['row']
   if r['source_CE_accept_edge']+2!=r['source_bank_capture_edge'] or r['source_CE_accept_edge']+3!=r['source_lane_consumer_edge']:raise ValueError('native source deadline changed')
   if r['source_acceptance_scope']!='CONDITIONAL_READY_PAIR_INPUT_SOURCE_MODEL_NOT_UPSTREAM_RTL_TRACE':raise ValueError('unknown acceptance evidence')
   phases.add((stage,rank,shard,phase,key));pairs.add(pair);request_count+=1
   for mb in r['main_word_address']['MBs']:
    m=macros[pair,mb,pp];rid=root(shard,pair,mb);regions.add(rid);MBcount+=1
    name=f'shard{shard}.localpair{pair}.MB{mb}.PP{pp}'
    endpoints[name]=dict(source_global_pair=r['source_global_pair'],local_pair=pair,shard=shard,MB=mb,PP=pp,root_id=rid,
      macro_bbox_DBU=m['bbox_DBU'],retained_template_origin_DBU=m['origin_DBU'],
      placement_scope='RETained shard0 proposal template reused in shard-local coordinates; source hierarchy not elaborated; BF_DUAL frame and actual shard placement must be rebound',
      source_hierarchy_elaborated=m['hierarchy_elaborated'],
      pins={k:dict(layer=pins[k]['layer'],bbox_DBU=pin_box(m,pins[k])) for k in ('clk','ce_in','addr_in[0]','rd_out[0]','rd_out[273]')},
      capture_D_endpoint_coordinates_available=False)
  summaries.append(dict(alias=case['alias'],phase_identities=[list(x) for x in sorted(phases)],paired_read_count=len(rs),main_MB_read_count=2*len(rs),unique_pairs=len(pairs),root_ids=sorted(regions),first_CE=case['first_CE'],last_CE=case['last_CE'],last_native_consumer=case['last_lane_consumer'],global_seats_added=0,extra_local_ACK_wire=False,absolute_origin_bound=False))
 # Native tags/captures replace the former ECC-global-seat proposal; zero new
 # slots are inferred from boundary obligation counts. Underlying frame stays.
 area=n['prospective_area_removal'];slot=b['full_topk_slot'];base=area['screen_without_parity_logic_before_coordinated_clearance_removal_mm2'];missing=slot['additional_state_only_debit_once_mm2']
 return dict(schema='opentallas.dsrom.noECC.source-geometry-composition.v1',candidate=b['candidate'],origin_receipts=read('origins.json'),
  input_sha256={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(I.iterdir()) if f.is_file()},generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
  native_phases=summaries,paired_read_count=request_count,MB_read_count=MBcount,translated_macro_endpoint_count=len(endpoints),translated_macro_endpoints=endpoints,
  acceptance='Nash conditional native ready-feed source model; not accepted upstream RTL events. Absolute cfg/VM/activation origins still required.',
  source_capacity={'no_new_128_320_512_global_pool':True,'no_new_local_ACK_wire':True,'existing_perpair_capture_bits':1096,'existing_i1_i2x_i3_tags_retained':True,'native_local_retirement':'bank-selected i2_v/lane sample at accept+3','shared_writer_and_collective_ownership_not_retired_by_local_sample':True},
  root={'roots_per_shard':64,'local_ordered_tree_levels':6,'root_id_formula':'64*shard+floor((2*local_pair+MB)/64)','unmodified_rowtags':True,'source_return_port_bits':69,'aggregate_interface_bits_64roots':4416,'interface_bits_are_not_link_BW':True,'ready_accept_and_write_visible_stamps_required':True,'root_latency_cycles_unmeasured':None},
  cfg_and_completion={'generic_CFG_capture_last_edge':26,'generic_safe_GO_edge':27,'hard_cfg_provider_acceptance_not_calibrated':True,'source_GO_or_timer_not_payload_delivery_proof':True,
    'absolute_origin_provider_fields':['phase/stage/rank/shard/key/era/source-clock identity','all cfg words accepted and final payload/act visibility','VM request accepted and activation-word return visible','actual s_ok/s_adv and source mainCE event receipts','actual root outputs/address/version and destination writes visible','writer drain and coll_busy release'],
    'source_rows_left_counts_r_v_not_external_ACK':True,'native_spine_idle_predicate':'rows_left==0 && !sm_run && !ld_run','dependent_collective_PC_requires':'coll_busy deasserted after final destination write','cfg_or_root_missing_cost_not_zero':True},
  physical={'complete_pair_macros':4,'capture_and_macro_clock_loads':p['complete_NB2_PP1_pair']['existing_capture_and4macro_clock_pins'],'layer_exclusions':p['local_macro_layer_exclusions'],
    'full_translated_element_map_closed':False,'macro_translation_not_whole_compute_control_pinmap':True,'actual_capture_control_clock_PG_vias_halo_and_route_tracks_owner':'Archimedes','no_ECC_jobs':True},
  area={'prior_conservative_main_proxy_screen_mm2':b['full_topk_slot']['same_candidate_screen_with_topk_state_only_mm2'],
    'source_native_no_extra_global_request_or_mux_reservation_branch_mm2':base+missing,'difference_is_old_proposal_reservation_not_instantiated_credit_mm2':b['full_topk_slot']['same_candidate_screen_with_topk_state_only_mm2']-base-missing,
    'noECC_macro_instances_area_credit_mm2':0,'source_clock_and_capture_area_savings_mm2':0,'actual_geometry_fit_proven':False,
    'complete_selector_state_added_once_mm2':missing,'selector_filter_full_logic_SSFF_and_slot_displacement_unpriced':True,'numeric_common_proxy_branch_not_auto_adopted':True},
  owner_tasks={'Nash':'actual cfg/VM/activation accepted origins and waveform bind; retain native no-global-seat pipeline flow','Epicurus':'ONE complete balanced filter quota/prefix/compaction plus histogram/suffix/choice model and source service calendar','Archimedes':'complete element pins/control/capture/clock/PG translated map and complete selector replacement/controller/corridor disjointunion','Maxwell':'compose actual root/cfg/write-visibility service stamps and shared-resource calendars, no zero unmeasured terms'},
  semantic_ROM_checks_retained=True,SRAM_HBM_link_protection_retained=True,build_admitted=False,physical_fit=False,fulltoken_rate_adopted=False,new_jobs=0)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--output',type=Path,required=True);x=a.parse_args()
 if x.output.exists():raise ValueError('fresh record required')
 x.output.write_text(json.dumps(build(),sort_keys=True,indent=2)+'\n')
