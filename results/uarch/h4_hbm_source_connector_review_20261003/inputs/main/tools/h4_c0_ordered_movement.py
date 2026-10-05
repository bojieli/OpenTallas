#!/usr/bin/env python3
"""Source-order C0 movement lowering. No payload, RTL or provider execution.

Only whole-value source-order stages fitting RF32 plus scratch64KiB enter
Dewey V1. Streaming leaves require their actual continuation emitter and stay
UNKNOWN. This is an executable software lowering, not a hardware trace.
"""
import ast, collections, gzip, hashlib, json, math, pathlib, re, types
from h4_c0_model import pinned, sources, ROOT

STRICT='0601e4ac7fca0ada63252733d303cb601b24b507'
DISPATCH='results/uarch/h3_deepseek_bounded_tiles_20261002/forward_dispatch_milestone.json.gz'
OUT=ROOT/'results/uarch/h4_c0_ordered_movement_20261002'

def strict_api():
    raw=pinned('tools/h3_complete_native_calendar.py',STRICT)
    names={'positive','ceil','native_value_specs','resolve_ds_movement_reference',
           'audit_ds_bounded_dispatch','compose_ds_full_program_services'}
    tree=ast.parse(raw)
    selected=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    assert len(selected)==len(names)
    ns=dict(math=math,re=re,hashlib=hashlib,json=json,
            Counter=collections.Counter,defaultdict=collections.defaultdict)
    exec(compile(ast.Module(body=selected,type_ignores=[]),'Dewey060-pinned','exec'),ns)
    return types.SimpleNamespace(**{n:ns[n] for n in names})

class CapacityGate(ValueError):pass

def first_fit(live,space,size,capacity):
    intervals=sorted((h['base'],h['base']+h['size']) for h in live.values() if h['space']==space)
    cursor=0
    for start,end in intervals:
        if cursor+size<=start:return cursor
        cursor=max(cursor,end)
    return cursor if cursor+size<=capacity else None

def emit_template(program,key,dispatch_template,api):
    if dispatch_template['execution_path']!='source_order_live_range_stages':
        raise CapacityGate('UNKNOWN_FORWARD_LEAF_CONTINUATION_NOT_RESOLVED')
    template=program['templates'][key];code=template['code']
    specs=api.native_value_specs(program,key);last={}
    for index,node in enumerate(code):
        for value in node['src']:last[value]=index
    for value in template['outputs'].values():last[value]=len(code)
    live={};homes={};routes=[];events=[];peak={'RF_vectors':0,'scratch_bytes':0}
    def release(value,step):
        home=live.pop(value)
        if home['space']=='scratch':
            events.append(dict(source_step=step,event='release_after_ACK_reverse',lease=home['lease']))
    def reference(index,operand,value):
        node=code[index]
        ref=dict(template=key,code_index=index,opcode=node['op'],attrs=node['attrs'],
                 result_shape=node['shape'],operand=operand,value=value,
                 logical_byte_offset=0,payload_bytes=specs[value]['bytes'])
        api.resolve_ds_movement_reference(program,key,ref,specs)
        return ref
    def movement(index,operand,value):
        home=live[value];ref=reference(index,operand,value)
        if home['space']=='RF':
            routes.append(dict(native_instruction_ref=ref,slot_first=home['base'],vectors=home['size'],
                               visibility_guard='two-mirror visible_ACK'))
        else:
            events.append(dict(source_step=index,event='write64_ACK' if operand=='dst' else 'read64',
                lease=home['lease'],byte_address=home['base'],span_bytes=home['size'],
                repetitions=1,native_instruction_ref=ref))
    for index,node in enumerate(code):
        for value in list(live):
            if last.get(value,specs[value]['definition'])<index:release(value,index)
        if any(value not in live for value in node['src']):raise ValueError('source definition retired early')
        value=node['dst'];size=specs[value]['bytes'];vectors=api.ceil(size,512)
        base=first_fit(live,'RF',vectors,32)
        if base is not None:
            live[value]=dict(space='RF',base=base,size=vectors)
            homes[value]=dict(slot_first=base,vectors=vectors)
        else:
            extent=api.ceil(size,64)*64;base=first_fit(live,'scratch',extent,65536)
            if base is None:raise CapacityGate('UNKNOWN_FINITE_SCRATCH_CAPACITY_AT_STEP_'+str(index))
            lease=key+':'+str(index)+':'+value+':generation1'
            live[value]=dict(space='scratch',base=base,size=extent,lease=lease)
            events.append(dict(source_step=index,event='acquire',lease=lease,base=base,bytes=extent,
                               value=value,logical_byte_offset=0,payload_bytes=size))
        peak['RF_vectors']=max(peak['RF_vectors'],sum(h['size'] for h in live.values() if h['space']=='RF'))
        peak['scratch_bytes']=max(peak['scratch_bytes'],sum(h['size'] for h in live.values() if h['space']=='scratch'))
        for j,src in enumerate(node['src']):movement(index,'src:'+str(j),src)
        movement(index,'dst',value)
    for value in list(live):release(value,len(code))
    return dict(execution_path=dispatch_template['execution_path'],
        native_primitive_scalars=dispatch_template['executed_primitive_scalar_projection'],
        ordered_movements=events,RF_value_homes=homes,RF_operand_routes=routes,
        finite_occupancy_peak=peak,scope='source-order software movement lowering; no payload/RTL execution')

