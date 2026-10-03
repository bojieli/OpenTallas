#!/usr/bin/env python3
"""Finite V1 analytical model composed with pinned H1, C0 and Dewey sources.

No engine RTL, P&R, source arithmetic rewrite or live-job source edits.
Full-program command counts retain source units; DS scalar dispatch is a
conservative upper, never silently divided by128 as an achieved speedup.
"""
import argparse
import collections
import gzip
import hashlib
import json
import math
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
H1='992c14a70f812028f9de5e46eb79d5688db9482b'
AUDIT='e844837ed6dcaa669761e7e394c5b93b61255e75'
C0='655f22b2b'
DEWEY='0601e4ac7fca0ada63252733d303cb601b24b507'
NATIVE='fd7220c1e55397dec90222e1f99a8bd95ae02e03'
AP='results/uarch/h4_native_rtl_binding_audit_20261002/'
QP='results/uarch/h3_qwen_complete_native_20261002/bounded_r2/Qwen_tiled.json.gz'
DP='results/uarch/h3_deepseek_complete_native_20261002/program_final.json.gz'
CP='results/uarch/h4_c0_bridge_model_20261002/dispatch_lowering.json.gz'
DW='results/uarch/h3_complete_native_calendar_20261002/ds_strict_shared_refs_r2/run/full_program_costs.json.gz'
V1={'AND','OR','XOR','IADD','ISUB','IMUL','IMOD','SHL','SHR','IOTA','I2F','F2I',
    'LDEXP','FCMP_EQ','FCMP_NE','FCMP_GT','FCMP_LT','SELECT','FMAX','FMIN','FP8_PACK','FP8_UNPACK'}
ALIASES={'IADD64':'IADD','SHL64':'SHL','CMP_EQ':'FCMP_EQ','CMP_NE':'FCMP_NE',
         'CMP_GT':'FCMP_GT','CMP_LT':'FCMP_LT','ITOF':'I2F','FTOI':'F2I'}
# Explicit proposed serial edge costs. These are not measured H1 timing.
DEFAULT={'accept':1,'RF_read_accept':1,'RF_response_capture':1,'RF_response_return':1,
         'RF_write_accept':1,'mirror_ACK':1,'complete':1,'reverse_retire':1,
         'lane_step':1,'bit_latency':1,'add_latency':2,'multiply_latency':8,
         'modulo_latency':64,'convert_latency':7,'compare_latency':3,
         'FP8_latency':16}


def pinned(commit,path):
    return subprocess.check_output(['git','show',commit+':'+path],cwd=ROOT)


def load(commit,path):
    data=pinned(commit,path)
    return json.loads(gzip.decompress(data) if path.endswith('.gz') else data)


def positive(values):
    if set(values)!=set(DEFAULT) or any(not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0 for v in values.values()):
        raise ValueError('complete positive provisional cost parameters required')


def contract(op):
    op=ALIASES.get(op,op)
    if op not in V1:raise ValueError('unsupported V1 opcode '+op)
    if op=='IOTA':return {'arity':0,'outputs':['I64'],'semantics':'source ordered I64 indices; continuation base supplied, no restart per tile'}
    if op=='SELECT':return {'arity':3,'outputs':['F32','U32','I64'],'semantics':'predicate !=0; branch bittypes and explicit dtype preserved; third RF operand serialized'}
    if op.startswith('FCMP_'):return {'arity':2,'outputs':['U32'],'semantics':'existing native comparison; F32 NaN unordered except NE; I64 indices remain integer, never converted to F32'}
    if op in ('FMAX','FMIN'):return {'arity':2,'outputs':['F32'],'semantics':'existing numpy/source maximum/minimum operand order, NaN propagation and signed-zero ties; no algebraic substitution'}
    if op=='I2F':return {'arity':1,'outputs':['F32'],'semantics':'source signed I8/I64 or U32 to F32 rounding exactly once, RNE including integer ties'}
    if op=='F2I':return {'arity':1,'outputs':['I64'],'semantics':'truncate toward zero; reject nonfinite and abs(value)>=2^63'}
    if op=='LDEXP':return {'arity':2,'outputs':['F32'],'semantics':'source exponent cast/view I32, source F32 ldexp and fault on nonfinite result'}
    if op=='FP8_PACK':return {'arity':1,'outputs':['U8'],'semantics':'existing source pack8 rounding/saturation/zero; nonfinite source rejected'}
    if op=='FP8_UNPACK':return {'arity':1,'outputs':['F32'],'semantics':'source finite127-entry lookup, reject code&127==127, canonical source +0'}
    return {'arity':2,'outputs':['U32','I64'],'semantics':'source dtype/wrap; signed arithmetic SHR on I64, logical SHR U32; reject shift outside word width and modulo zero; NumPy/source signed remainder'}


