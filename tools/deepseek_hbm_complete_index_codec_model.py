"""Full finite index quantizer/transpose/pack/decode phase demand, no RTL credit."""
from pathlib import Path
import hashlib,json
import deepseek_hbm_complete_index_codec as C
import deepseek_hbm_complete_index_ports as P
import deepseek_hbm_complete_calendar as Calendar

SCRATCH_BASE=P.END
SCRATCH_BYTES=32*33*4
END=SCRATCH_BASE+SCRATCH_BYTES


def transpose(row_base,term_base,count=64,family='key'):
    if row_base not in (0,32) or term_base not in (0,32,64,96) or not 1<=count<=64:
        raise ValueError('finite source tile')
    if family not in ('key','query') or (family=='query' and count>32):raise ValueError('source family geometry')
    source_base=16384 if family=='key' else 0
    rows=min(32,max(0,count-row_base));events=[]
    for row in range(rows):
        events.append({'kind':'read-source-code-warp','row':row_base+row,
                       'source_addresses':[source_base+4*((row_base+row)*128+term_base+lane) for lane in range(32)],
                       'scratch_addresses':[SCRATCH_BASE+4*(row*33+lane) for lane in range(32)],
                       'requires':'source quantizer code STORE-visible','actual_hardware_timestamp':None})
    reads=[]
    for term in range(32):
        reads.append({'term':term_base+term,
                      'addresses':[SCRATCH_BASE+4*(row*33+term) for row in range(rows)],
                      'requires':'all matching transpose scratch STORE-visible before pack LOAD',
                      'actual_hardware_timestamp':None})
    return {'copy_events':events,'packer_read_events':reads,
            'source_family':family,
            'scratch_reuse_requires':'all four word packer scratch LOAD consumers done',
            'copy_read_bytes':rows*128,'copy_write_bytes':rows*128,
            'copy_shared_warp_issues':rows*2,'qualified_cycles':None}


