#!/usr/bin/env python3
"""TP96 standard-GPU kernel/service lowering candidate, model only.

Schedules instructions and bytes, never tensor values. No engine RTL, no
host arithmetic backend. Existing SM SIMD/RF opcode path is absent and must
be built only after unified-model area/routes/full-token cycles admission.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'results/rtl/w19_checkpoint_production_20261001'


def instruction(op,dst=None,src=(),lat=3,shared=False):
    return dict(op=op,dst=dst,src=list(src),latency=lat,shared=shared)


def chunk_program(norm=False):
    ops=[]
    if not norm:
        ops.extend(instruction('LDS32',f'w{k}',lat=2,shared=True) for k in range(8))
    ops.extend(instruction('LDS_PACKED_BF16',f'b{k}',lat=2,shared=True) for k in range(4))
    ops.extend(instruction('BF16_WIDEN',f'x{k}',[f'b{k//2}']) for k in range(8))
    # Product and add are separate instructions: no FMA contraction.
    ops.extend(instruction('FMUL',f'p{k}',[f'x{k}',f'x{k}' if norm else f'w{k}'],9) for k in range(8))
    ops.extend(instruction('FADD','sum',[f'p{k}']+(['sum'] if k else []),9) for k in range(8))
    for level in range(5):
        ops.extend([instruction('SHFL_PAIR',f'other{level}',['sum']),
                    instruction('FADD','sum',['sum',f'other{level}'],9)])
    ops.append(instruction('STS_PARTIAL',src=['sum'],shared=True))
    return ops


def schedule_warps(program,warps):
    """Four warp32 partitions, one issue/partition/cycle, one shared op/SM/cycle.

    Register scoreboard enforces source readiness at LAT7. Conservative
    deterministic round-robin. Shared latency1 is a candidate macro contract,
    not a routed RF/shared-memory measurement.
    """
    if not 0<warps<=32:raise ValueError('resident warp limit32')
    written=set()
    for op in program:
        if op['latency']<1:raise ValueError('nonpositive instruction latency')
        if not set(op['src'])<=written:raise ValueError('read of unwritten RF register')
        if op['dst']:written.add(op['dst'])
    pc=[0]*warps;ready=[{} for _ in range(warps)]
    cursor=[0]*4;cycle=0;issued=Counter();shared_cycles=0
    rf_writes=[set() for _ in range(4)];retire_at=0
    while any(p<len(program) for p in pc):
        shared_used=False
        for partition in range(4):
            pool=list(range(partition,warps,4))
            if not pool:continue
            for advance in range(len(pool)):
                slot=(cursor[partition]+advance)%len(pool);w=pool[slot]
                if pc[w]==len(program):continue
                op=program[pc[w]]
                if op['shared'] and shared_used:continue
                if any(ready[w].get(r,0)>cycle for r in op['src']):continue
                write_cycle=cycle+op['latency']
                if op['dst'] and write_cycle in rf_writes[partition]:continue
                if op['dst']:
                    ready[w][op['dst']]=write_cycle
                    rf_writes[partition].add(write_cycle)
                issued[op['op']]+=1
                retire_at=max(retire_at,write_cycle)
                if op['shared']:shared_used=True;shared_cycles+=1
                pc[w]+=1;cursor[partition]=(slot+1)%len(pool)
                break
        cycle+=1
        if cycle>100000:raise ValueError('scheduler deadlock')
    return dict(cycles=max([cycle,retire_at]+[t for regs in ready for t in regs.values()]),
                instructions=dict(issued),shared_issue_cycles=shared_cycles,
                rf_write_slots=[len(s) for s in rf_writes],
                resident_warps=warps,scalar_products=warps*32*8,
                scalar_chunk_adds=warps*32*8)


def admit_controller_request(address,sectors,write=False,AW=27):
    if not 1<=sectors<=16 or (write and sectors!=1):
        raise ValueError('unsafe LENW5/BEATW4 request length')
    if address<0 or address+sectors>1<<AW:
        raise ValueError('resident sector aperture overflow')
    return dict(address=address,sectors=sectors,write=write)


def controller_run(address,sectors,AW=27):
    if sectors<1:raise ValueError('empty controller run')
    commands=[]
    while sectors:
        n=min(sectors,16)
        commands.append(admit_controller_request(address,n,AW=AW))
        address+=n;sectors-=n
    return commands


def index_loop_descriptors(n,rank):
    if n<1 or not 0<=rank<96:raise ValueError('invalid TP96 scan')
    cycles,tail=divmod(n,768)
    rows=cycles*8+min(8,max(0,tail-rank*8))
    return [dict(local_base=start,count=min(1024,rows-start),rank=rank,
                 global_id='((local_base+lane)//8)*768+rank*8+(local_base+lane)%8',
                 reduction='complete32-head score reduction per row before loop advance',
                 descriptor_count_bits=16,global_id_bits=32)
            for start in range(0,rows,1024)]


def hc_compute():
    waves=[]
    for chunks in [1024,1024,512]:
        warps=chunks//32
        waves.append(dict(chunks=chunks,coefficient_bytes=chunks*8*4,activation_bytes=chunks*8*2,
                          shared_refill_cycles=(chunks*8*6)//128,
                          projection=schedule_warps(chunk_program(),warps),
                          norm=schedule_warps(chunk_program(True),warps)))
    # The80 warp partials form128 leaves (+0 pad), four ordinary warp32
    # trees, then one four-leaf tree. Separate shuffle and FP32 ADD stages.
    final_tree_cycles=2+5*(3+9)+3+2+2*(3+9)+3
    return dict(output_rows=24,K=20480,chunk_terms=8,chunks=2560,
                assignment='row o -> SM o for o0..23; norm -> SM24; remaining SMs participate in32SM barrier',
                waves=waves,final_tree_cycles_candidate=final_tree_cycles,
                projection_cycles_candidate=sum(w['shared_refill_cycles']+w['projection']['cycles'] for w in waves)+final_tree_cycles,
                norm_cycles_candidate=sum(w['activation_bytes']//128+w['norm']['cycles'] for w in waves)+final_tree_cycles,
                tree='per-thread eight sequential adds from+0; per-warp pairwise32 contiguous chunks;80 warp partials padded128; ordinary shuffles/shared RF exchange then pairwise tree; no FMA or reordering',
                coefficient_hbm_bytes_operator=1966080,
                activation_broadcast_bytes_operator=25*40960,
                coefficient_copy_policy='resident per rank; each coefficient processed once across24SMs, no BF16 fn conversion',
                local_collect_bytes_operator=25*4,
                collective='32SM standard grid barrier; collect24 raw row scalars +norm scalar atSM0; release only after all25 producers retire',
                qualifier='compute/refill issue schedule only; NoC, DMA latency, CDC, collector/barrier and memory bank timing not qualified')


def scalar_recipes():
    # Exact golden operation recipes on ordinary FP32/INT/SFU instructions.
    # Latencies are explicit proposed standard GPU unit service assumptions.
    # EXP uses direct golden Horner operations, not a ROM-specific ln2 table.
    return dict(
      rsqrt=dict(seed='0x5F3759DF-(bits(v)>>1)',half='FMUL(v,0.5)',iterations=3,
                 iteration=['FMUL(y,y)','FMUL(half,yy)','FADD(1.5,-half_yy)','FMUL(y,correction)'],
                 fp32_critical_cycles=9+3*4*9,integer_seed_cycles_candidate=6),
      exp=dict(clamp='golden EXP_MIN/MAX',range_reduce=['FMUL(x,LOG2E)','FADD(t,MAGIC)','FADD(u,-MAGIC)',
                  'FMUL(n,LN2_HI)','FMUL(n,LN2_LO)','FADD(x,-n_hi)','FADD(inner,-n_lo)'],
               horner_iterations=6,horner=['FMUL(p,r)','FADD(product,coefficient)'],
               scale='integer exponent update from p and n',fp32_operations=19,
               conservative_fp32_cycles=19*9,integer_control_cycles_candidate=18),
      sigmoid=dict(recipe='DIV(1,FADD(EXP(-x),1))',divisor_service='one standard32b divider/SM; active lanes serialized,II1,LAT19 candidate',
                   qualification='divider opcode wrapper/SSFF and full special-value gate pending'),
      sinkhorn=dict(matrix_shape=[4,4],iterations=20,initial='row max;EXP(comb-max);three ordered FADD per row;DIV16;FADD eps',
                    normalization_passes=39,pass_order='COL then19*(ROW,COL)',
                    one_pass=['four ordered warp operand shuffles','three ordered FADD per4-vector sum','FADD(sum,eps)','broadcast denominator by warp shuffle','DIV16elements'],
                    ordered_sum_cycles=3*9,epsilon_cycles=9,
                    division16_service_cycles_candidate=2+16+19-1,
                    shuffle_control_cycles_candidate=5*3,
                    normalization_cycles_candidate=39*(3*9+9+2+16+19-1+5*3),
                    total_comb_divisions=640,total_ordered_seq_adds=480,
                    comb_initial_output_eps_adds=16,normalization_denominator_eps_adds=39*4,
                    rounding='seqsum starts first term; no extra +0; every division is IEEE F32RNE'),
      norm=dict(recipe='chunk8 FP32 squared-sum tree;DIV(sum,F32(n));FADD(eps);golden rsqrt3Newton;FMUL scaling; BF16 rounding only at source-defined point',
                post_sum_scalar_cycles_candidate=2+19+9+(9+3*4*9)+6,
                activation_norm_contract='FUSE=[]: multiply x*r then gain, BF16 at golden point; no nfold adoption'),
      hc_mix_finish=dict(pre='four sigmoid +eps',post='four sigmoid *2',comb='sixteen FMUL(scale)+FADD(base), row softmax and20Sinkhorn iterations',
                         parallel_branch='pre/post/comb use disjoint registers; conservative serialize until GPU scheduler price'))


def kernel(op):
    fn=op['fn'];kind='SIMD';shape={};barriers=['operands staged','scoreboard dependencies retired']
    if fn=='hc_mixes':shape=dict(fn=[24,20480],norm=20480,sinkhorn=[4,4,20]);kind='HC_GPU_WARPS'
    elif fn in ['hc_pre_norm','final_norm']:shape=dict(hc=[4,5120],norm=5120)
    elif fn=='hc_post':shape=dict(residual=[4,5120],post=4,comb=[4,4],output=20480)
    elif fn=='engram_fetch':shape=dict(rows=24,row_codes=256,row_scales=8);kind='PACKED_TABLE_DMA_DECODE'
    elif fn=='engram_mix':shape=dict(residual=[4,5120],norms=[4,5120],dot=[4,5120])
    elif fn=='q_norm_kv_row':shape=dict(qnorm=1280,kvnorm=512,window_qdq=512);barriers+=['window paired code/scale commit']
    elif fn=='q_rope':shape=dict(head=512,rope_tail=64)
    elif fn=='compressor':shape=dict(group=op['group'],max_group_positions=2,pool_width=512,wk=[128,512],knorm=128);barriers+=['index/CKV paired append commit']
    elif fn=='index_q':shape=dict(heads=32,width=128,scale_weights=32)
    elif fn=='index_scores':shape=dict(global_rows=op['n'],key_width=128,query_heads=32,owner='(i//8)%96',row_loop_max=1024);kind='SHARDED_INDEX_WARPS'
    elif fn in ['cand_local','cand_apply','cand_mask']:shape=dict(block=8,local_top=2048,global_rows=op.get('n'));kind='F32_METADATA_SELECTION'
    elif fn=='topk_local':shape=dict(k=op['k']);kind='F32_METADATA_SELECTION'
    elif fn=='attend':shape=dict(heads_per_owner=1,width=512,window=128,selected=512 if op['yarn'] else 0);kind='ATTENTION_GPU_WARPS'
    elif fn=='router_act':shape=dict(rows_per_rank=4)
    elif fn=='route':shape=dict(router=384,topk=6);barriers+=['RTL-produced ID descriptors only']
    elif fn=='swiglu':shape=dict(rows_per_rank=24,slot=op['slot'])
    elif fn=='moe_sum':shape=dict(rank_rows_max=54,expert_terms=7,order='sorted6IDs then shared')
    elif fn=='argmax_local':shape=dict(rank_rows_max=1347);kind='F32_METADATA_SELECTION'
    else:raise ValueError('unlowered local function '+fn)
    return dict(kernel=kind,function=fn,shape=shape,owners=op['ranks'],barriers=barriers,
                arithmetic_source='tools/w19_hbm_tp96_isa.py:f_'+fn,
                opcode_encoding=None,connected_exactness=False,full_cycles=None)


def build():
    path=ROOT/'results/rtl/w19_hbm_tp96_program_oreduce.json';p=json.loads(path.read_text())
    graph=[]
    for layer in p['layers']:
        for op in layer['ops']:
            node=dict(sequence=len(graph),layer=layer['layer'],op=op['id'],kind=op['kind'],
                      predecessor=len(graph)-1 if graph else None)
            if op['kind']=='local':node['lowering']=kernel(op)
            elif op['kind']=='mv':node['lowering']=dict(kernel='EXISTING_MATRIX_COLUMNS',rows=op['rows'],n=op['n'],k=op['k'],
                input=op['x'],output=op['out'],fmt=op['fmt'],weight=op['w'],
                descriptor_source='accepted256 affine ledger; routed slot resolved from RTL IDs, no golden selection',
                barrier='SIMD/RF release then original matrix activation staging before issue; finite controller phase',connected_exactness=False)
            else:node['lowering']=dict(kernel='FINITE_GPU_SERVICE',source_op=op,connected_exactness=False)
            graph.append(node)
    sources=['tools/w19_gpu_simd_contract.py','tools/uarch_model.py','rtl/gpu/ot_gpu_sm_v.sv',
             'rtl/gpu/ot_gpu_fadd.sv','rtl/hdc/v41x/ot_hdc_v41x_sfu.sv','tools/hdc_golden.py',
             'tools/hdc_golden_v41.py','tools/w19_hbm_tp96_isa.py','rtl/hdc/kv/ot_hdc_hbm_model.sv',
             'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.lef',
             'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.json',
             'results/rtl/w19_checkpoint_production_20261001/resident-service-candidate-r1.json',str(path.relative_to(ROOT))]
    hc=hc_compute();scalar=scalar_recipes()
    # Conservative serial scalar branch accounting. These are candidate
    # microprogram cycles; transport/CDC/barrier unknowns must not be set0.
    scalar_cycles=dict(norm=scalar['norm']['post_sum_scalar_cycles_candidate'],
                       mix_scale=9,pre_post=9+9+189+9+(2+8+19-1)+9+9,
                       comb_softmax=9+9+(4+3)*3+9+189+(4*3+3*9)+3+(2+16+19-1)+9,
                       sinkhorn=scalar['sinkhorn']['normalization_cycles_candidate'])
    hc['scalar_dependency_cycles_candidate']=scalar_cycles
    hc['explicit_divisions_operator']=649
    hc['exp_elements_operator']=24
    hc['source_hc_operators_token']=80
    hc['local_compute_cycles_candidate']=max(hc['projection_cycles_candidate'],hc['norm_cycles_candidate']+scalar_cycles['norm'])+sum(v for k,v in scalar_cycles.items() if k!='norm')
    return dict(schema='opentallas.w19.tp96-gpu-simd-lowering-candidate.v1',status='MODEL_AND_INTERFACE_ADMISSION_PENDING',
      supersedes='609af8387 consumer compute/service organisation only; resident address allocations retained as capacity candidate. Dedicated HCP and wide SU are arithmetic/profile references, not GPU units.',
      source_pins={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in sources},
      numerical_contract=dict(arithmetic='chunk8',fusion=[],host_arithmetic=False,
                              fullshape_connected_exactness=False),
      organisation=dict(sm_count=32,simt_lanes_sm=128,partitions_sm=4,warp_threads=32,resident_warps_sm=32,
                        modeled_fp32_lanes_die=4096,implemented_general_simd_lanes=0,
                        statement='Current ot_gpu_sm_v is matrix-only. SIMD/RF/standard divider/INT/shuffle path is proposed additional implementation of model-budgeted GPU organisation, not existing RTL or dedicated HCP/SU adoption.'),
      register_file=dict(registers_thread=32,capacity_bytes_sm=131072,banks=128,word_bits=32,read_ports_bank=2,write_ports_bank=1,
                         read_bits_cycle_sm=8192,write_bits_cycle_sm=4096,read_latency_candidate=2,
                         macro='ot_sram_1r1w_128x256_m1_r2c2',macro_count_sm=64,macro_count_die=2048,
                         layout='16 groups of8lanes; each word256b,depth256=8warps*32regs;two128row depthbanks;two readcopies; all writes broadcast to bothcopies',
                         physical_capacity_bytes_sm=262144,physical_capacity_bytes_die=8388608,
                         depth_select_mux_bits_sm=8192,qualified_ported_area=False,
                         arbitration='one warp32 per partition; scoreboard; shared/SFU results reserve RF write slots, queue instead of unpriced multiwrite',
                         macros_and_area=None),
      shared_memory=dict(capacity_bytes_sm=65536,banks=32,bank_word_bits=32,read_ports_bank=1,write_ports_bank=1,
                         warp_port_bytes_cycle=128,read_latency_candidate=1,write_latency_candidate=1,
                         hc_tile_coefficient_bytes=32768,hc_tile_activation_bytes=16384,hc_partial_control_bytes=4096,
                         hc_live_bytes=53248,refill='singlebuffer no overlap; row/chunk loop tiles1024+1024+512; scratch eviction never changes resident HBM bases',
                         layout='row-major consecutive chunks;coefficient k warp load word8*chunk+k has8-way bank conflict in naive layout: DMA/transposed32x8 shared tile required',
                         scatter='stage tile term-major shared words k*1024+chunk; adjacent warp lanes address adjacent banks; BF16 packed pairs similarly term-pair-major',
                         transpose_buffer_bytes_coefficient=2048,transpose_buffer_bytes_activation=1024,
                         transpose_service='proposed normal DMA/swizzle32chunk x8term tile, double1KB coefficient/512B activation buffers outside64KBshmem; term-major128B writes; initial fill/drain cycles not free',
                         dma_scatter_and_port_model_pending=True,macros_and_area=None),
      ALU=dict(fp32_mul_lanes_sm=128,fp32_add_lanes_sm=128,mul_latency=7,add_latency=7,FMA=False,
               rf_to_result_scoreboard_cycles=9,
               issue='one warp opcode/partition/cycle; ADD/MUL share scheduler; RF2cycles+coreLAT7; separate primitives area charged, not128 fusedMAC estimate assumed equivalent',
               integer_shift_compare_shuffle='standard GPU paths proposed; area/routes/opcode/exactness pending',
               divider='one standard IEEE F32 divider/SM,II1 LAT19 candidate; actual wrapper/SSFF not qualified'),
      clocks=dict(simd_hz=900000000,fabric_hz=1200000000,
                   cdc='proposed16x128B async credit FIFO/SM for DMA to .9GHz shmem; release/acquire epoch barrier; clock-crossing latency/area/SSFF pending'),
      controller=dict(source='ot_hdc_hbm_model',NPC=32,LENW=5,BEATW=4,LENMAX=16,QD=64,RQD=32,RW=16,MAXSKIP=16,
                      CLK_PS=833,sector_bytes=32,safe_read_sectors=[1,16],safe_write_sectors=1,
                      ingress_command_ports_stack=1,ingress_max_bytes_command=512,
                      ingress_bytes_s_stack_clock_target=614400000000,ingress_bytes_s_die_clock_target=2457600000000,
                      boundary='ALL matrix/table/coefficient/state traffic shares single request port/stack;512B/cycle ceiling before queue/bank/refresh/turnaround losses',
                      RW_is_not_LENMAX=True,
                      invalid_length_policy='reject length0 or>16 before controller; readiness loops16 but enqueue loopsreq_len, so direct unchecked descriptors prohibited',
                      larger_command_adoption=False,
                      write_commit_and_RMW='MISSING writecompletion tag/fence; read-modify-write32B sectors holds address lock until commit; no read/other writer passes same-sector pending write',
                      acknowledgement_is_not_request_acceptance=True),
      phases=['resident HBM finite service->L2/NoC->shared tile staging','operand-ready barrier',
              'GPU warp32 separate F32 product/add/chunk tree','32SM result collect and norm/SFU dependencies',
              'scalar/selection/state commit barrier','matrix activation/weight refill->original matrix columns',
              'collective->current-token activation registers; next source op'],
      hc=hc,scalar_recipes=scalar,
      selection=dict(score_bits=32,score_format='IEEE F32 bits (BF16-valued index scores);+/-Inf supported sentinels',id_bits=32,
                     stable_order='score descending then globalID ascending; separate valid/epoch; no F64 arithmetic',
                     prior_capacity_reserves_retained=True,RTL_merge_and_masks_qualified=False),
      finite_loops=dict(index='owner(i//8)%96; local rows in ascending globalID; chunks<=1024 rows; new chunk after reduction retirement',
                        hc='24 row owners;each2560chunks in ascending order;3bounded scratch tiles, fulltree before scale',
                        SU='logical op count is software loop, never send >65535 toNW16;GPU descriptor/globalIDs32b; tile boundaries never split a golden reduction tree or drop partial state'),
      index_loop_profiles=[dict(layer=op['layer'],n=op['n'],ranks=[dict(rank=r,loops=index_loop_descriptors(op['n'],r)) for r in range(96)])
                           for layer in p['layers'] for op in layer['ops'] if op.get('fn')=='index_scores'],
      graph=graph,counts=dict(Counter(n['kind'] for n in graph)),full_token_cycles=None,
      prerequisites=['unified model prices whole2213-node serial graph including80HCnorms,80prenorms,80posts and80Sinkhorn loops plusall dependent services',
                     'RF/shared SRAM ports, scatter/bank conflicts, area/slot fit and NoC/clock-crossing routes',
                     'actual SIMD opcode/compiler backend and TP96 buffer/address lowering',
                     'write completion/RMW/nohazard pipeline model and interfaces before code',
                     'all connected consumer and fulltoken exactness gates before runtime claim'],
      full_token_qualified=False,physical_qualified=False,adopted=False)


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    if a.out.exists():ap.error('refuse overwrite: preserve evidence')
    c=build();a.out.write_text(json.dumps(c,separators=(',',':'))+'\n')
    print(json.dumps(dict(counts=c['counts'],hc_projection_cycles_candidate=c['hc']['projection_cycles_candidate'],
                         hc_norm_cycles_candidate=c['hc']['norm_cycles_candidate'],status=c['status'])))
