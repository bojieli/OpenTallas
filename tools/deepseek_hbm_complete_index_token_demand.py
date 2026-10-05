"""Actual TP96 index inventory and expanded kernel demand for Boyle/Ram.

This is resource demand, not a second whole-token dependency/timing graph.
Fixed model geometry/port rates are read from source. Physical opcode clocks,
ports/lease timings and achievable token latency remain unqualified.
"""
import ast,hashlib,json
from pathlib import Path
from math import ceil
import deepseek_hbm_complete_index_blas_model as M
ROOT=Path(__file__).resolve().parents[1]
PROGRAM=ROOT/'results/rtl/w19_hbm_tp96_program_oreduce.json'
CALENDAR=ROOT/'results/rtl/deepseek_hbm_complete_20261001/whole-program-calendar-r2.json'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def keyword_constants(path,keyword):
    tree=ast.parse(path.read_text())
    nodes=[node.value for node in ast.walk(tree) if isinstance(node,ast.keyword) and node.arg==keyword and isinstance(node.value,ast.Call)]
    if len(nodes)!=1:raise ValueError('ambiguous model resource '+keyword)
    result={}
    for item in nodes[0].keywords:
        try:result[item.arg]=ast.literal_eval(item.value)
        except (ValueError,TypeError):pass
    return result

def resources():
    uarch=ROOT/'tools/uarch_model.py';simd=ROOT/'tools/w19_gpu_simd_contract.py'
    tree=ast.parse(uarch.read_text())
    function=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='hbm_gpu_design')
    values=[ast.literal_eval(n.value) for n in ast.walk(function) if isinstance(n,ast.Assign)
            and any(isinstance(t,ast.Name) and t.id=='n_sm' for t in n.targets) and isinstance(n.value,ast.Constant)]
    if values!=[32]:raise ValueError('unbound/changed fixed SM geometry')
    org=keyword_constants(simd,'organisation');shared=keyword_constants(simd,'shared_memory');rf=keyword_constants(simd,'register_file');clocks=keyword_constants(simd,'clocks')
    if (org['sm_count'],org['simt_lanes_sm'],org['partitions_sm'],shared['warp_port_bytes_cycle'])!=(32,128,4,128):raise ValueError('resource contract changed')
    return {'SMs_per_rank_die':values[0],'FP32_SIMT_lanes_per_SM':org['simt_lanes_sm'],'partitions_per_SM':org['partitions_sm'],
        'shared_combined_bytes_per_SM_serial_cycle':shared['warp_port_bytes_cycle'],
        'shared_bank_count':shared['banks'],'shared_bank_read_ports':shared['read_ports_bank'],'shared_bank_write_ports':shared['write_ports_bank'],
        'RF_read_bits_per_SM_serial_cycle':rf['read_bits_cycle_sm'],'RF_logical_write_bits_per_SM_serial_cycle':rf['write_bits_cycle_sm'],
        'physical_RF_write_copies':2,'implemented_general_SIMD_lanes':org['implemented_general_simd_lanes'],
        'serial_hz_model_target_NOT_qualified':clocks['simd_hz'],'fabric_hz_model_target_NOT_qualified':clocks['fabric_hz'],
        'physical_clock_qualified':False,'actual_opcode_II_and_shared_command_ports':None,
        'source_pins':{'tools/uarch_model.py':sha(uarch),'tools/w19_gpu_simd_contract.py':sha(simd)}}

