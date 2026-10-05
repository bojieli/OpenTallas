"""Source-counted ordinary index service floors; conditional capacity, not clocks."""
import ast,gzip,hashlib,json,math,subprocess
from pathlib import Path
PATH='results/rtl/deepseek_hbm_complete_20261001/index-blas-production-candidate-r1.json.gz'

def build():
 b=subprocess.check_output(['git','show','efdfcb483:'+PATH]);d=json.loads(gzip.decompress(b))
 src=subprocess.check_output(['git','show','922a6b673:tools/deepseek_hbm_complete_index_blas.py'])
 assert hashlib.sha256(src).hexdigest()==d['source_sha256']['tools/deepseek_hbm_complete_index_blas.py']
 model_path='tools/deepseek_hbm_complete_index_blas_model.py'
 model_raw=subprocess.check_output(['git','show','e416630f0:'+model_path])
 tree=ast.parse(model_raw);fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='build')
 bridge_node=next(n.value for n in fn.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='scale_bridge' for t in n.targets))
 bridge=eval(compile(ast.Expression(bridge_node),'pinned_scale_handoff','eval'),{'__builtins__':{}})
 phases={
  'query_sanitize_decode_once_per_call':{'bytes':81920,'warp_shared_issues':640,'scope':'32queries x128terms; conditional caching across keytiles requires capacity/lease proof'},
  'key_sanitize_decode':{'bytes':163840,'warp_shared_issues':1280},
  'finite_integer_block_always':{'bytes':1081344,'warp_shared_issues':16384},
  'exceptional_selection_merge_always':{'bytes':2195456,'warp_shared_issues':17152,'scope':'q/k loads and classify executed every term; not exceptional-only shortcut'},
  'connected_finish_always':{'bytes':270336,'warp_shared_issues':2112}}
 shared=sum(p['bytes'] for p in phases.values());issues=sum(p['warp_shared_issues'] for p in phases.values())
 assert shared==d['executed_whole64_metrics']['shared_requested_bytes'] and issues==d['executed_whole64_metrics']['shared_warp_issues']
 # These source operations have two register operands and all32head lanes,
 # unlike the aggregate counter that includes immediates/masked branches.
 full_two_reg_warps={'finite_IMUL':8192,'finite_loop_IADD':8192,'decode_FMUL':384,'weight_FMUL':64,'ordered_block_csum_FADD':512}
 rr=sum(full_two_reg_warps.values())*2048+2048*1024 # STORE operands
 rw=sum(full_two_reg_warps.values())*1024+35520*1024 # full-lane LOAD result writes
 capacity=[]
 for sm in [1,32]:
  slow=math.ceil(shared/(128*sm));readfloor=math.ceil(rr/(8192*sm));writefloor=math.ceil(rw/(4096*sm))
  capacity.append({'SMs':sm,'shared_combined_bytes_per_serial_cycle':128*sm,'RF_register_read_bits_per_serial_cycle':8192*sm,
   'RF_logical_write_bits_per_serial_cycle':4096*sm,'shared_serial_cycle_floor':slow,
   'RF_active_read_serial_cycle_floor':readfloor,'RF_active_write_serial_cycle_floor':writefloor,
   'max_service_serial_cycle_floor':max(slow,readfloor,writefloor),
   'nominal_target_service_floor_us':max(slow,readfloor,writefloor)/900,
   'scope':'one64key fixture;32SM row ideal global capacity over one die, assumes distribution but no assignment proof',
   'actual_port_event_schedule':None})
 extra=bridge['shared_bytes'];expanded=shared+extra
 return {'schema':'w13.index-source-service-floor.v2','source_phase_model_pin':{'git':'e416630f0','path':model_path,'sha256':hashlib.sha256(model_raw).hexdigest()},
  'source_scale_handoff_bridge':bridge,'expanded_shared_bytes_with_scale_handoff':expanded,
  'expanded_shared_warp_issues_with_scale_handoff':issues+bridge['warp_issues'],
  'expanded_shared_serial_cycle_floors':{'one_SM':math.ceil(expanded/128),'ideal32SM':math.ceil(expanded/4096)},
  'source_initializer_still_unbound':{'accumulator_bytes_if_shared':8192,'warp_STORE_issues':64,'literal_fusion_actual_ops':None},
  'pitch33_fullquerycache_plus_rawkeys_bytes':67072,
  '32SM_partition_replication_is_not_free':{'query_refill_extra_shared_bytes':1047552,'padding_zero_init_extra_bytes':122880,'qdecode_replication':32,'keydecode_inflation':16,'additional_actual_ports_lease_timeline':None},'source_manifest_pin':{'git':'efdfcb483','path':PATH,'sha256':hashlib.sha256(b).hexdigest()},
  'source_lowerer_pin':{'git':'922a6b673','path':'tools/deepseek_hbm_complete_index_blas.py','sha256':hashlib.sha256(src).hexdigest()},
  'phases':phases,'combined_shared_bytes':shared,'warp_shared_issues':issues,
  'exceptional_only_branch_work':{'divergent_branch_counter':d['executed_whole64_metrics']['divergent_warp_branches'],'exact_active_lane_RF_extra_bits':None,'branch_latency':None,'cost_not_zero':True},
  'RF_known_full_lane_two_register_warp_counts':full_two_reg_warps,'RF_known_active_read_bits_lower_bound':rr,
  'RF_known_active_write_bits_lower_bound':rw,'RF_read_including_immediates_NOT_lower_bound':783331328,
  'RF_write_fullwarp_counter_NOT_active_lane_lower_bound':375089152,'RF_unknown_remainder_active_counts':None,
  'capacity_floor_cases':capacity,'ordinary_opcode_issue_reconvergence_latency_floor':None,
  'query_full_cache_scope':{'raw_query_bytes':16384,'decoded_units_bytes':16384,'query_exponents_bytes':512,
    'query_cache_bytes':33280,'plus64raw_keys_bytes':66048,'shared_capacity_bytes':65536,
    'strategy_verdict':'FAIL_FULL_QUERY_CACHE_PLUS_FULL_RAW_KEY_TILE_BEFORE_OTHER_BUFFERS',
    'cachequeryonce_not_admitted':True,'block_streaming_lifetimes_and_banks':None},
  'no_incompatible_fit_transfer':True,'full_program_rank_to_die_SM_mapping':None,'all_domain_exact_gate':False,
  'actual_provider_ACK_CDC_and_leases':None,'SS_FF':None,'whole_token_latency':None,'rate_credit':0,'hardware_launch':False}

if __name__=='__main__':
 import sys
 Path(sys.argv[1]).write_text(json.dumps(build(),indent=2)+'\n')
