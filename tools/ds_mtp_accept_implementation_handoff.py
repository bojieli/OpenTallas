"""Source realization/portbook handoff; no RTL generation or build admission."""
import argparse,hashlib,json,math
from pathlib import Path
import ds_mtp_accept_leaf_model as L
import ds_mtp_tokx_enrollment_model as T
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/ds_mtp_accept_implementation_handoff_20261003'

def scalar_records(k=512,iw=21):
 kw=math.ceil(math.log2(k+1));pw=32+iw+2
 groups=[('r0',2+32+iw+kw,1),('x0',pw,1),('xw',k,1),('thr',k,1),
 ('g_cell.s',pw,k),('g_cell.g_pass.x',pw,k-1),('g_bank.bv_bi_bn',iw+2,k),
 ('controller_and_output',kw+iw+10,1)]
 return [dict(group=n,raw_bits_each=b,instances=r,words_each=math.ceil(b/64),
              padding_high_zero_bits_each=math.ceil(b/64)*64-b,
              simultaneous_update='all words belonging to one logical register update atomically on same accepted source edge') for n,b,r in groups]

def model():
 pins=json.loads((OUT/'input_manifest.json').read_text())
 for p in pins:assert hashlib.sha256((OUT/p['archive']).read_bytes()).hexdigest()==p['sha256']
 arch=json.loads((OUT/'inputs/Archimedes_handoff.json').read_text());t=T.model();leaf=L.model()
 assert arch['clock_reset']['sinks']==2016 and arch['request']['height_um']==191.7
 assert not arch['admission']['slot_reserved']
 records=scalar_records();raw=sum(r['raw_bits_each']*r['instances'] for r in records)
 words=sum(r['words_each']*r['instances'] for r in records)
 assert raw==T.scalar_bits(512,21)[1]
 return dict(schema='DS_MTP_DEFAULT_OFF_IMPLEMENTATION_HANDOFF_R1',prerequisites=['468c2b913bc96f82dcf334a17b148dc993ec1bc9','a9691644adb23e9b8ffa37ffca80c219db325f8e','686c552854d62db3ce051483e8a73ee8180484bf'],
 source_pins=pins,source_kernel_selected={'NSLOT':8,'NW':21,'scalar_K':512,'scalar_VW':32,'scalar_ORDER':1,'default_enable':False,'new_replica':False,'class':'A greedy only'},
 planned_source_units=[{'name':'ot_hdc_mtp_accept_guarded','role':'exact24leaf codedword/FSM recipe from468c','original':'rtl/hdc/ot_hdc_accept.sv','new_file_only':True},
 {'name':'ot_hdc_mtp_source_holders','role':'two origin29/two value22 K64/N72 records; no hidden lease or slot','original':'a969 ProducerHolders reference','new_file_only':True},
 {'name':'ot_hdc_select_fullwidth_guarded','role':'scalar K512 index21, same insertion+odd/even sort; complete protected source inventory and checked stages required','original':'rtl/hdc/v41/ot_hdc_select.sv','new_file_only':True},
 {'name':'opt_in_caller_successor','role':'separate copied core/XU wrapper, default0 prior branch; hold CTL and stamp accepted producer launch, no original edits','original':'rtl/w17_runtime/hdc/v41x/ot_hdc_core_v41x.sv','new_file_only':True}],
 leaf_record_layout=leaf['state_layout'],caller_record_layout={'tokx_value':{'token':21,'fresh':1},'tokx_origin':{'position':21,'generation':4,'destination_slot':3,'occupied':1},'amax_value':{'token':21,'fresh':1},'amax_origin':{'position':21,'generation':4,'destination_slot':3,'occupied':1}},
 scalar_protection_inventory={'source_K':512,'new_IW':21,'source_raw_register_bits':raw,'source_register_groups':records,
 'independent_K64_N72_words':words,'coded_register_bits':words*72,'extra_over_fullwidth_raw_bits':words*72-raw,
 'physical_implementation_selected':False,'inventory_not_area_or_stage_admission':True,
 'codec_encoder_decoder_parallel_instances_if_this_direct_mapping_is_used':words,
 'source_initial_reset':'coherent legal encoded zero records; reset only truthful external allcopies fence; no reset erasing accepted segment',
 'joint_quarantine':'uncorrectable or bad padding on any used record suppresses ALL normal source grants/bank updates/writeback on discovery edge; feeds protected leaf stickyfault before normal consume',
 'atomic_words':'r0 65bits split into2 codewords is one simultaneous update; xw/thr eight words each update by source wave/threshold; no partial capture valid',
 'needed_before_scalar_RTL':['fullcodec+feedback/hold/update+fanin/fanout/clock/reset/slot/cuts area beyond width-only debit','checked insertion/sort/protectedwriteback latency and inputready bound','correction/fault ownership and coherent multiword source capture','actual source clock/CDC/reset context'],
 'no_free_intermediate_regs_or_K64_timing_transfer':True},
 endpoint_ABI={'lease_fields':{'position':21,'generation':4},'kernel_context':'one private actual die.u_tile.u_core namespace; fleet count unproven',
 'start':leaf['ports']['start'],'TOKX_leaf':leaf['ports']['tokx'],'AMAX_leaf':leaf['ports']['amax'],
 'ACCEPT_leaf':leaf['ports']['accept'],'RESULT_leaf':leaf['ports']['result'],'positive_fence':leaf['ports']['fence'],
 'producer_per_kind':{'token':21,'original_lease':25,'destination_slot':3,'valid':1,'ready':1,'begin_finish':1,'signals':52},
 'direction_encoding':{'begin_finish_0':'accepted producer command origin; token ignored but zero required','begin_finish_1':'producer terminal; full21 token and original echo required'},
 'actual_selected_routing':{'TOKX':'Builder.draft_body static FP32 LG SELECT ->scalar input NW21 ->u_sel ->XU full so_idx ->sourceholder fresh ->CTL TOKX leaf','AMAX':'accepted main ME verify command->exact lane full21 am_idx_v ->original stamped sourceholder ->CTL AMAX leaf','ACCEPT':'held CTL3d4 original25 lease/g3 until leaf acceptance','restore':'S_ACC guarded result drives stable acc_a; S_RST samples xu_rst_v before local result ACK'},
 'one_holder_each':True,'held_CTL_PC_advance':'once only on matching leaf handshake; decoded slot/g/lease held immutable while stalled',
 'source_slot_construction':'TOKX draft row+1 at accepted source launch; AMAX actual verified slot/lane at accepted command; no use of current c_slot_r to relabel returned work',
 'actual_multi_lane_ME_echo_adapter':'uninstalled, exact lane/slot outstanding receipt required; no eight-lane free source holder multiplication'},
 clock_and_latency=t['clock'],
 physical_contract={'Archimedes_request':arch['request'],'Archimedes_clock_reset':arch['clock_reset'],'Archimedes_replica_census':arch['replicas'],'Archimedes_channels':arch['channels'],
 'Maxwell_required_reply':{'actual_core_home_and_shard':None,'kernel_disjoint_rectangle':None,'scalar_matched_debit_and_containment':None,'actual_replica_count':None},
 'Archimedes_required_reply':{'loaded_clock_reset_paths':None,'legal636_52_52_channel_reservations':None,'SS_FF_cuts':None,'actualproducer_clock_CDC':None},
 'request_not_reservation':True,'no_uniform_corridor_or_existing_relay_borrow':True},
 gates={'kernel_component_model':'468c+a969 source/ports finite; independent of whole drafter','scalar_component_model':'NOT_COMPLETE_PROTECTED_COST_AND_CHECKED_STAGE_PLAN','contextual_build':'NOT_ADMITTED_NO_RESERVED_SLOT_CHANNEL_OR_LOADED_CLOCK','RTL_written_by_this_receipt':False,'job_launches':0,'whole_MTP':False,'rate':None,'conditional_tau_is_adoption':False,'HBM_service_ACK_terms_unchanged':True},
 minimum_next_dependency={'kernel':'Arch/Maxwell selected home/slot/clock/cuts, then assigned defaultoff functional source owner with exact fullwidth cases','scalar':'price this fullsource inventory/protection stages once before code, unchangedK512; width screen alone cannot qualify it','native':'Dewey/Popper actual producer echoes/positivefences, independently owned','acceptance':'Claude d2aff19 review separate; conditionaltau not adoption'},
 preserved_model_costs={'leaf_plus_caller':t['kernel_composition'],'scalar_width_only':t['scalar_repair'],'no_blind_add_scalar_fullcoded_inventory_to_previous_width_FF':True})

def main():
 p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');p.add_argument('--out',type=Path);a=p.parse_args()
 b=(json.dumps(model(),indent=2,sort_keys=True)+'\n').encode();dest=a.out or OUT/'model.json'
 if a.verify:assert dest.read_bytes()==b;print('PASS byteexact implementation portbook/source inventory; source physical admission pending')
 else:dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b);print(dest)
if __name__=='__main__':main()