def owned_count(n,rank,tp=96,granule=8):
    blocks=ceil(n/granule);owned=max(0,(blocks-rank+tp-1)//tp)
    count=owned*granule
    if owned and (blocks-1)%tp==rank:count-=blocks*granule-n
    return count

def inventory():
    program=json.loads(PROGRAM.read_text());calendar=json.loads(CALENDAR.read_text())
    if (program['tp'],program['head_dies'],program['key_block'],program['position'])!=(96,64,8,1048575):raise ValueError('source program shape changed')
    calendar_index={x['layer']:x for x in calendar['operations'] if x['function']=='index_scores'}
    rows=[];pc=0
    for layer in program['layers']:
        for op in layer['ops']:
            if op.get('fn')=='index_scores':
                expected=calendar_index[layer['layer']];counts=[owned_count(op['n'],r) for r in range(96)]
                if counts!=expected['ordinary_recipe_phases'][0]['rows_per_rank'] or pc!=expected['pc']:raise ValueError('source/calendar ownership mismatch')
                ranks=[]
                for rank,count in enumerate(counts):
                    full,tail=divmod(count,64)
                    ranks.append({'rank':rank,'owned_keys':count,'full64_tiles':full,'tail_keys':tail,'total_tiles':full+bool(tail),
                        'tail_active_SM_count':ceil(tail/2),'tail_keys_on_first_SM':min(2,tail),
                        'original_CH16384_batches':[min(16384,count-a) for a in range(0,count,16384)],
                        'SM0_two_key_invocations':full+bool(tail),'active_SM_two_key_invocations':ceil(count/2)})
                rows.append({'program_pc':pc,'source_op_id':op['id'],'layer':layer['layer'],'KV_source_layer':op['src'],
                    'global_source_keys':op['n'],'query_heads':32,'key_dimensions':128,'ranks':ranks})
            pc+=1
    if pc!=2213 or len(rows)!=8:raise ValueError('wholeprogram/index coverage changed')
    return rows

def local2_cost():
    # Shape-fixed LOAD/STORE demand from922a actual two-key execution over
    # retained efdf synthetic raw/produced fixture, not production operand counts.
    # Branch-dependent instruction counts are never multiplied into token clocks.
    parts={'query_sanitize_decode':{'bytes':81920,'warp_issues':640},
        'key_sanitize_decode_with32_lane_padding':{'bytes':51200,'warp_issues':400},
        'finite_block':{'bytes':33792,'warp_issues':512},
        'always_exception_merge':{'bytes':68608,'warp_issues':536},
        'finish':{'bytes':8448,'warp_issues':66}}
    if sum(p['bytes'] for p in parts.values())!=243968 or sum(p['warp_issues'] for p in parts.values())!=2154:raise AssertionError('local2 metric decomposition')
    additions={
        'scale_handoff':{'bytes':1600,'warp_issues':24,'definition':'perblock qSTORE128+kSTORE8+qLOAD256+kLOAD8;fourblocks'},
        'finite_result_register_to_shared':{'bytes':1024,'warp_issues':8,'definition':'two key warps STORE128B each, fourblocks; source X.block returned regs'},
        'accumulator_reset':{'bytes':256,'warp_issues':2,'definition':'ordinary MOV +STORE for two key/head warps'},
        'decoder_padding_init':{'bytes':15360,'warp_issues':120,'definition':'four conservative fills:30padded rows x32words; no free acrossblock pad reuse'},
        'query_transpose_refill':{'bytes':32768,'warp_issues':256,'definition':'16384 actual words-byte payload read and write; unused pitch33 holes not read'},
        'weights_refill':{'bytes':256,'warp_issues':2,'definition':'128B source-produced weights read and write'},
        'zero_constant_init':{'bytes':4,'warp_issues':1,'definition':'one actual+0 shared word; no native host zero allocation credit'},
        'head_lane0_to_ABI_input':{'bytes':16,'warp_issues':3,'definition':'two scalar results LOAD from stride128/bank0, packed STORE; >=2 bankread waves'},
        'ABI_input_padding_init':{'bytes':120,'warp_issues':1,'definition':'30inactive key slots initialized, current ABI source executes all32 lanes'},
        'F32_to_F64_ABI':{'bytes':384,'warp_issues':3,'definition':'ordinary U32 LOAD128, STORE hi128 +lo128; exactly2valid outputs'},
    }
    cold=sum(p['bytes'] for p in parts.values())+sum(p['bytes'] for p in additions.values())
    cold_issues=sum(p['warp_issues'] for p in parts.values())+sum(p['warp_issues'] for p in additions.values())
    # Cache proposal: full decoded QUERY units/scales held for whole index op.
    # No arithmetic order changes: only invariant query computations reused.
    warm=cold-parts['query_sanitize_decode']['bytes']-additions['query_transpose_refill']['bytes']-additions['weights_refill']['bytes']-additions['zero_constant_init']['bytes']
    warm_issues=cold_issues-640-256-2-1
    prefill=81920+32768+256+4
    prefill_issues=640+256+2+1
    return {'source_local2_parts':parts,'mandatory_added_shared_events':additions,
        'cold_shared_bytes_per_SM_two_keys':cold,'cold_shared_warp_issues_per_SM_two_keys':cold_issues,
        'proposed_cache_steady_shared_bytes_per_SM_two_keys':warm,'proposed_cache_steady_warp_issues':warm_issues,
        'proposed_cache_prefill_shared_bytes_per_SM_per_index_call':prefill,'proposed_cache_prefill_warp_issues':prefill_issues,
        'fixed_mainloop_opcode_events_per_SM_two_keys':{'IMUL':256,'loop_IADD':256,'decode_FMUL':256,'weight_FMUL':2,'block_csum_FADD':16,'head_FADD':20,'F2I':256,'SHFL':20},
        'cache_prefill_moves_decode_FMUL_and_F2I_query_events_once_per_index':128,
        'branch_INT_RNE_reset_ABI_opcode_remainder':None,'physical_II_and_reconvergence':None,
        'NoC_queries_lease_writecommit_and_DMA_extra':None,'output_index_ID_U64_recipe_cost':None,
        'provider_valid_F64_output_bytes_per_two_keys':16,
        'provider_sector32_half_sector_merge_or_RMW_cost':None,
        'source_F64_arithmetic_ops_credited':0,'whole_dispatcher_demand_complete':False}

def cache_layout():
    source,_=M.layout(2);sizes={name:r['bytes'] for name,r in source.items()}
    sizes.update(q_units=128*33*4,q_exp=4*32*4,output=32*8,ABI_input=32*4,query_epoch_control=16)
    cursor=0;regions={}
    for name,size in sizes.items():
        cursor=ceil(cursor/256)*256;regions[name]={'base':cursor,'bytes':size,'end':cursor+size};cursor+=size
    arena=ceil(cursor/256)*256
    return {'regions_per_SM':regions,'arena_bytes_per_SM':arena,'capacity_only_fit':arena<=65536,
        'raw_query_and_decoded_units_replicas':32,'query_epoch_owner':'current produced iqf, sourceprogram PC; provider epoch/visibility not bound',
        'immutable_query_retention':'through all tiles of one index call; no reuse across different produced query epoch',
        'release':'last source query consumer done, all other operation scratch readers done; no timer',
        'bank_layout':'pitch33[term,head] for both raw query and cached units; shared32banks',
        'TMEM_or_special_HCP':False,'register_resident_epilogue_gain_adopted':False,
        'full_query_cache_software_exact_gate':False,'full_cache_RF_ports_context_fit':False,
        'physical_latency_gain_measured':False,'model_adoption':False}

def build():
    calls=inventory();rates=resources();cost=local2_cost();cache=cache_layout()
    totals=[]
    for rank in range(96):
        entries=[call['ranks'][rank] for call in calls];tiles=sum(e['total_tiles'] for e in entries);micro=sum(e['active_SM_two_key_invocations'] for e in entries)
        cold=tiles*cost['cold_shared_bytes_per_SM_two_keys']
        warm=tiles*cost['proposed_cache_steady_shared_bytes_per_SM_two_keys']+len(calls)*cost['proposed_cache_prefill_shared_bytes_per_SM_per_index_call']
        totals.append({'rank':rank,'index_calls':len(calls),'owned_key_scores':sum(e['owned_keys'] for e in entries),
            'full64_tiles':sum(e['full64_tiles'] for e in entries),'tail_tiles':sum(bool(e['tail_keys']) for e in entries),
            'SM0_two_key_invocations':tiles,'all_SM_two_key_invocations':micro,
            'cold_SM0_requested_shared_bytes':cold,'proposed_querycache_SM0_requested_shared_bytes':warm,
            'cold_rank_all_SM_shared_bytes':micro*cost['cold_shared_bytes_per_SM_two_keys'],
            'proposed_querycache_rank_all_SM_shared_bytes':micro*cost['proposed_cache_steady_shared_bytes_per_SM_two_keys']+len(calls)*32*cost['proposed_cache_prefill_shared_bytes_per_SM_per_index_call'],
            'physical_service_cycles':None})
    return {'schema':'opentallas.deepseek.index-token-demand.v1','whole_program_ops':2213,'TP':96,'context_capacity':1048576,
        'program_pin':{'path':str(PROGRAM.relative_to(ROOT)),'sha256':sha(PROGRAM)},
        'calendar_pin':{'path':str(CALENDAR.relative_to(ROOT)),'sha256':sha(CALENDAR)},
        'kernel_source_pins':{p:sha(ROOT/p) for p in ['tools/deepseek_hbm_complete_index_blas.py','tools/deepseek_hbm_complete_index_abi.py','tools/deepseek_hbm_complete_index_blas_model.py','tools/deepseek_hbm_complete_index_token_demand.py']},
        'fixed_unified_model_resources':rates,'source_index_calls':calls,'local2_demand':cost,'cache_proposal':cache,
        'rank_token_demand':totals,'package_scored_keys':sum(t['owned_key_scores'] for t in totals),
        'original_runtime_batches_preserved':True,'smallshape_BLAS_replacement':False,
        'ports_lifetimes_admission_owner':'Boyle; Ram composed wholeprogram graph',
        'Boyle_join_prerequisites':{'shared_port_floor':'3ac9528ac/service_floor_r2.json',
            'lane_version_allocator':'936a0841f selected one-key1237SSA only; notfull64',
            'no_same_address_RW':'32banks1R1W sameaddressRW forbidden',
            'RF_read_bits_per_SM_serial':8192,'RF_logical_write_bits_per_SM_serial':4096,'two_read_copy_write_fanout':2,
            'actual_ACK_return_drain_consumerdone_reverseCDC':None,'fullphase_epoch_and_scalar_halfsector_output_merge':None},
        'actual_physical_service_cycles':None,'whole_token_baseline_or_rate_credit':None,
        'full_clock_qualified':False,'dispatcher_binding_authorized':False,'checkpoint_reads':0,'new_CPU_lease':False}
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);args=p.parse_args()
    Path(args.output).write_text(json.dumps(build(),indent=2)+'\n')
