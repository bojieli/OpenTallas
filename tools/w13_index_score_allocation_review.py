"""Source-bound review of selected score trace; rejects unsupported fit transfer."""
import gzip,hashlib,json,subprocess
from pathlib import Path
from w13_index_lane_allocation import allocate
PATH='results/rtl/deepseek_hbm_complete_20261001/index-blas-production-candidate-r1.json.gz'

def build():
 b=subprocess.check_output(['git','show','efdfcb483:'+PATH]);d=json.loads(gzip.decompress(b))
 for path,sha in d['source_sha256'].items():
  if hashlib.sha256(subprocess.check_output(['git','show',d['source_commit']+':'+path])).hexdigest()!=sha:raise ValueError('source pin mismatch')
 events=d['selected_first_key_block_executed_virtual_SSA'];a=allocate(events);spans=a['symbol_lifetimes_instruction_ordinals']
 peak,index=max((sum(start<=i<=end for start,end in spans.values()),i) for i in range(len(events)))
 reserve=d['RF_address_loop_regs'];counts=d['executed_whole64_metrics']
 return {'schema':'w13.index-selected-score-allocation-review.v1','source_manifest_pin':{'git':'efdfcb483','path':PATH,'sha256':hashlib.sha256(b).hexdigest()},
  'verified_source_sha256':d['source_sha256'],'fixture_kind':d['fixture_kind'],
  'actual_source_produced_key_rows':len(d['produced_key_bits']),'distinct_raw_key_rows':len({tuple(r) for r in d['raw_key_bits']}),'distinct_produced_key_rows':len({tuple(r) for r in d['produced_key_bits']}),
  'selected_trace_events':len(events),'whole64_SSA_expanded':d['whole64_SSA_expanded'],
  'conservative_symbol_interval_peak':peak,'peak_event_index':index,'peak_live_symbols':[k for k,(s,e) in spans.items() if s<=index<=e],
  'address_loop_reserved_registers':reserve,'combined_strategy_register_demand':peak+reserve,'registers_per_thread':32,
  'allocation_strategy_verdict':'FAIL_CONSERVATIVE_SYMBOL_INTERVAL_RF_CAPACITY',
  'failure_scope':'selected trace conservative symbolic allocation, not proof all SSA allocation or ordinary GPU arithmetic impossible',
  'allocation_issues':a['issues'],'physical_register_assignments_admitted':False,
  'executed_whole64_software_metrics':counts,'RF_read_bits_scope':'operand count includes immediates; not physical register-port traffic',
  'shared_allocation_warning':d['shared_note'],'old_joint_63488_fit_reusable':False,
  'new_sanitize_exception_buffers_actual_addresses':None,'old_65536copy_traffic_additive_proof':None,
  'coverage':d['coverage'],'production_dispatcher_bound':d['production_dispatcher_bound'],
  'whole64_actual_branches_and_allocation':None,'physical_provider_timeline':None,'phase_leases':None,
  'checkpoint_reads':d['checkpoint_reads'],'hardware_launch':False,'physical_admission':False,'rate_credit':0}

if __name__=='__main__':
 import sys
 Path(sys.argv[1]).write_text(json.dumps(build(),indent=2)+'\n')
