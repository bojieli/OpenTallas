"""Price source922a expanded score staging before any dispatcher binding.

No physical cycle or allocation is inferred from the software interpreter.
The source's external eq/ek register handoff is an explicit additional shared
STORE/LOAD obligation here. 32SM partition is a proposal with query replication,
not an admitted schedule or a free division of single-SM traffic by32.
"""
from pathlib import Path
from math import ceil
import gzip,hashlib,json
import deepseek_hbm_complete_canonical as Canon
ROOT=Path(__file__).resolve().parents[1]
RECEIPT=ROOT/'results/rtl/deepseek_hbm_complete_20261001/index-blas-production-candidate-r1.json.gz'

def layout(keys=64):
    if not 1<=keys<=64:raise ValueError('finite local key count')
    padded_keys=ceil(keys/32)*32
    sizes=[('query',128*33*4),('keys',keys*128*4),('weights',128),('descriptors',keys*32),
        ('joint_payload_descriptor_buffers',4*544),('q_sanitized',32*33*4),('k_sanitized',padded_keys*33*4),
        ('q_units',32*33*4),('k_units',padded_keys*33*4),('q_exp',128),('k_exp',padded_keys*4),
        ('finite_block',keys*32*4),('exception_state',keys*32*4),('chosen_blocks',4*keys*32*4),
        ('acc_ping',keys*32*4),('acc_pong',keys*32*4),('positive',keys*32*4),
        ('terms',keys*32*4),('head_reduction',keys*32*4),('output',keys*8),('zero_constant',4)]
    result={};cursor=0
    for name,size in sizes:
        cursor=ceil(cursor/256)*256
        result[name]={'base':cursor,'bytes':size,'end':cursor+size};cursor+=size
    return result,ceil(cursor/256)*256

def peak_live(keys=64):
    r,_=layout(keys)
    resident=['query','keys','weights','descriptors','joint_payload_descriptor_buffers']
    stages=[]
    for block in range(4):
        # chosen_blocks reserves four outputs conservatively from first block.
        # No release inferred from latency: requires actual downstream reads done.
        live=resident+['q_sanitized','k_sanitized','q_units','k_units','q_exp','k_exp','finite_block','exception_state','chosen_blocks']
        stages.append({'stage':f'block{block}_exception_merge','live_regions':live,
            'live_bytes':sum(r[n]['bytes'] for n in live),
            'release_requires':['all finite_block consumers done','exception_state/chosen STORE-visible',
                'q/k unit and scale final LOAD consumers done'],'physical_release_ticks':None})
    live=resident+['chosen_blocks','acc_ping','acc_pong']
    stages.append({'stage':'block_csum','live_regions':live,'live_bytes':sum(r[n]['bytes'] for n in live),
        'release_requires':['all chosen block LOADs consumed','last acc STORE-visible'],'physical_release_ticks':None})
    return stages,max(s['live_bytes'] for s in stages)