def produce(program,dispatch,api):
    bridge=dict(schema='H4_DS_NATIVE_SHARED_MOVEMENT_BRIDGE_V1',
        source_program_sha256=dispatch['source_program_sha256'],
        source_dispatch_sha256=hashlib.sha256(json.dumps(dispatch,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
        bridge_source_sha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
        scratch_beat_bytes=64,scratch_capacity_bytes=65536,templates={})
    gates={}
    for key,t in dispatch['templates'].items():
        try:bridge['templates'][key]=emit_template(program,key,t,api)
        except CapacityGate as exc:gates[key]=str(exc)
    return bridge,gates

def write_gz(path,value):
    path.write_bytes(gzip.compress(json.dumps(value,sort_keys=True,separators=(',',':')).encode(),mtime=0))

def main():
    _,program,_=sources();dispatch=json.loads(gzip.decompress(pinned(DISPATCH)));api=strict_api()
    bridge,gates=produce(program,dispatch,api)
    joined=api.compose_ds_full_program_services(dispatch,bridge=bridge,native_program=program)
    OUT.mkdir(parents=True,exist_ok=True)
    write_gz(OUT/'source_order_bridge.json.gz',bridge)
    write_gz(OUT/'strict060_service_join.json.gz',joined)
    write_gz(OUT/'remaining_template_gates.json.gz',gates)
    summary=dict(schema='H4_C0_ORDERED_MOVEMENT_SOFTWARE_LOWERING_V1',strict_validator_commit=STRICT,
        source_program_sha256=bridge['source_program_sha256'],source_dispatch_sha256=bridge['source_dispatch_sha256'],
        producer_sha256=bridge['bridge_source_sha256'],total_templates=len(dispatch['templates']),
        bound_templates=len(bridge['templates']),remaining_templates=len(gates),
        remaining_gates=dict(collections.Counter(gates.values())),PCs=joined['PCs'],families=joined['families'],
        unknown_shared_template_calls=joined['unknown_shared_template_calls'],
        bound_read64_subtotal=joined['bound_scratch64_read_subtotal'],
        bound_write64_ACK_subtotal=joined['bound_scratch64_write_ACK_subtotal'],
        hardware_qualification=False,payload_executed=False,full_program_ordered_execution=False,
        next_G0='Actual forward leaf continuation emitter with typed workspace refill/writeback ACK/reverse; V1 whole-value lowering does not close streaming leaves.',
        Popper_V1='integer/bit/convert/predicate hardware model required; source scalar counts are software bounds, no hardware credit')
    (OUT/'summary.json').write_text(json.dumps(summary,sort_keys=True,indent=2)+'\n')
    print(json.dumps(summary,sort_keys=True))

if __name__=='__main__':main()