def latency_key(op):
    if op=='IMOD':return 'modulo_latency'
    if op=='IMUL':return 'multiply_latency'
    if op in ('IADD','ISUB','IOTA'):return 'add_latency'
    if op in ('I2F','F2I','LDEXP'):return 'convert_latency'
    if op.startswith('FCMP_') or op in ('FMAX','FMIN'):return 'compare_latency'
    if op.startswith('FP8_'):return 'FP8_latency'
    return 'bit_latency'


def command_cost(op,input_bits,output_bits,elements=128,*,lanes=32,costs=None):
    """Exact RF phase accounting for a supplied typed bounded command.

    Costs and lane pipeline are provisional; physical RF words are always32bit.
    Predicate uses source U32 slots, not an invented third port or free mask.
    """
    op=ALIASES.get(op,op);c=contract(op);costs=dict(DEFAULT if costs is None else costs);positive(costs)
    if len(input_bits)!=c['arity'] or any(b not in (8,32,64) for b in list(input_bits)+[output_bits]):
        raise ValueError('explicit supported source/result bittypes required')
    if not isinstance(elements,int) or not 0<elements<=128 or lanes not in (32,64,128):raise ValueError('finite lane/tile shape')
    if op in ('F2I','IOTA') and output_bits!=64:raise ValueError('I64 result contract')
    if op.startswith('FCMP_') and output_bits!=32:raise ValueError('U32 predicate result contract')
    if op=='SELECT' and input_bits[0]!=32:raise ValueError('source U32 predicate slot')
    reads=sum(math.ceil(elements*max(32,b)/4096) for b in input_bits)
    writes=math.ceil(elements*max(32,output_bits)/4096)
    pairs=math.ceil(reads/2);steps=math.ceil(elements/lanes)
    # Iterative modulo and FP8 service keep their per-lane state until complete.
    # No implied fully-pipelined64stage modulo or hidden one-cycle new group.
    lane_II=costs[latency_key(op)] if op in ('IMOD','FP8_PACK','FP8_UNPACK') else costs['lane_step']
    components={'accept':costs['accept'],
      'RF_read':pairs*(costs['RF_read_accept']+costs['RF_response_capture']+costs['RF_response_return']),
      'native_only':costs[latency_key(op)]+(steps-1)*lane_II,
      'RF_write_visible':writes*(costs['RF_write_accept']+costs['mirror_ACK']),
      'complete':costs['complete'],'reverse_retire':costs['reverse_retire']}
    return dict(opcode=op,input_bits=list(input_bits),output_bits=output_bits,elements=elements,lanes=lanes,
      folded_lane_groups=steps,lane_group_II_provisional=lane_II,RF_read_vectors=reads,RF_read_pair_transactions=pairs,RF_response_bus_bytes=pairs*1024,
      RF_write_vectors=writes,RF_write_physical_mirror_bytes=writes*1024,
      third_operand_extra_read_pairs=max(0,pairs-1) if op=='SELECT' else 0,
      ordered_phases=['accepted']+['read_pair/capture/return']*pairs+['native_exact_leaf']+
                     ['write_vector/both_mirror_ACK']*writes+['complete','reverse_grant','retire'],
      owner_credit=1,owner_held_through='all mirrored ACK + consumer acceptance + reverse retirement',
      components=components,serialized_service_ticks=sum(components.values()),
      native_only_replacement_ticks=components['native_only'],measured_cost=None,
      RMW_codec_cost_recharged=False,provisional=True)


def variants(op,lanes):
    arity=contract(op)['arity'];out=64 if op in ('IOTA','F2I') else 8 if op=='FP8_PACK' else 32
    lo=[32]*arity;hi=[64]*arity
    if op=='SELECT':hi[0]=32
    if op in ('FMAX','FMIN','F2I','FP8_PACK'):hi=[32]*arity
    if op=='FP8_UNPACK':lo=hi=[8]
    if op=='LDEXP':hi=[32,64]
    high_out=64 if 64 in hi and not (op.startswith('FCMP_') or op in ('I2F','LDEXP')) else out
    return command_cost(op,lo,out,lanes=lanes),command_cost(op,hi,high_out,lanes=lanes)