def addresses(regions,stage,symbol,warp,lanes,block=0):
    """Candidate source-variable word addresses; no provider aperture assigned."""
    base=lambda name:regions[name]['base']
    term=int(symbol[1:]) if symbol.startswith(('v','q','k')) and symbol[1:].isdigit() else None
    if stage=='q_sanitize':return [base('query')+4*((block*32+lane)*33+warp) for lane in lanes]
    if stage=='q_sanitize_store':return [base('q_sanitized')+4*(lane*33+warp) for lane in lanes]
    if stage=='k_sanitize':return [base('keys')+4*(warp*128+block*32+lane) for lane in lanes]
    if stage=='k_sanitize_store':return [base('k_sanitized')+4*(warp*33+lane) for lane in lanes]
    if stage in ('q_decode','k_decode'):
        if term is None:raise ValueError('actual decoder v0..31')
        return [base('q_sanitized')+4*(term*33+warp*32+lane) if stage=='q_decode'
                else base('k_sanitized')+4*((warp*32+lane)*33+term) for lane in lanes]
    if stage in ('q_unit_store','k_unit_store'):
        if term is None:raise ValueError('unit store term')
        return [base('q_units')+4*(term*33+warp*32+lane) if stage=='q_unit_store'
                else base('k_units')+4*((warp*32+lane)*33+term) for lane in lanes]
    if stage=='finite_block':
        if term is None:raise ValueError('actual q/k0..31')
        return [base('q_units')+4*(term*33+lane) if symbol[0]=='q'
                else base('k_units')+4*(warp*33+term) for lane in lanes]
    if stage=='exception_block':
        if term is None:raise ValueError('actual q/k0..31')
        return [base('query')+4*((block*32+term)*33+lane) if symbol[0]=='q'
                else base('keys')+4*(warp*128+block*32+term) for lane in lanes]
    if stage=='q_scale_load':return [base('q_exp')+4*lane for lane in lanes]
    if stage=='k_scale_load':return [base('k_exp')+4*warp for lane in lanes]
    if stage in ('finite_block_store','exception_state_store','finite_result','chosen_store','csum_block'):
        family={'finite_block_store':'finite_block','exception_state_store':'exception_state',
            'finite_result':'finite_block','chosen_store':'chosen_blocks','csum_block':'chosen_blocks'}[stage]
        offset=block*(regions['keys']['bytes']//512)*32 if family=='chosen_blocks' else 0
        return [base(family)+4*(offset+warp*32+lane) for lane in lanes]
    raise ValueError('unbound source memory operation '+stage)

def build():
    receipt=json.loads(gzip.decompress(RECEIPT.read_bytes()))
    for name,pin in receipt['source_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=pin:raise ValueError('source mismatch '+name)
    count=receipt['executed_whole64_ordinary_warp_opcode_counts'];metrics=receipt['executed_whole64_metrics']
    # Candidate latencies are isolated canonical costs, not composed service clocks.
    known={op:{'warp_events':n,'serial_latency_candidate':Canon.KNOWN[op]}
           for op,n in count.items() if op in Canon.KNOWN}
    unknown={op:n for op,n in count.items() if op not in Canon.KNOWN}
    full,arena=layout(64);live,peak=peak_live(64);local,localarena=layout(2);local_live,localpeak=peak_live(2)
    # q_exp128B+k_exp256B stores, followed by q_exp8192B+k_exp256B
    # loads across64 key warps, for EACH of four32-term blocks.
    scale_bridge={'shared_bytes':4*(128+256+8192+256),'warp_issues':4*(1+2+64+64),
        'source_handoff':'X.decode returns regs[e]; X.block initializes external eq/ek without a source STORE/LOAD',
        'candidate_added_ops':{'STORE':12,'LOAD':512},'producer_consumer_barrier':'scale STORE-visible before finite block LOAD',
        'actual_visibility_ticks':None,'qualified_cycles':None}
    traffic=metrics['shared_requested_bytes']+scale_bridge['shared_bytes']
    phases=[]
    for block in range(4):
        for kind,reads,writes in [('q_sanitize',['query'],['q_sanitized']),('k_sanitize',['keys'],['k_sanitized']),
            ('q_decode',['q_sanitized'],['q_units','q_exp']),('k_decode',['k_sanitized'],['k_units','k_exp']),
            ('finite_block',['q_units','k_units','q_exp','k_exp'],['finite_block']),
            ('exception_merge',['query','keys','finite_block'],['exception_state','chosen_blocks'])]:
            phases.append({'source_kernel_index':len(phases),'block':block,'kind':kind,'reader_regions':reads,'writer_regions':writes,
                'source_address_function':kind if kind!='exception_merge' else 'exception_block',
                'producer_barrier':'all corresponding input STORE-visible and return identity matched before LOAD',
                'scratch_reuse_barrier':'all corresponding last LOAD consumers done; no latency timer',
                'physical_ticks':None})
    for step in range(8):
        phases.append({'source_kernel_index':24+step,'kind':'block_csum_FADD','step':step,
            'reader_regions':['acc_ping' if step%2==0 else 'acc_pong','chosen_blocks' if step<4 else 'zero_constant'],
            'writer_regions':['acc_pong' if step%2==0 else 'acc_ping'],'nan_priority':'left',
            'producer_barrier':'corresponding acc and chosen STORE-visible','physical_ticks':None})
    for index,kind,reads,writes,policy in [(32,'BF16_MAX',['acc_ping'],['positive'],'source compare bitwrapper'),
        (33,'weight_FMUL',['positive','weights'],['terms'],'right'),
        (34,'terms_BF16',['terms'],['terms'],'integer source rounding'),
        (35,'head_chunk_tree',['terms'],['head_reduction'],'chunk right;tree left')]:
        phases.append({'source_kernel_index':index,'kind':kind,'reader_regions':reads,'writer_regions':writes,
            'nan_priority':policy,'producer_barrier':'matching input STORE-visible','physical_ticks':None})
    return {'schema':'opentallas.deepseek.index-blas-expanded-model.v1',
        'source_receipt_sha256':hashlib.sha256(RECEIPT.read_bytes()).hexdigest(),
        'source_pins':{**receipt['source_sha256'],'tools/deepseek_hbm_complete_index_blas_model.py':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
        'original_batch_shapes':[5456,5464,10920,10928,16384],'source_tile_keys':64,'head_lanes_per_key':32,
        'source_kernel_phase_bindings':phases,
        'source_stage_traffic_decomposition':{
            'q_sanitize_q_decode':{'shared_bytes':81920,'warp_issues':640},
            'key_sanitize_key_decode':{'shared_bytes':163840,'warp_issues':1280},
            'finite_block':{'shared_bytes':1081344,'warp_issues':16384,'key_LOAD_source_flag':'broadcast=True;4requested bytes perwarp'},
            'always_exception_merge':{'shared_bytes':2195456,'warp_issues':17152,'key_LOAD_source_flag':'no broadcast flag;128requested bytes perwarp'},
            'finish':{'shared_bytes':270336,'warp_issues':2112}},
        'full_query_cache_capacity_counterexample':{'row_major_query_raw_units_scales_bytes':33280,
            'pitch33_query_raw_units_scales_bytes':34304,'raw64keys_bytes':32768,
            'row_major_before_metadata_outputs_bytes':66048,'pitch33_before_metadata_outputs_bytes':67072,
            'SM_capacity_bytes':65536,'verdict':'REJECT whole64 rawkeys plusfullquery cache; blockwave/partition requires explicit costs'},
        'additional_missing_execution_events':{
            'accumulator_initialization':{'source':'np.zeros((64,32),F32)','candidate_required':'ordinary MOV+STORE or explicitly fused literal','bytes_if_shared':8192,'warp_STORE_issues':64,'qualified_cycles':None},
            'zero_constant_initialization':{'bytes':4,'candidate_required':'source+0 literal or visible immutable shared word','qualified_cycles':None},
            'F64_ABI_output_bridge':{'source':'head F32 -> np.astype(F64) into is_v','integer_bit_widening_recipe_bound':False,
                'output_bytes_per64keys':512,'RF_words_per_value':2,'qualified_cycles':None},
            'producer_query_transpose':{'source_query_row_major_to_pitch33':'additional staging copy required','qualified_cycles':None}},
        'executed_warp_opcode_counts':count,'known_isolated_opcode_costs':known,'unpriced_opcode_counts':unknown,
        'executed_RF_operand_bits_including_immediates':metrics['RF_read_bits_including_immediates'],
        'executed_RF_write_bits':metrics['RF_write_bits'],'executed_divergent_warp_branches':metrics['divergent_warp_branches'],
        'scale_handoff_bridge':scale_bridge,'expanded_requested_shared_bytes':traffic,
        'counted_traffic_is_not_complete_dispatcher_cost':True,
        'expanded_shared_warp_issues':metrics['shared_warp_issues']+scale_bridge['warp_issues'],
        'single_SM_shared_bandwidth_floor_serial_cycles':ceil(traffic/128),
        'single_SM_shared_issue_floor_if_one_warp_command_per_cycle':metrics['shared_warp_issues']+scale_bridge['warp_issues'],
        'actual_shared_command_issue_ports_bound':False,
        'floors_are_not_actual_latency':True,'actual_kernel_RF_read_write_ticks':None,
        'eager_single_SM':{'regions':full,'unaliasing_arena_bytes':arena,'live_stages':live,'peak_live_payload_bytes':peak,
            'SM_shared_capacity_bytes':65536,'capacity_fit':peak<=65536,'verdict':'REJECT exceeds64KB; old63488 codec fit not applicable'},
        'partition_proposal':{'SMs':32,'key_warps_per_SM':2,'FP32_lanes_per_SM':128,'warp_width':32,
            'regions_per_SM':local,'unaliasing_arena_bytes_per_SM':localarena,'live_stages':local_live,
            'peak_live_payload_bytes_per_SM':localpeak,'SM_shared_capacity_bytes':65536,'capacity_fit_only':localarena<=65536,
            'replicated_query_bytes_per_die':32*local['query']['bytes'],
            'query_refill_extra_shared_copy_bytes_per_tile':31*local['query']['bytes']*2,
            'query_scale_and_unit_compute_replica_count':32,
            'key_decoder_active_source_lanes_per_SM':32,
            'key_decoder_padding_rows_per_SM':30,'key_decoder_padding_zero_init_bytes_per_SM':30*32*4,
            'key_decoder_padding_zero_init_extra_bytes_per_die':32*30*32*4,
            'key_decode_warp_work_inflation_vs_full64':16,
            'padding_lane_suppression_lowerer_bound':False,
            'shared_macro_bytes_per_die':32*65536,'lane_RF_ports':'2R1W; version allocation Boyle pending',
            'source_key_scalar_reads':'sameword broadcast candidate;32lane fanout/port service not qualified',
            'barriers':['query transpose/refill visible on every assigned SM','key return/rowlease held through consumerdone',
                        'scale bridge stores visible before block arithmetic','chosen/acc/terms stores visible before next kernel',
                        'output actual writecommit before rowlease/descriptor slot reuse'],
            'area_replica_mux_fanout_cost':None,'NoC_route_tracks':None,'CDC_cycles':None,'whole_phase_cycles':None,
            'floorplan_and_schedule_admission':False},
        'HBM_ingress':{'stacks_per_rank':4,'safe_max_sectors_per_command':16,'sector_bytes':32,
            'command_bytes':512,'commands_per_stack_cycle':1,'maximum_bytes_per_rank_fastcycle':2048,
            'actual_request_ingress_competition':None,'writecommit_ACK_reverse_CDC':None},
        'source_domain_and_tail_dispatch_complete':False,'producer_dispatcher_bound':False,
        'joint_provider_context_priced':False,'whole_token_cycles':None,'adoption_1percent_gate':None,
        'model_admission':'FAIL_CLOSED','hardware_build_authorized':False,'checkpoint_reads':0}
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);args=p.parse_args()
    Path(args.output).write_text(json.dumps(build(),indent=2)+'\n')
