#!/usr/bin/env python3
"""Bounded, OFF GPU HC cost provider with explicit register/port cycle replay."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import subprocess
import types
import w16_gpu_hc_simt_contract as R
import w19_gpu_simd_contract as W
PROGRAM='results/rtl/w19_hbm_tp96_program_oreduce.json'
import w19_gpu_norm_calendar as N
ROOT=Path(__file__).resolve().parents[1]
OUT='results/uarch/w16_gpu_hc_dot_schedule_20261001'
INPUTS=OUT+'/inputs_r1.json'
NONLINEAR_COMMIT='c4613d8fed7e74417d059107a323e19406dfb91c'
GRAPH_COMMIT='0095fc4bc016ff1571e8316e836d5e522fc029e8'
NONLINEAR_PATH='tools/w19_hc_nonlinear_proof.py'
TC16_COMMIT='4f19cb6952e6a1f27c3a0d007b3aa7dd7a4ef94f'
TC16_PATH='results/physical_abi3/asap7/gpu/w13_tc16_terminal_20261001T120346Z/receipt.json'
BANK_COMMIT='0833a6613d0f0568dd28cb68fb1550b0d1b7c137'
BANK_PATH='tools/w19_landing_banks.py'


def assumptions():
    return dict(schema='opentallas.w16.bounded_HC_cost_inputs.v1',measured=False,
        RF_read_latency=2,shared_latency=2,mul_latency=7,add_latency=7,
        integer_latency=3,shuffle_latency=3,barrier_latency=8,
        warp_issue_interval=1,RF_words_thread=32,control_registers=4,
        shared_banks=32,RF_partition_count=4,warp_threads=32,
        RF_read_ports_lane=2,RF_write_ports_lane=1,
        loaded_HBM_ns=500,HBM_line_bytes=128,controllers=4,
        NoC_bytes_cycle=32,NoC_frame_header_bytes=16,network_startup_cycles=16,CDC_cycles=2,
        grid_barrier_rounds=5,landing_after_last_sector_cycles=3,
        bounded_credit_wait_cycles=450,serial_hz=900000000,fabric_hz=1200000000,
        policy='Positive proposed bounded single-HC isolated service;500ns loaded HBM model assumption, fixed450cycle credit wait assumption, finite32SM endpoints. No matrix concurrency or overlap. Bounds require owner confirmation and physical preflight, not measurements.')


def validate(p):
    R.require(p['measured'] is False,'measured flag invalid')
    for key,value in p.items():
        if key not in ('schema','measured','policy'):
            R.require(type(value) is int and value>0,'unknown/zero cost '+key)
    for key,value in dict(RF_words_thread=32,control_registers=4,shared_banks=32,
        RF_partition_count=4,warp_threads=32,RF_read_ports_lane=2,RF_write_ports_lane=1,
        HBM_line_bytes=128,controllers=4,serial_hz=900000000,fabric_hz=1200000000).items():
        R.require(p[key]==value,'unsupported resource '+key)


CONTROL={'@CHUNK':28,'@SHARED_BASE':30}
CONSTANTS=dict(W.CONSTANTS,**{key:dict(register=value) for key,value in CONTROL.items()},**{key:dict(readonly=True) for key in N.CONSTANTS},**{'@F20480':dict(readonly=True)})


def address_program(program):
    out=[]
    for op in program:
        if op['shared']:
            # Six explicit32bit shared address instructions; no64bit external
            # load in dot kernel. Bases/indices reside in reserved controls.
            for step in range(6):
                out.append(W.instruction('IADDR','ea',
                    ['@CHUNK','@SHARED_BASE'] if step==0 else ['ea'],3,
                    purpose=('scale leaf','term offset','add shared base','mask bank','form row','bounds/predicate')[step]))
            op=dict(op,src=op['src']+['ea'])
        out.append(op)
    return out


def lower(program,p):
    """SSA last-use allocator; reserve actual r28..31 for control/address pair."""
    validate(p);ssa=[];current={};uses={};definitions={}
    for pc,op in enumerate(program):
        src=[]
        for name in op['src']:
            if name in CONSTANTS:src.append(name)
            else:
                R.require(name in current,'unwritten register '+name)
                value=current[name];src.append(value);uses[value]=pc
        dst=None
        if op['dst'] is not None:
            dst=f'{op["dst"]}@{pc}';current[op['dst']]=dst;definitions[dst]=pc
            uses.setdefault(dst,pc)
        ssa.append(dict(op,src=src,dst=dst))
    free=list(range(28));assigned={};active={};physical=[];peak=0;bindings=[]
    for pc,op in enumerate(ssa):
        src_regs=[assigned[x] if x not in CONSTANTS else CONTROL.get(x,x) for x in op['src']]
        # Sources are latched before a newly assigned result returns; minimum
        # result latency2 includes RF read2. Replay also checks WAW retirement.
        for value in list(active):
            if uses[value]<=pc:
                free.append(active.pop(value));free.sort()
        dst_reg=None
        if op['dst']:
            R.require(bool(free),'RF spills required')
            dst_reg=free.pop(0);assigned[op['dst']]=dst_reg
            active[op['dst']]=dst_reg;peak=max(peak,len(active))
            bindings.append(dict(value=op['dst'],register=dst_reg,definition=pc,last_use=uses[op['dst']]))
        physical.append(dict(op,physical_src=src_regs,physical_dst=dst_reg))
    return physical,dict(bindings=bindings,peak_value_registers=peak,
        control_registers=[28,29,30,31],registers_thread=32,spills=0,
        control_assignment={'r28':'chunk/leaf index','r29':'predicate/loop counter',
            'r30':'address low32','r31':'address high32'},
        operand_word='8lane group g=(warp%4)*4+lane//8;word=(warp//4)*32+register;readcopy0/1, depthbank=word//128;row=word%128. Four lane8 groups per warp32;16 groups per SM.',
        readonly_zero='Ordinary FP32+0 immediate mux, charged normal FADD latency; no first-term bypass.')


def latency(op,p):
    if op['op'] in ('FMUL','FADD'):return p['RF_read_latency']+p['mul_latency' if op['op']=='FMUL' else 'add_latency']
    if op['op']=='DIV':return 21  # norm calendar RF2+IEEE divider LAT19, one active lane
    if op['op']=='SHFL_PAIR':return p['RF_read_latency']+p['shuffle_latency']
    if op['shared']:return p['shared_latency']
    return p['RF_read_latency']+p['integer_latency']


def replay(program,warps,p):
    R.require(0<warps<=32,'resident warp limit')
    code,allocation=lower(address_program(program),p);pc=[0]*warps;ready=[{} for _ in range(warps)]
    physical_ready=[{} for _ in range(warps)];writes=[set() for _ in range(4)]
    cursor=[0]*4;trace=[];cycle=0;retire=0;counts=Counter()
    while any(x<len(code) for x in pc):
        shared=False
        for partition in range(4):
            pool=list(range(partition,warps,4))
            for advance in range(len(pool)):
                index=(cursor[partition]+advance)%len(pool);w=pool[index]
                if pc[w]==len(code):continue
                op=code[pc[w]];finish=cycle+latency(op,p)
                if any(ready[w].get(s,0)>cycle for s in op['src'] if s not in CONSTANTS):continue
                if op['shared'] and shared:continue
                if op['dst'] and (finish in writes[partition] or physical_ready[w].get(op['physical_dst'],-1)>=finish):continue
                R.require(len(op['physical_src'])<=2,'unpriced RF read ports')
                if op['dst']:
                    ready[w][op['dst']]=finish;physical_ready[w][op['physical_dst']]=finish;writes[partition].add(finish)
                counts[op['op']]+=1;shared|=op['shared'];retire=max(retire,finish)
                trace.append(dict(cycle=cycle,retire=finish,warp=w,partition=partition,pc=pc[w],
                    op=op['op'],src=op['physical_src'],dst=op['physical_dst'],shared=op['shared']))
                pc[w]+=1;cursor[partition]=(index+1)%len(pool);break
        cycle+=p['warp_issue_interval']
        R.require(cycle<100000,'schedule did not drain')
    return dict(cycles=max(cycle,retire),instructions=dict(counts),allocation=allocation,
        issue_trace_sha256=hashlib.sha256(json.dumps(trace,sort_keys=True).encode()).hexdigest(),
        RF_write_reservations=[len(x) for x in writes],shared_issue_cycles=sum(x['shared'] for x in trace)),trace


def final_tree(p):
    program=[W.instruction('LDS32','sum',lat=2,shared=True)]
    for level in range(5):
        program.extend([W.instruction('SHFL_PAIR','other',['sum'],offset=1<<level),
            W.instruction('FADD','sum',['sum','other'],9)])
    program.append(W.instruction('STS_PARTIAL',src=['sum'],shared=True))
    first,_=replay(program,4,p)
    last=[W.instruction('LDS32','sum',lat=2,shared=True)]
    for level in range(2):
        last.extend([W.instruction('SHFL_PAIR','other',['sum'],offset=1<<level),W.instruction('FADD','sum',['sum','other'],9)])
    last.append(W.instruction('STS_PARTIAL',src=['sum'],shared=True))
    second,_=replay(last,1,p)
    return dict(first128_partial_tree=first,last4_partial_tree=second,
        barriers=2,barrier_cycles=2*p['barrier_latency'],
        cycles=first['cycles']+second['cycles']+2*p['barrier_latency'],
        padded_leaf_initialization_cycles=4,
        policy='80 accumulated warp partials padded128; fourwarp fivelevel tree then one fourleaf twolevel tree, each adjacent ordered pair. Padding initialization4 shared warp writes charged separately.')


def build(inputs=INPUTS,evidence_commit=None):
    p=R.read(inputs);validate(p);kernel=R.read(R.KERNEL)
    evidence_commit=evidence_commit or subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    waves=[];traces={};tree=final_tree(p)
    for wave,chunks in enumerate((1024,1024,512)):
        projection,pt=replay(W.chunk_program(),chunks//32,p)
        norm,nt=replay(W.chunk_program(True),chunks//32,p)
        traces[f'wave{wave}.projection']=pt;traces[f'wave{wave}.norm']=nt
        waves.append(dict(chunks=chunks,projection=projection,norm=norm,
            wave_barrier_cycles=2*p['barrier_latency'],
            term_major_load_mapping='F32 address=coef_base+(term*chunks+leaf)*4; packedBF16 address=act_base+(term_pair*chunks+leaf)*4; lane consecutive leaf =>32 distinct banks. Word stores preserve BF16 pairs; no widening coefficient.',
            retained_warp_partial_indices=[sum((1024,1024,512)[:wave])//32,sum((1024,1024,512)[:wave+1])//32]))
    dot=sum(w['projection']['cycles']+w['wave_barrier_cycles'] for w in waves)+tree['cycles']+4
    norm=sum(w['norm']['cycles']+w['wave_barrier_cycles'] for w in waves)+tree['cycles']+4
    transposes=[dict(coefficient=R.transpose(c,R.assumptions()),activation=R.transpose(c,R.assumptions(),True)) for c in (1024,1024,512)]
    staging=sum(t['coefficient']['additional_cycles']+t['activation']['additional_cycles'] for t in transposes)
    # Ordinary proposed32SM reduction barrier: five ordered gather/release rounds,
    # Charge32 sixteen-byte packets in each direction per round on the one
    # shared NoC port; no32-way free simultaneous fanout/acknowledgment.
    fabric_to_serial=lambda cycles:math.ceil(cycles*p['serial_hz']/p['fabric_hz'])
    barrier=fabric_to_serial(p['grid_barrier_rounds']*(2*p['network_startup_cycles']+math.ceil(32*2*16/p['NoC_bytes_cycle'])))+p['barrier_latency']
    collector=fabric_to_serial(math.ceil(25*16/p['NoC_bytes_cycle'])+p['network_startup_cycles'])+p['CDC_cycles']
    scalar=sum(kernel['hc']['scalar_dependency_cycles_candidate'].values())
    compute=max(dot,norm)+barrier+collector+scalar
    # No concurrent matrix traffic: isolate HC. Four controllers each accepts
    # at most one4sector128B line/cycle, as Euler's current finite tag contract.
    operand_bytes=1966080+25*40960+108
    lines=math.ceil(operand_bytes/128)
    read_cycles=math.ceil(lines/4)+math.ceil(p['loaded_HBM_ns']*1e-9*p['fabric_hz'])
    read_cycles+=p['landing_after_last_sector_cycles']
    operand_cycles=p['bounded_credit_wait_cycles']+math.ceil(read_cycles*p['serial_hz']/p['fabric_hz'])+p['CDC_cycles']
    result_cycles=fabric_to_serial(math.ceil((32*112+32*16)/p['NoC_bytes_cycle'])+p['network_startup_cycles'])+p['CDC_cycles']+p['barrier_latency']
    phases={}
    for i,wave in enumerate(waves):
        size=wave['chunks']*8*(24*4+25*2)
        cycles=math.ceil(math.ceil(size/128)/4)+math.ceil(p['loaded_HBM_ns']*1e-9*p['fabric_hz'])+p['landing_after_last_sector_cycles']
        phases[f'hc_wave{i}_read_credit_wait']=p['bounded_credit_wait_cycles']+math.ceil(cycles*p['serial_hz']/p['fabric_hz'])+p['CDC_cycles']
        # Byte copies to25 endpoints, ordinary finite NoC, no multicast credit.
        phases[f'hc_wave{i}_transpose_noc_credit_wait']=p['bounded_credit_wait_cycles']+fabric_to_serial(p['network_startup_cycles'])+p['CDC_cycles']
        tile_count=wave['chunks']//32
        wire_bytes_tile=math.ceil((24*1024+25*512)/128)*(128+p['NoC_frame_header_bytes'])
        noc_cycles=tile_count*fabric_to_serial(math.ceil(wire_bytes_tile/p['NoC_bytes_cycle']))
        buffer_fences=tile_count*p['barrier_latency']
        phases[f'hc_wave{i}_shared_fill']=transposes[i]['coefficient']['additional_cycles']+transposes[i]['activation']['additional_cycles']+kernel['hc']['waves'][i]['shared_refill_cycles']+noc_cycles+buffer_fences
        wave['tile_service']=dict(tile_count=tile_count,wire_bytes_tile=wire_bytes_tile,NoC_fabric_hz=p['fabric_hz'],
            NoC_transfer_serial_cycles=noc_cycles,buffer_reuse_fence_cycles=buffer_fences,
            coefficient_raw_buffer_live_bytes_SM=1024,activation_raw_buffer_live_bytes_SM=512,
            landing_lines_per_controller=math.ceil(math.ceil(size/128)/4),
            chronological_steps=['reserve endpoint and landing credits','deliver one32chunk tile, framed128Blines serialized on NoC','ordinary shared/INT8waycoef4waypackedactivation transpose','term-major shared tile write','buffer reuse fence before next32chunk tile'],
            accounting='Credit setup in preceding NoC phase; payloadtransfer plus transpose/fill service here. Shared fill includes conservatively retained additional r3 refill copy; no overlap or full-wave raw staging fit.')
        phases[f'hc_wave{i}_projection_norm_kernel']=max(wave['projection']['cycles'],wave['norm']['cycles'])
        phases[f'hc_wave{i}_partial_retire_barrier']=wave['wave_barrier_cycles']
    norm_scalar_program=[dict(op,src=['@F20480' if v=='@F5120' else v for v in op['src']]) for op in N.scalar_norm_program()]
    norm_scalar_calendar,norm_scalar_trace=replay(norm_scalar_program,1,p)
    traces['norm_scalar']=norm_scalar_trace
    phases.update(hc_final_chunk_tree_kernel=tree['cycles']+4,
        hc_norm_scalar_kernel=norm_scalar_calendar['cycles'],
        hc_row_norm_collect_credit_wait=p['bounded_credit_wait_cycles']+collector,
        hc_collect_barrier=barrier,
        hc_scalar_finish_kernel=sum(v for key,v in kernel['hc']['scalar_dependency_cycles_candidate'].items() if key!='norm'),
        hc_scalar_publish=result_cycles,hc_retire_barrier=barrier)
    # Read the graph owner's pending22phase package by immutable commit, without
    # changing parent or replacing the historical5phase graph/helper sources.
    graph_blob=subprocess.check_output(['git','show',GRAPH_COMMIT+':tools/w19_composed_schedule.py'],cwd=ROOT)
    expanded=types.ModuleType('w16_expanded_graph_input');expanded.__file__=str(ROOT/'tools/w19_composed_schedule.py')
    exec(compile(graph_blob,expanded.__file__,'exec'),expanded.__dict__)
    programme=R.read(PROGRAM)
    revisions={expanded.PROGRAM:expanded.PIN,expanded.ISA:expanded.PIN,expanded.SM:expanded.PIN,expanded.KERNEL:expanded.KERNEL_COMMIT}
    graph_pins={}
    for path,revision in revisions.items():
        blob=subprocess.check_output(['git','show',revision+':'+path],cwd=ROOT)
        graph_pins[path]=dict(commit=revision,sha256=hashlib.sha256(blob).hexdigest())
        if path==PROGRAM:R.require(json.loads(blob)==programme,'source programme differs from expanded owner graph')
    g=expanded.graph(programme,graph_pins)
    bindings={}
    for node in g['nodes']:
        op=g['operations'][node['source_operation_index']]
        if op.get('fn')=='hc_mixes':
            R.require(node['phase'] in phases,'unpriced HC phase '+node['phase'])
            units=25 if node['phase'].endswith(('shared_fill','projection_norm_kernel')) or node['phase']=='hc_final_chunk_tree_kernel' else 1
            bindings[node['id']]=dict(cycles=phases[node['phase']],clock_hz=p['serial_hz'],resource_units=units,
                logical_SM_owners=list(range(25)) if units==25 else [24] if node['phase']=='hc_norm_scalar_kernel' else list(range(32)) if node['resource']=='barrier' else [0],
                finite_waits_included=True,exact_gpu_lowering_bound=True,
                target_GPU_exactness=False,analytical_candidate=True,physical_qualified=False,phase=node['phase'],
                evidence=dict(commit=evidence_commit,path='tools/w16_gpu_hc_dot_schedule.py',sha256=R.sha('tools/w16_gpu_hc_dot_schedule.py')),
                scope='Bounded positive analytical calendar only; exact_gpu_lowering_bound is model correspondence, not RTL numerical qualification.')
    R.require(len(bindings)==1760 and len(phases)==22,'HC22 phase binding drift')
    nonlinear=subprocess.check_output(['git','show',NONLINEAR_COMMIT+':'+NONLINEAR_PATH],cwd=ROOT)
    nonlinear_proof_blob=subprocess.check_output(['git','show',NONLINEAR_COMMIT+':results/quality/w19_hc_nonlinear_proof_20261001/proof.json'],cwd=ROOT)
    nonlinear_proof=json.loads(nonlinear_proof_blob)
    R.require(nonlinear_proof['verdict']=='PASS','nonlinear proof not PASS')
    for path,pin in nonlinear_proof['source_pins'].items():
        blob=subprocess.check_output(['git','show',NONLINEAR_COMMIT+':'+path],cwd=ROOT)
        R.require(hashlib.sha256(blob).hexdigest()==pin,'nonlinear package drift '+path)
    counts=nonlinear_proof['fixtures'][0]['boundary_F32_element_counts']
    R.require(all(f['boundary_F32_element_counts']==counts for f in nonlinear_proof['fixtures']),'nonlinear primitive work differs')
    R.require(counts['div']==649,'IEEE F32 divisions drift')
    bank_blob=subprocess.check_output(['git','show',BANK_COMMIT+':'+BANK_PATH],cwd=ROOT)
    bank=types.ModuleType('w16_Euler_bank_input');bank.__file__=str(ROOT/BANK_PATH)
    exec(compile(bank_blob,bank.__file__,'exec'),bank.__dict__)
    bank_layout=bank.layout()
    R.require(p['landing_after_last_sector_cycles']==3 and b'after_final_sector_write_to_delivery_cycles=3' in bank_blob,'Euler bank pipeline drift')
    tc16_blob=subprocess.check_output(['git','show',TC16_COMMIT+':'+TC16_PATH],cwd=ROOT)
    paths=[inputs,R.KERNEL,R.TRANSPORT,R.PROOF,R.MACRO,'tools/w19_gpu_simd_contract.py',
        'tools/w19_gpu_norm_calendar.py','results/rtl/w19_checkpoint_production_20261001/gpu-norm-calendar-r1.json',PROGRAM,'tools/uarch_model.py',
        'tools/w16_gpu_hc_simt_contract.py','tools/w16_gpu_hc_dot_schedule.py','tests/test_w16_gpu_hc_dot_schedule.py']
    return dict(schema='opentallas.w16.bounded_HC_cost_provider.v1',inputs=inputs,cost_evidence_commit=evidence_commit,assumptions=p,
        bounded_dot_model_sized=True,SMs=32,FP32_lanes_SM=128,shared_bytes_SM=65536,
        waves=waves,final_tree=tree,dot_cycles=dot,norm_cycles=norm,transpose_waves=transposes,
        phases_cycles=phases,node_costs=bindings,graph_sha256=g['graph_sha256'],scope='GPU_SIMT_FULL_TOKEN_MODEL',
        HC80_conditional_time_us=80*sum(phases.values())/900,
        resource_capacities={'hbm':4,'staging':32,'simt':32,'barrier':32,'noc':1},
        expanded_graph_source_pins=graph_pins,expanded_graph_input=dict(commit=GRAPH_COMMIT,path='tools/w19_composed_schedule.py',sha256=hashlib.sha256(graph_blob).hexdigest()),
        preserved_transpose_cycles=staging,
        scalar_RF=dict(registers_thread=32,control=[28,29,30,31],
            allocation={'dot_or_comb_current':0,'norm':1,'scale':2,'base':3,'mix':4,'polynomial_Newton_temporaries':list(range(5,15)),'denominator':15,'shuffle_partner':16,'pre_post_output':17,'conversion_integer64_pair':[18,19],'predicate':20},
            spill_bytes=0,scalar_owner='SM0 one warp; active masks4 pre/4 post/16 comb; IEEE divider lane requests serializeII1LAT19',
            liveness='Phase reuse after25producer barrier. r0 retains each lanecomb between39 normalization passes; denominator/partner replaced only after division retires. Exp and Newton scratch lifetimes do not overlap; pre/post outputs retained r17 in inactive lanes until publish.',
            qualified_compiler_allocation=False),
        input_scope='Single HC sequential phases,32SM inside phase concurrent;96 ranks concurrent slowest equal owner bound. No credit for hypothetical controller/matrix overlap.',
        nonlinear_input=dict(commit=NONLINEAR_COMMIT,path=NONLINEAR_PATH,
            sha256=hashlib.sha256(nonlinear).hexdigest(),scalar_dependency_cycles=kernel['hc']['scalar_dependency_cycles_candidate'],
            precision='F32 IEEE division; no reciprocalmultiply, FMA or nativeapproximateSFU. GOLDEN canonical+0 onlyafter roundedADD/MUL/DIV; XORneg preservesnegativezero.',
            proof_commit=NONLINEAR_COMMIT,proof_sha256=hashlib.sha256(nonlinear_proof_blob).hexdigest(),
            proof_fixtures=len(nonlinear_proof['fixtures']),primitive_F32_element_counts=counts,proof_boundaries=sum(f['boundary_count'] for f in nonlinear_proof['fixtures']),
            proof_role='Leibniz CPU recipe source bound; no new campaign or target latency proof. Existing candidate exact scalar recipes and649 divisions charged, wrappers pending.'),
        norm_calendar_input=dict(path='results/rtl/w19_checkpoint_production_20261001/gpu-norm-calendar-r1.json',
            norm_scalar_schedule=norm_scalar_calendar,source_denominator=5120,HC_mix_denominator=20480,
            scope='Reuse scalar opcode recipe and resource inputs only; mean constant explicitly20480 forHCmix. No adoption of5120 pre/post norm graph here.'),
        Euler_input=dict(transport=R.TRANSPORT,commit=BANK_COMMIT,path=BANK_PATH,
            sha256=hashlib.sha256(bank_blob).hexdigest(),bank_layout=bank_layout,
            storage_bytes_rank=bank_layout['bytes_per_rank'],context_allocation_lines_cycle_controller=1,
            actual_current_line_request_bytes_second_controller=128*1200000000,
            proposed_fullstack_TBps_credit=False,bank_after_final_sector_assumption_cycles=p['landing_after_last_sector_cycles'],
            request='Confirm proposed banked delivery3cycles after last sector and fourcontroller one128Bline/clock isolated HC service; bind reservation bounds. No full-stack1TB/s credit; shared transpose explicit8/4-way.'),
        TC16_consequence=dict(commit=TC16_COMMIT,path=TC16_PATH,sha256=hashlib.sha256(tc16_blob).hexdigest(),
            setup_slack_ps=-31.06,hold_slack_ps=5.22,period_ps=833,
            status='REJECT_SS_FAIL; downstream SM refused',
            connected_matrix_clock_qualified=False,connected_token_price=None,
            action='Preserve failed vehicle, no clock relaxation/tuning/restart; HC analytical calendar cannot confer comparator physical eligibility.'),
        build_boundary='HC dot finite instruction/RF/shared/tree/barrier analytical candidate supplied. Any implementation still requires parent model/floorplan preflight; SS60ps/FF25ps and numerical target gate. Non-HC token nodes untouched.',
        exact_gpu_lowering_bound=False,physical_qualified=False,ready_to_build=False,hardware_adopted=False,headline_rate=None,
        model_generator_changed=False,pins={path:R.sha(path) for path in paths}),traces


def check(record):
    source_blob=subprocess.check_output(['git','show',record['cost_evidence_commit']+':tools/w16_gpu_hc_dot_schedule.py'],cwd=ROOT)
    R.require(hashlib.sha256(source_blob).hexdigest()==record['pins']['tools/w16_gpu_hc_dot_schedule.py'],'cost evidence commit drift')
    for path,pin in record['pins'].items():R.require(R.sha(path)==pin,'pin drift '+path)
    fresh,_=build(record['inputs'],record['cost_evidence_commit']);R.require(fresh==record,'cost replay drift')


def main():
    ap=argparse.ArgumentParser(description=__doc__);mode=ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('--out',type=Path);mode.add_argument('--check',type=Path);ap.add_argument('--inputs',default=INPUTS)
    a=ap.parse_args()
    if a.check:check(json.loads(a.check.read_text()))
    else:
        r,traces=build(a.inputs)
        with a.out.open('x') as f:json.dump(r,f,indent=2,sort_keys=True);f.write('\n')
        with a.out.with_suffix('.trace.json').open('x') as f:json.dump(traces,f,separators=(',',':'));f.write('\n')
    print('PASS: finite analytical HC dot/cost phases; physical/target qualification pending')


if __name__=='__main__':main()