def build():
    root=Path(__file__).resolve().parents[1]
    recipes={'classify':C.classify_program(),'route':C.route_program(),
             'quantizer':C.quant_program(),'packer':C.pack_program(),'decoder':C.decode_program()}
    profiles={k:Calendar.profile(v) for k,v in recipes.items()}
    nonfinite=[]
    import numpy as np
    for name,value in [('positiveInf',np.float32(np.inf)),('quietNaN',np.float32(np.nan))]:
        row=np.full(32,value,np.float32)
        with np.errstate(invalid='ignore',over='ignore'):
            amax=np.maximum(np.max(np.abs(row)),C.V.FP4_AMAX_FLOOR_E8M0)
            e=int(C.V._ceil_log2(C.G.mul(amax,C.V.FP4_MAX_INV)))
            decoded=C.V.qdq_fp4_e8m0(row)
        nonfinite.append({'input':name,'input_bits':int(value.view(np.uint32)),
                          'source_exponent':e,'raw_exponent_plus127':e+127,
                          'source_output_bits':int(decoded[0].view(np.uint32)),
                          'reachability_in_full_program_proved_absent':False})
    paths=['tools/deepseek_hbm_complete_index_codec.py',
           'tools/deepseek_hbm_complete_index_codec_model.py',
           'tools/deepseek_hbm_complete_packed_index_provider.py',
           'tools/deepseek_hbm_complete_index_consumer.py',
           'tools/deepseek_hbm_complete_index.py','tools/deepseek_hbm_complete_canonical.py',
           'tools/hdc_golden.py','tools/hdc_golden_v41.py','tools/w19_hbm_tp96_isa.py',
           'tests/test_deepseek_hbm_complete_index_codec.py',
           'tests/test_deepseek_hbm_complete_index_codec_model.py']
    return {'schema':'opentallas.deepseek.index-full-codec-phase.v1',
            'source_pins':{p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths},
            'finite_input_domain':'packed ordinary quantizer handles all finite F32; nonfinite source inputs retain actual source-produced decoded F32 bits in format2',
            'reachable_scale_bytes':[1,253],'scale0_254_255':'unreachable from finite F32 quantizer amax floor and F32 mul/ceil exponent; reject malformed payloads',
            'finite_domain_bound_proof':{
                'lower':'amax floor=6*2^-126; F32 multiply by source1/6 rounds to2^-126; ceil=-126;stored byte1',
                'upper':'amax<=max finite F32; monotone source F32 multiply/bitceil has maximum126;stored byte253',
                'scale254':'would require e127; absent for finite inputs and absent for +/-Inf input, which gives e128',
                'scale0':'would require e-127 below source floor; NaN e129/code256 must never wrap to0'},
            'raw_nonfinite_source_counterexamples':nonfinite,
            'whole_source_input_domain_closed':False,
            'transport_domain_closed_with_source_F32_fallback':True,
            'fallback_GPU_producer_lowering_complete':False,
            'fallback_score_consumer':'actual H.f_index_scores with private chunk8 reference globals; current returned operands, no golden injection; oracle only, not ordinaryGPU implementation',
            'fallback_score_GPU_lowering_complete':False,
            'scale253':'code-dependent F32 overflow to signed Inf preserved; code0/8 preserve zero signs; smaller codes finite',
            'BF16':'ordinary U32 RNE bit recipe matches G.to_bf16; never force canonical+0 on bit-transport',
            'wire':'16 little-endian U32 of eight low-nibble-first E2M1 codes each, then U32 of four UE8M0 scales',
            'producer_binding':'PackedIndexExecutor private f_compressor/f_index_q source globals -> ProducerBinding; produced row carries its own 68B payload',
            'provider_binding':'PackedIndexStateArray tagged68B/512B software payload commit ->descriptor commit ->consumer lease ->release; initial fixture remains decoded F32; physical provider unbound',
            'programs':recipes,'profiles':profiles,'finite_tile_keys':64,'full_tile_quantizer_warps':256,
            'opcode_service_demand':{k:{'warp_invocations_per64keytile':256 if k in ['quantizer','classify'] else 64 if k=='route' else 2,
                'warp_instruction_counts_upper':p['warp_instruction_upper_all_divergent_arms'],
                'RF_operand_bits_upper_per_warp':p['RF_read_bits_including_immediates'],
                'RF_result_bits_upper_per_warp':p['RF_write_bits'],
                'shared_issue_count_upper_per_warp':p['shared_issue_cycles_upper'],
                'replica_budget':'128 ordinary SIMD lanes/SM x32SM/die; standard integer datapath must be costed, not free from FP32 budget',
                'extra_novel_quantizer_units':0,'physical_area_routes_and_cycles':None} for k,p in profiles.items()},
            'full_tile_packer_warps':2,'full_tile_decoder_warps':2,'shared_capacity_bytes':65536,
            'shared_allocation_bytes':END+2048+2176,'packed_codec_shared_bytes':END,
            'shared_regions':{'query':[0,16384],'key_source_codes_then_decoded':[16384,49152],
                'query_scales':[49152,49664],'key_scales':[49664,50688],'raw_packed':[50688,55040],
                'transpose_scratch_pitch33':[SCRATCH_BASE,END],
                'tile64_descriptors_or_prepublication_classification_flags':[END,END+2048],
                'joint4_payload512_descriptor32_row_buffers':[END+2048,END+2048+2176]},
            'transpose_templates':[transpose(r,t) for r in [0,32] for t in [0,32,64,96]],
            'query_transpose_templates':[transpose(0,t,32,'query') for t in [0,32,64,96]],
            'decoded_output_maps':{'key':'word=4096+term*64+key_row,one unpack key/lane',
                                   'query':'word=term*32+head,one unpack head/lane'},
            'phase_order':['source F32 input visible,row-major key input bank map',
                'typed IEEE exponent classify ->SHFL/OR block flags ->ordinary four-block OR route; consume classification flags before descriptor overwrite',
                'quantizer warp32 one block/lane;source LOAD consumed before same row code STORE',
                'scale lane0 STORE,all codes visible',
                '32x32 copy to pitch33 scratch,read/write32 distinct banks',
                'packer warp32 one key/lane;scratch column LOAD32 distinct banks;four word outputs visible before scratch reuse',
                'all17 packed words committed/read-return/visible before decoder',
                'decoder warp32 one key/lane;term-major key output banks unique',
                'score consumers complete before raw/key/scratch overwrite and reverse credit return'],
            'full_tile_shared_demand':{
                'quantizer_input_read_bytes':32768,'quantizer_code_write_bytes':32768,'quantizer_scale_write_bytes':1024,
                'transpose_read_bytes':32768,'transpose_write_bytes':32768,
                'packer_code_read_bytes':32768,'packer_scale_read_bytes':1024,'packer_raw_write_bytes':4352,
                'decoder_raw_read_bytes':65536,'decoder_value_write_bytes':32768,
                'classifier_source_read_bytes':32768,'classifier_partial_flag_write_bytes':1024,
                'route_flag_read_bytes':1024,'route_flag_write_bytes':256,
                'combined_bytes':303616,'serialized_warp_shared_issues_candidate':3178,
                'shared_bytes_per_serial_cycle_budget':128,'RF_reads':2,'RF_writes':1,
                'physical_issue_writeback_and_fabric_calendar':None},
            'query32_codec_demand':{'quantizer_warps':128,'packer_warps':1,'decoder_warps':1,
                                   'shared_bytes':151808,'serialized_warp_shared_issues_candidate':1589,
                                   'production_query_register_handoff':None},
            'score_operand_exception_classification':{
                'key64_shared_bytes':35072,'key64_memory_warp_issues':832,
                'query32_shared_bytes_once':17536,'query32_memory_warp_issues_once':416,
                'weight32_padded_classification_shared_bytes_once':548,'weight_memory_warp_issues_once':13,
                'tag1_may_still_decode_Inf':True,'classification_opcodes':['AND','IEQ','SHFL','OR'],
                'opcode_clock_area_and_physical_issue_calendar':None},
            'FP64_alternative_cost_obligations':{
                'source':'V.dots_q4 FP64 @ per32block ->F32+0 ->csum8; source host BLAS order/NaN operand policy not specified in Python',
                'tile_keys':64,'heads':32,'terms':128,'blocks32':4,
                'FP64_products':262144,'FP64_accumulation_steps_upper_starting_pluszero':262144,
                'FP64_to_F32_block_rounds':8192,'F32_block_csum_adds_including4paddedzero':16384,
                'GPU_FP64_lanes':None,'FP64_latency_and_area':None,
                'RF64':'each value2RF32words; 2source operands need4wordreads, cannot reuse2R32 budget for free',
                'shared64':'materializing all query/key FP64 values needs98304B>64KiB; on-demand standard widening would require explicit RF/issue cost',
                'source_exception_policy_bound':False,'physical_admission':'FAIL_CLOSED'},
            'cost_policy':'known opcode source canonical; unbound variants/branches not zero. Arithmetic counts bounded per finite warp loop; no software walltime clocks',
            'missing':['opcode/branch physical costs and RF slot arbitration',
                'SM assignment and full phase timeline with other traffic',
                'actual initial packed state provider and resident allocation',
                'controller partial-sector RMW/writevisible/reverseCDC and NoC routes',
                'fallback nonfinite producer ordinary GPU lowering and downstream exceptional blockdot/index consumer',
                'per-format actual stack distribution, allocations and HBM protocol join'],
            'format_protocol':{'magic':'IKD1','descriptor':'<4sBBHQ:magic,formatU8,flagsU8=0,lengthLE16,epochLE64;16byte zero padding to32B sector',
                'format1':{'payload_bytes':68,'initialized_sector_bytes':96,'LEN_sectors':3},
                'format2':{'payload_bytes':512,'initialized_sector_bytes':512,'LEN_sectors':16},
                'descriptor_LEN_sectors':1,'joint_publication_consumer_buffers':4,'row_buffer_bytes':544,
                'publication_rule':'matching actual software payload commit/consume first, then descriptor commit/consume; old row consumers block replacement; executor owns whole-op fence',
                'epoch_wrap':'reject >=2^64; no modulo-generation alias',
                'owner':'(global_key//8)%96; local=(global_key//768)*8+global_key%8',
                'physical_payload_base':None,'physical_descriptor_base':None,'stack_PC_selector':None},
            'Boyle_format_screen':{'tool_commit':'89c811222','evidence_commit':'2e2ac1d01',
                'path':'results/physical_abi3/asap7/gpu/w13_index_format_screen_20261001/screen.json',
                'scope':'independent candidate allF32/tagged capacity/service screening; format and actual layout join pending;750B bound singlequad only'},
            'model_authority':'Ram composed dependencies/Boyle ports/calendar',
            'qualified_cycles':None,'full_shader_checkpoint_reexecuted':False,
            'physical_admission':'FAIL_CLOSED','hardware_build_authorized':False}


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);a=parser.parse_args()
    if a.out.exists():raise SystemExit('preserve prior evidence')
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(build(),separators=(',',':'))+'\n')
