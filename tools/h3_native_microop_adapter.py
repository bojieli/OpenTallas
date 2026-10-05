#!/usr/bin/env python3
"""Common software entrypoint/ABI for the actual DS and Qwen primitive VMs.

Keeps both source dialects intact, including their different native rounding and
DIV/reciprocal contracts. No source-family callback or timing oracle is added.
"""
from collections import Counter
import hashlib
import importlib.util
from pathlib import Path
import numpy as np
import h3_deepseek_complete_native as DS
import h3_deepseek_bounded_tiles as T
import h3_deepseek_streaming_linear as STREAM
import h3_deepseek_staged_native as STAGE
ROOT=Path(__file__).resolve().parents[1]
DEP=ROOT/'results/uarch/h3_deepseek_bounded_tiles_20261002/dependencies'


def load(name):
    path=DEP/(name+'.py');spec=importlib.util.spec_from_file_location('pinned_'+name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
QW=load('h3_qwen_complete_native')
CAL=load('h3_complete_native_calendar')
PASS_STATUSES={'PASS_BOUNDED_NATIVE_TILES','PASS_FORWARD_STREAMING_NATIVE_LINEAR','PASS_FORWARD_STREAMING_NATIVE_INDEX','PASS_SOURCE_ORDER_STAGED_NATIVE','PASS_FORWARD_STREAMING_NATIVE_FLOAT','PASS_FORWARD_STREAMING_NATIVE_GATHER'}
ALIASES={'BITS':'BITCAST_U','FLOAT_BITS':'BITCAST_F','ITOF':'I2F','FTOI':'F2I','CMP_EQ':'FCMP_EQ','CMP_GT':'FCMP_GT','CMP_LT':'FCMP_LT'}


def walk(nodes):
    for node in nodes:
        yield node
        if node['op']=='FOR':yield from walk(node['body'])


def ABI(ds_program,qwen_program):
    qw=set(node['op'] for op in qwen_program['operations'] for node in walk(op['recipe']))
    return {'schema':'H3_TWO_MODEL_NATIVE_MICROOP_ABI_V1','DS':{'schema':ds_program['schema'],'PCs':ds_program['coverage']['PCs'],'families':len(ds_program['coverage']['families']),'primitives':sorted(DS.NATIVE),'execution':'original SSA tile continuations','arithmetic':'chunk8/noFMA/exactDIV source99da'},
            'Qwen':{'schema':qwen_program['schema'],'PCs':len(qwen_program['operations']),'families':len(qwen_program['coverage']['families']),'primitives':sorted(qw),'execution':'original FOR/index recipe Qwen Machine.nodes/run','arithmetic':'Qwen source reciprocal/rsqrt/polynomial; retain source rounding'},
            'spelling_aliases':ALIASES,'provider_contract':{'selected_read_credits':1,'selected_write_credits':1,'accepted_fragment_MAX':512,'identity':'PC/version/rank/SM/generation/fragment','logical_ACK_is_not_physical_visibility':True},
            'calendar_contract':'positive explicit duration per executed primitive, transfer and memo/frame event; all finite reservations held to reverse consume; no unknown cost zero',
            'hardware_qualified':False,'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),DEP/'h3_qwen_complete_native.py',DEP/'h3_complete_native_calendar.py',ROOT/'tools/qwen_hbm_complete_program.py')}}


def execute_ds(program,inputs,owner,work_limit=2000000):
    family=program.get('family')
    if family=='linear_q':
        fmt=program['source_attributes'].get('fmt','fp8');value,receipt=STREAM.StreamingLinear(owner).run(inputs['x'],inputs['weight_codes'],inputs['weight_scale_codes'],fmt)
        return ({} if value is None else {'out':value}),receipt
    if family in ('mv','linear_bf16','wo_a_part'):
        value,receipt=STREAM.StreamingFloat(owner).run_float(inputs['x'],inputs['weight'],family=='linear_bf16')
        return ({} if value is None else {'out':value}),receipt
    if family=='all_gather':
        value,receipt=STREAM.StreamingGather(owner).run_gather(inputs['parts'],inputs['ownership_mask']);return {'out':value},receipt
    if family=='index_scores':return STREAM.StreamingIndex(owner).run_index(inputs,owner[2])
    if family and STAGE.plan(program)['fits']:return STAGE.StagedMachine(program,inputs,owner).run()
    out,receipt=T.TileExecutor(program,T.ArrayProvider(program,inputs,owner),work_limit).run()
    receipt['execution_path']='REFERENCE_ONLY_SCALAR_FALLBACK';receipt['latency_admitted']=False
    return out,receipt


def execute_qwen(native,token,position,machine=None,observer=None):
    machine=QW.Machine(native) if machine is None else machine
    receipt=machine.run(token,position,observer)
    return receipt,machine


def finite_calendar(counts,costs,provider_commands=0,frame_commands=0):
    # One selected owner: conservative explicit serialization, no ideal overlap.
    needed=set(counts)|({'provider'} if provider_commands else set())|({'frame'} if frame_commands else set())
    if any(type(costs.get(op)) is not int or costs[op]<=0 for op in needed):raise ValueError('positive explicit measured/provisional cost required')
    c=CAL.Calendar({'RF_R':2,'RF_W':1,'provider':1,'frame':1});dep=[]
    for op,count in sorted(counts.items()):
        if type(count) is not int or count<0:raise ValueError('finite instruction count')
        if count:
            name=c.add(op,dep,count*costs[op],{'RF_R':2,'RF_W':1},repeats=count,primitive=op,provisional=True);dep=[name]
    for label,count in [('provider',provider_commands),('frame',frame_commands)]:
        if type(count) is not int or count<0:raise ValueError('finite traffic count')
        if count:name=c.add(label,dep,count*costs[label],{label:1},repeats=count,provisional=True);dep=[name]
    return {'events':c.events,'end_cycle':max(c.ends.values(),default=0),'policy':'conservative counted work+transfers; positive explicit costs; no latency qualification','hardware_qualified':False}


def execute_bound_ds_operation(native,pc,rank,providers,generation,SM,work_limit=2000000):
    """Execute an actual PC with typed storage views, never a numeric callback.

    Each view carries its declared source version/provider ref, field, rank and
    generation. The external provider supplies source-defined data movement
    views. Unknown/missing views fail closed; no zeros or weight substitutions.
    """
    if not 0<=pc<len(native['instructions']):raise ValueError('PC range')
    if type(generation) is not int or generation<0 or type(SM) is not int or not 0<=SM<32:raise ValueError('generation/SM range')
    op=native['instructions'][pc]
    if op['pc']!=pc:raise ValueError('PC identity')
    owned=next((r for r in op['rank_bindings'] if r['rank']==rank),None)
    if owned is None or owned.get('empty_owned_extent'):raise ValueError('rank has no executable owned extent')
    if owned.get('buffer_programs'):
        buffers=owned['buffer_programs'];expected={b['write_version'] for b in buffers}
        if set(providers)!=expected:raise ValueError('exact per-buffer collective provider views required')
        stores=[];receipts=[]
        for b in buffers:
            # buffer_programs is the authoritative read/write identity. The old
            # generic parts binding names the first buffer and is insufficient.
            subop=dict(op);subop['rank_bindings']=[{**owned,'template':b['template'],'buffer_programs':[]}]
            subop['writes']=[w for w in op['writes'] if w['version']==b['write_version']]
            bindings={name:dict(binding) for name,binding in op['provider_bindings'][b['template']].items()}
            for name,required in bindings.items():
                if name=='parts':required.update(version=b['read_version'],additional_versions=[b['read_version']])
                elif required['kind']=='explicit_auxiliary_provider':required['identity_from_versions']=[b['read_version']]
            subop['provider_bindings']={b['template']:bindings}
            subnative={'templates':native['templates'],'instructions':list(native['instructions'])};subnative['instructions'][pc]=subop
            values,r=execute_bound_ds_operation(subnative,pc,rank,providers[b['write_version']],generation,SM,work_limit)
            stores.extend(values);receipts.append(r)
            if r['status'] not in PASS_STATUSES:return [],{'status':'FAULT_NO_OUTPUT_PUBLICATION','buffer_receipts':receipts,'physical_provider_qualified':False}
        return stores,{'status':'PASS_BOUNDED_NATIVE_TILES','source_PC':pc,'rank':rank,'buffer_receipts':receipts,'source_result_stores':len(stores),'physical_provider_qualified':False}
    key=owned['template'];program=native['templates'][key];binding=op['provider_bindings'][key];inputs={}
    if set(providers)!=set(program['providers']):raise ValueError('exact native LOAD view set required')
    for name,value in providers.items():
        required=binding[name];kind=required['kind']
        if value.get('field')!=name or value.get('rank')!=rank or value.get('generation')!=generation or value.get('kind')!=kind:raise ValueError('typed provider field/rank/generation/kind identity '+name)
        if not value.get('provenance_certified'):raise ValueError('uncertified logical provider provenance '+name)
        if kind=='versioned_operand':
            if value.get('version')!=required['version']:raise ValueError('stale/wrong operand version '+name)
            if value.get('view_contract')!=required['native_address_view']:raise ValueError('source address view contract '+name)
        elif kind in ('immutable_parameter_provider','immutable_weight_provider'):
            if value.get('logical_tensor')!=required['logical_tensor'] or not value.get('revision'):raise ValueError('immutable provider source identity '+name)
        else:
            if value.get('source_binding')!=required:raise ValueError('explicit auxiliary/zero provider source binding '+name)
        inputs[name]=value['data']
    outputs,receipt=execute_ds(program,inputs,(pc,'PC_outputs',rank,SM,generation),work_limit)
    stores=[]
    if receipt['status'] in PASS_STATUSES:
        for write in op['writes']:
            view=write['native_result_binding'];result=view['result']
            if result not in outputs:raise ValueError('native output binding missing '+result)
            data=outputs[result]
            if 'flat_slice' in view:data=data.reshape(-1)[slice(*view['flat_slice'])]
            stores.append({'version':write['version'],'rank':rank,'SM':SM,'generation':generation,'home_indices':write['home_indices'],'source_store_view':view,'data':data,
                'compound_fields':{field:outputs[field] for field in op.get('compound_output_fields',{}).get(result,[])},'causal_visibility_certified':False})
    receipt['source_PC']=pc;receipt['rank']=rank;receipt['source_result_stores']=len(stores)
    return stores,receipt