def critical(rows):
    finish={};serial=0
    for row in rows:
        if any(d not in finish for d in row['dependencies']):raise ValueError('unresolved PC dependency')
        finish[row['pc']]=max((finish[d] for d in row['dependencies']),default=0)+row['V1_ticks_upper']
        serial+=row['V1_ticks_upper']
    return {'dependency_path_ticks_upper':max(finish.values(),default=0),'serialized_single_worker_ticks_upper':serial,
            'scope':'V1 isolated contribution only; absent M1/S1/R1/T1/provider/collective costs remain unknown, never zero full-token latency',
            'hardware_token_rate':None}


def build(lanes=32):
    caps=load(AUDIT,AP+'primitive_capabilities.json')
    if {x['opcode'] for x in caps if x['implementation_requirement']=='V1'}!=V1:raise ValueError('audit V1 opcode gate')
    h1=load(AUDIT,AP+'hardware_inventory.json')['bindings'];rf=h1['RF']['config']
    if (rf['read_ports'],rf['write_ports'],rf['mirrors'],rf['vector_bits'])!=(2,1,2,4096):raise ValueError('H1 RF ABI gate')
    c0=load(C0,CP);q=load(NATIVE,QP);d=load(NATIVE,DP);dw=load(DEWEY,DW)
    if len(dw['PC_intervals'])!=len(d['instructions']) or any(
        a['pc']!=b['pc'] or a['family']!=b['family'] or a['dependencies']!=b['dependencies']
        for a,b in zip(dw['PC_intervals'],d['instructions'])):raise ValueError('Dewey/native DS PC dependency join')
    families=load(AUDIT,AP+'family_bindings.json.gz'); profiles={op:variants(op,lanes) for op in sorted(V1)}
    models={}
    for name,ops in [('Qwen',q['operations']),('DeepSeek',dw['PC_intervals'])]:
        rows=[];totals=collections.Counter();byfamily=collections.defaultdict(collections.Counter)
        for op in ops:
            rank_counts=([op['calendar_export']['physical_primitives']['native_primitive_commands']] if name=='Qwen'
                         else [r['native_scalar_command_upper_by_opcode']for r in op['ranks']])
            upper=0;lower=0;counts=collections.Counter()
            for counts_rank in rank_counts:
                selected={k:int(v) for k,v in counts_rank.items()if k in V1}
                counts.update(selected)
                hi=sum(v*profiles[k][1]['serialized_service_ticks']for k,v in selected.items())
                # No claimed SIMD speedup: lower is an ideal packed occupancy floor.
                lo=sum((math.ceil(v/128) if name=='DeepSeek' else v)*profiles[k][0]['serialized_service_ticks']for k,v in selected.items())
                upper=max(upper,hi);lower=max(lower,lo)
            family=op.get('opcode',op.get('family'));totals.update(counts);byfamily[family].update(counts)
            rows.append(dict(pc=op['pc'],family=family,dependencies=op['dependencies'],source_count=dict(counts),
                 V1_ticks_lower_ideal_occupancy=lower,V1_ticks_upper=upper,
                 count_scope='native128lane source command export' if name=='Qwen' else 'Dewey conservative scalar command upper per rank; max rank duration, no achieved32SM overlap',
                 typed_cost_scope='bounded32/64-bit variants; dynamic exact widths must arrive in C0 command',
                 native_only_ticks_upper=max((sum(v*profiles[k][1]['native_only_replacement_ticks']for k,v in rc.items()if k in V1)for rc in rank_counts),default=0)))
        expected=1737 if name=='Qwen' else 2213
        if len(rows)!=expected or len({r['family']for r in rows})!=(21 if name=='Qwen' else 30):raise ValueError('full PC/family gate')
        ranks=2 if name=='Qwen' else 96
        models[name]=dict(PCs=expected,families=len(byfamily),ranks=ranks,SMs_per_rank=32,replicas=ranks*32,
          replica_scope='fully spatial upper of source rank x32 finite services; mapping logical ranks to installed physical SMs remains an admission gate',
          opcode_count=dict(totals),family_counts={k:dict(v)for k,v in byfamily.items()},PC_costs=rows,
          critical_path=critical(rows),static_V1_source_steps=sum(x['primitive_counts'].get(k,0)for x in families if x['model']==name for k in V1))
    # Proposed one32lane slice with64bit integer ALU; folded over a128lane RF vector.
    # Gate equivalents are deliberately bounded analytical assumptions, not synthesis.
    per_lane_gates=(64*64*6+64*12+64*6*2+64*12+64*24+32*24+64*12)
    captures_bits=5*4096+2*4096+256+128+64 #C0 keeps its existing512bit command latch
    lane_pipeline_bits=lanes*8*(3*64+2) #8stage proposed multiply/convert, data+valid/fault
    iterative_state_bits=lanes*(3*64+8) #modulo/FP8 source service state
    state_bits=captures_bits+lane_pipeline_bits+iterative_state_bits
    FP8_table_bits=127*32*lanes #one exact constant decoder lookup per active lane
    FP8_table_mux_bit_equivalents=126*32*lanes
    mux_bits=(5+2)*32*32*(128//lanes-1)+lanes*64*8 #input mux+output capture demux+opcode mux
    gate_area_range=[.1,.3];dff=.2916;util=.5
    logic_range=[state_bits*dff+(lanes*per_lane_gates+mux_bits+FP8_table_mux_bit_equivalents)*a for a in gate_area_range]
    local_tracks=lanes*64*3+128+64+512;capacity=math.floor(64*4/.08)
    sources=[(H1,'rtl/gpu/ot_gpu_rf_service.sv'),(H1,'rtl/gpu/ot_gpu_full_sm_service.sv'),
      (AUDIT,AP+'primitive_capabilities.json'),(AUDIT,AP+'hardware_inventory.json'),(AUDIT,AP+'family_bindings.json.gz'),
      (C0,CP),(NATIVE,QP),(NATIVE,DP),(DEWEY,DW),(NATIVE,'tools/h3_qwen_bounded_native.py'),
      (C0,'tools/h4_c0_model.py'),(C0,'tools/uarch_model.py'),(DEWEY,'tools/h3_complete_native_calendar.py')]
    pins=[dict(commit=c,path=p,sha256=hashlib.sha256(pinned(c,p)).hexdigest())for c,p in sources]
    footprint=[a/util/1e6 for a in logic_range]
    for model in models.values():model['incremental_footprint_mm2_range']=[a*model['replicas']for a in footprint]
    return dict(schema='opentallas.H4.V1.G0.v1',status='MODEL_COMPLETE_G0_ADMISSION_BLOCKED',before_RTL=True,
      source_pins=pins,coverage=dict(V1_opcodes=22,Qwen_PCs=1737,DS_PCs=2213,C0_static_dispatch_coverage=c0['coverage']),
      opcode_contracts={op:contract(op)for op in sorted(V1)},typed_cost_bounds={op:{'lower':a,'upper':b}for op,(a,b)in profiles.items()},
      provisional_costs=DEFAULT,models=models,
      resource_contract=dict(lanes=lanes,native_tile_elements_max=128,physical_word_bits=32,logical_I64_words=2,
        RF_2R1W=rf,temporary_RF_vectors=32,command_credit=1,RF_credit=1,tag_credit=1,
        scalar_or_literal='C0 owns source bittyped immediate/broadcast; not a free third RF port',
        state_bits=state_bits,lane_pipeline_bits=lane_pipeline_bits,iterative_state_bits=iterative_state_bits,
        FP8_table_bits=FP8_table_bits,FP8_table_replicas=lanes,FP8_table_read_ports_each=1,FP8_code127_rejected=True,operand_capture_vectors=5,result_capture_vectors=2,command_bits=512,command_latch_owner='existing C0 window; no second512bit command latch charged',
        tag='64bit generation + source owner identity retained outside H1 8bit fence; no reuse until all ACK/returns/reverse grants',
        RF_source_home_scope='existing per-version rank/SM RF/spill bindings; local V1 capture not a replacement source arena',
        atomicity='C0 must exclude unrelated H1 host/matrix requests between serialized reads and final mirror ACK; current H1 host ports do not implement V1 owner lock',
        third_operand='SELECT condition+both branches captured with serialized pairs;64bit branches require3 read pairs',
        compute_MACs_per_cycle=0,compute_integer_elements_per_lane_step=lanes,
        RF_read_bus_B_per_accept=1024,RF_mirrored_write_B_per_accept=1024,
        source_derived_no_stall_RF_read_edges=3,source_derived_no_stall_RF_write_ACK_edges=2,
        edge_basis='read_go T0, registered response T1, consume T2, next accept T3; write_go T0 mirrors same edge, ACK consumed T1, next accept T2; host gateway stalls separately owned',
        capture_boundary_bits_per_cycle=8192,write_boundary_bits_per_cycle=8192,
        communication_scope='port payload ceiling only; sustainedBpc bounded by serial accept/return/ACK costs',
        additional_HBM_bytes=0),
      area=dict(FP8_table_constant_mux_bit_equivalents=FP8_table_mux_bit_equivalents,FP8_table_scope='Exact127entry source decoder, per-lane local constants; included gate area bound, not free table or shared unlimited read port',lane_gate_equivalents_upper=per_lane_gates,lane_replica_count=lanes,mux_demux_bit_equivalents=mux_bits,
        state_DFF_area_um2_per_bit=dff,assumed_gate_area_um2_range=gate_area_range,placement_utilization=util,
        logic_um2_range=logic_range,incremental_footprint_mm2_per_SM_range=footprint,
        existing_RF_and_C0_area_recharged=False,slot_capacity_mm2=None,slot_fit='UNKNOWN; full SMslot reservation required'),
      routing=dict(local_tracks_upper=local_tracks,channel_capacity_tracks_assumed=capacity,
        basis='64um channel,4existing signal layers,0.08um pitch; no new layers',
        channels_required=math.ceil(local_tracks/capacity),single_channel_fits=local_tracks<=capacity,
        H1_existing_RF_payload_tracks=8192+8192,RF_page_read_mux_4to1_bit_equivalents=2*4096*3,
        RF_existing_bank_mirror_replicas=4*16*2,shared_hub_channels_required=math.ceil((local_tracks+16384)/capacity),
        control_broadcast_fanout=32,rank_replicas=dict(Qwen=2,DeepSeek=96),hub_routing_layer_check='PENDING_PHYSICAL_CAPACITY_JOIN'),
      unified_model_join=dict(source_commit=C0,source_path='tools/uarch_model.py',read_only=True,
        additive_entrypoint='h4_v1_g0_model.additive_summary(model)',
        calibration_entrypoint='h4_v1_g0_model.reconcile_cost(command,explicit_existing_RF_ledger)',
        composition='Dewey compose_h4_uarch/reprice_h4_native_stages owns full-token composition; V1 exports separate delta/native service demand, never mutates live unified source'),
      cost_interface=dict(owner='Dewey',control_owner='Sagan',keys=['model','family','source_PC','program_sha256','template_id','ordered_step_index','source_bittypes','destination_bittype'],
        required_command_fields=['owner_tag','generation','rank','SM','source_version_home_refs','destination_version_home_ref','predicate','active_lanes','source_attrs_rounding'],
        replace='native:OP positive provisional32 tick entry with native_only_replacement_ticks after finite lane grouping is admitted',
        RF='RF read/write/third operand phases are exported separately; reconcile against existing charged provider/highword/RMW intervals, never blindly add whole serialized_service_ticks',
        C0='C0 fetch/decode/scoreboard/accept/complete/reverse remain owned by C0, never recharged in V1 native-only cost',
        M1='BITCAST_U/F, scalar/broadcast/view transport remain M1; V1 preserves their bittypes but does not double-charge movement',
        clock='software ticks only; streaming1.2GHz and serial0.9GHz CDC/direction and measured costs must be bound by owner before ns/token claim'),
      admission_gates=['Dewey cost component replacement and dynamic typed command count join',
        'Sagan C0 source homes/thirdoperand/atomic owner gate','V1 opcode endpoint absent in H1; exact connected source gate required after own G0 admission',
        'incremental SMslot fit, physical rank/SM mapping and routed channel allocation','source exact conversion/FP8/predicate exceptional gates','context SS setup/FF hold'],
      exact_semantic_provider='tools/h3_qwen_bounded_native.py:NativePrimitiveVM.primitive at pinned native commit; attrs U32/I64 and F32 bitcasts/rounds unchanged',
      actual_H1_binding=dict(opt_in=False,available_endpoint='host RF pair-read/full-vector mirrored-write only; SIMD FADD/FMUL',V1_opcode_endpoint=False,gate='No actual V1 binding/RTL until model admission closes routing, slot and C0 atomic owner gates'),
      engine_RTL_written=False,hardware_admitted=False,physical_or_timing_credit=False)


def additive_summary(model):
    return {'schema':'opentallas.H4.V1.uarch-additive.v1','status':model['status'],
            'source_pins':model['source_pins'],'model_contributions':{
            name:{'critical_path':item['critical_path'],'replicas':item['replicas'],
                  'incremental_footprint_mm2_range':item['incremental_footprint_mm2_range']}
            for name,item in model['models'].items()},
            'resource_contract':model['resource_contract'],'routing':model['routing'],
            'cost_interface':model['cost_interface'],'hardware_admitted':False}


def reconcile_cost(command, ledger):
    """Exact physical count delta; no second charge for provider highword/RMW."""
    required={'RF_read_pair_transactions','RF_write_vectors','native_ticks_per_command',
              'I64_RMW_already_charged','C0_already_charged'}
    if set(ledger)!=required or not ledger['C0_already_charged']:raise ValueError('complete existing cost ledger required')
    for key in ('RF_read_pair_transactions','RF_write_vectors'):
        if type(ledger[key])is not int or ledger[key]<0:raise ValueError('invalid charged RF count')
        if ledger[key]>command[key]:raise ValueError('RF ledger scope mismatch; cannot subtract unrelated costs')
    base=ledger['native_ticks_per_command']
    if not isinstance(base,(int,float)) or not math.isfinite(base) or base<=0:raise ValueError('explicit positive native baseline')
    reads=command['RF_read_pair_transactions']-ledger['RF_read_pair_transactions']
    writes=command['RF_write_vectors']-ledger['RF_write_vectors']
    return {'native_only_replacement_ticks':command['native_only_replacement_ticks'],
            'native_baseline_replaced_ticks':base,'native_only_delta_ticks':command['native_only_replacement_ticks']-base,
            'additional_RF_read_pairs':reads,'additional_RF_write_vectors':writes,
            'existing_I64_RMW_charge_preserved':ledger['I64_RMW_already_charged'],
            'additional_I64_RMW_charge':0,'additional_C0_charge':0,
            'provider_diagnostic_ticks_added':False,'hardware_admitted':False}


class CommandLease:
    """Finite software source gate for ACK/owner ordering; no RTL claim."""
    def __init__(self): self.live=None
    def accept(self, identity, cost):
        if self.live is not None: raise ValueError('single V1 owner credit busy')
        if not isinstance(identity,tuple) or len(identity)!=4: raise ValueError('rank SM tag generation identity')
        rank,sm,tag,generation=identity
        if not 0<=rank<96 or not 0<=sm<32 or not 0<=tag<2**64 or not 0<=generation<2**64: raise ValueError('owner identity bound')
        self.live={'identity':identity,'required_reads':cost['RF_read_pair_transactions'],
                   'required_writes':cost['RF_write_vectors'],'reads':0,'writes':0,'computed':False}
    def read_return(self,identity):
        self._owner(identity)
        if self.live['computed'] or self.live['reads']>=self.live['required_reads']: raise ValueError('read phase')
        self.live['reads']+=1
    def compute_complete(self,identity):
        self._owner(identity)
        if self.live['reads']!=self.live['required_reads'] or self.live['computed']: raise ValueError('all operands required')
        self.live['computed']=True
    def write_ACK(self,identity,mirror_mask):
        self._owner(identity)
        if not self.live['computed'] or mirror_mask!=3 or self.live['writes']>=self.live['required_writes']: raise ValueError('mirrored visible ACK required')
        self.live['writes']+=1
    def retire(self,identity,consumer_accept,reverse_grant):
        self._owner(identity)
        if self.live['writes']!=self.live['required_writes'] or not consumer_accept or not reverse_grant: raise ValueError('all ACK and reverse retirement required')
        self.live=None
    def _owner(self,identity):
        if self.live is None or self.live['identity']!=identity: raise ValueError('stale V1 owner or generation')


def replay(folder):
    recorded=json.loads((folder/'model.json').read_text());actual=build(recorded['resource_contract']['lanes'])
    if actual!=recorded:raise ValueError('V1 model replay mismatch')
    return {'status':'PASS_EXACT_PINNED_V1_MODEL_REPLAY','coverage':actual['coverage'],'hardware_admitted':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--lanes',type=int,choices=[32,64,128],default=32);parser.add_argument('--verify',action='store_true')
    args=parser.parse_args()
    if args.verify:print(json.dumps(replay(args.out),sort_keys=True))
    else:
        model=build(args.lanes);args.out.mkdir(parents=True,exist_ok=False)
        (args.out/'model.json').write_text(json.dumps(model,sort_keys=True,indent=2)+'\n')
        print(json.dumps({'status':model['status'],'coverage':model['coverage']},sort_keys=True))
