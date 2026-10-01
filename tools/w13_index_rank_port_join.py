"""Authoritative index rank/tile work joins candidate SM ports, never token admission."""
import ast,hashlib,json,math,subprocess
from pathlib import Path
G='results/rtl/deepseek_hbm_complete_20261001/whole-program-calendar-r2.json'
C='tools/w19_gpu_simd_contract.py'


def work(n):
    # Source sanitize all N keys, decoder ceil(N/32) software padding, four
    # blocks, finite/selection/finish per-key, scale bridge q/k stores+loads.
    padded=(n+31)//32
    kernel_bytes=81920+n*56448+padded*49152
    scale_bytes=512+padded*512+n*528
    kernel_issues=640+n*565+padded*384
    scale_issues=4+padded*4+n*8
    return {'keys':n,'decoder_warp_groups':padded,'software_decoder_padding_rows':padded*32-n,
      'source_shaped_shared_bytes':kernel_bytes+scale_bytes,'source_shaped_shared_issues':kernel_issues+scale_issues,
      'actual_tail_runtime_and_dispatch_proven':n==64,'unpriced_initializer_transpose_F64_ABI':True}


def build():
    gb=subprocess.check_output(['git','show','1c37cdaa9:'+G]);graph=json.loads(gb)
    cb=subprocess.check_output(['git','show','922a6b673:'+C]);text=cb.decode()
    assert 'one shared op/SM/cycle' in text and 'shared_used=False' in text
    modelblob=subprocess.check_output(['git','show','e416630f0:tools/deepseek_hbm_complete_index_blas_model.py'])
    ops=[];rowsum=0;tilesum=0;fullsum=0;bytesum=0;issuesum=0
    for o in graph['operations']:
      if o['function']!='index_scores':continue
      r=o['ordinary_recipe_phases'][0]['rows_per_rank'];rank=[]
      for i,n in enumerate(r):
        full,tail=divmod(n,64);wt=work(tail) if tail else {'source_shaped_shared_bytes':0,'source_shaped_shared_issues':0}
        base=work(64);b=full*base['source_shaped_shared_bytes']+wt['source_shaped_shared_bytes'];commands=full*base['source_shaped_shared_issues']+wt['source_shaped_shared_issues']
        rank.append({'logical_rank':i,'keys':n,'full64tiles':full,'tail_keys':tail,'tiles':full+bool(tail),
          'source_shaped_shared_bytes':b,'source_shaped_shared_issues':commands,'tail_shape':wt,
          'physical_die_SM_assignment':None})
        rowsum+=n;tilesum+=full+bool(tail);fullsum+=full;bytesum+=b;issuesum+=commands
      ops.append({'pc':o['pc'],'layer':o['layer'],'authoritative_dependencies':o['dependencies'],'ranks':rank})
    assert len(ops)==8
    rank_floors=[]
    for rank_id in range(96):
      fulltiles=sum(o['ranks'][rank_id]['full64tiles'] for o in ops)
      issues=fulltiles*work(64)['source_shaped_shared_issues']
      cycles=(issues+31)//32
      rank_floors.append({'logical_rank':rank_id,'full64tiles':fulltiles,
        'fulltile_shared_issues':issues,'ideal32SM_aggregate_pool_cycles':cycles,
        'candidate_0p9GHz_microseconds':cycles/900,
        'historical_budget_microseconds':442,
        'budget_verdict':'FAIL_CURRENT_LOWERING_BUDGET' if cycles>442*900 else 'UNQUALIFIED',
        'scope':'full tiles only; pool total work before rounding; rank-to-die placement unbound'})
    control_pins=[]
    for rev,path in [('c01fc4b72','tools/engram_clock_boundary_capture.py'),('5b8c456a3','tools/engram_sync_branch_drain_inventory.py')]:
      raw=subprocess.check_output(['git','show',rev+':'+path]);control_pins.append({'git':rev,'path':path,'sha256':hashlib.sha256(raw).hexdigest()})
    return {'schema':'w13.index-rank-port-join.v2','source_pins':[
      {'git':'1c37cdaa9','path':G,'sha256':hashlib.sha256(gb).hexdigest()},
      {'git':'922a6b673','path':C,'sha256':hashlib.sha256(cb).hexdigest()},
      {'git':'e416630f0','path':'tools/deepseek_hbm_complete_index_blas_model.py','sha256':hashlib.sha256(modelblob).hexdigest()}],
      'operations':ops,'logical_rank_count':96,'aggregate_keys_across_source_ranks':rowsum,
      'aggregate_tiles_across_source_ranks':tilesum,'aggregate_full64tiles':fullsum,
      'aggregate_tailtiles':tilesum-fullsum,'source_shaped_shared_bytes_across_ranks':bytesum,
      'source_shaped_shared_issues_across_ranks':issuesum,
      'per_rank_aggregate_pool_lower_floors':rank_floors,
      'historical_442us_budget_verdict':'FAIL_CURRENT_LOWERING_BUDGET',
      'lower_floor_exclusions':['tails','finite result STORE bridge','replication/refill/padding','other graph operations','bank conflicts','dependencies','provider/ACK/CDC service'],
      'model_port_contract':{'SMs_per_candidate_die':32,'lanes_per_SM':128,'resident_warps_per_SM':32,
        'RF_32bit_read_ports_per_lane':2,'RF_logical_write_ports_per_lane':1,'RF_read_bits_per_serial_cycle_per_SM':8192,
        'RF_write_bits_per_serial_cycle_per_SM':4096,'physical_RF_readcopy_writes':2,
        'shared_combined_bytes_per_serial_cycle_per_SM':128,'shared_warp_issues_per_serial_cycle_per_SM':1,
        'shared_banks':32,'bank_word_bytes':4,'shared_capacity_bytes':65536,
        'clock_GHz_target_only':{'serial':0.9,'fabric':1.2},'physically_measured_rates':None},
      'full64_fixture_capacity_floor':{'shared_bytes':3828224,'shared_issues':38092,
        'one_SM_shared_byte_cycles':29908,'ideal32SM_shared_byte_cycles':935,
        'one_SM_contract_shared_issue_cycles':38092,'ideal32SM_contract_shared_issue_cycles':1191,
        'scope':'conditional source scheduler one issue/SM; not physical issue qualification or per-token latency'},
      'tail_cost_provenance':'analytical source-loop/padding formulas; original-tail exceptional dispatch/runtime still unproven',
      'query_cache_credit':False,'partition_query_replication_padding_refill_cost_included':False,
      'additional_phase_traffic_must_join':['finite result register-to-shared STORE before exception LOAD','accumulator initialization','source/query transpose','F64 ABI output widening','32SM proposal duplicated qdecode/refill/padding','descriptor publication/read leases/actualACK/CDC'],
      'Avicenna_sync_control_source_pins':control_pins,'Avicenna_sync_control_condition':'c01fc4b72/5b8c456a3 requires actualclock/branchcontrol/fulltree drain/gate/capture wholejoin; no generic24928FIFO substitute',
      'actual_physical_SM_placement':None,'runtime_branch_and_shared_bank_calendar':None,
      'source_provider_ACK_CDC_drain':None,'SS_FF':None,'whole_token_cycles':None,'rate_credit':0,
      'hardware_launch':False,'model_admission':'FAIL_CLOSED','checkpoint_reads':0}

if __name__=='__main__':
 import sys
 Path(sys.argv[1]).write_text(json.dumps(build(),separators=(',',':'))+'\n')
