"""Immutable source shape fingerprints. Symbolic metadata only; no numerical VM.

Inputs to the hardware lookup MUST come from retained source/lease metadata,
not a copy of the pending command. This compiler authorizes no RF allocation.
"""
import argparse,ast,hashlib,json
from pathlib import Path
from tools.gpu_sys.canonical_qwen_primitive_control import ROOT,compile_source,canonical,PROGRAM_SHA
TYPES={'<f4':0,'<u4':1,'<i8':2,'|u1':3,'|i1':4}
F32='<f4';U32='<u4';I64='<i8';U8='|u1';I8='|i1'
def value(dtype,shape=()):return dict(dtype=dtype,shape=list(shape))
def expression(text,env):
    n=ast.parse(text,mode='eval').body
    if isinstance(n,ast.Name):return dict(env[n.id])
    if isinstance(n,ast.Constant) and type(n.value) is int:return value(I64)
    if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='f32':return value(F32)
    raise ValueError('unsupported source metadata expression '+text)
def broadcast(args):
    shapes=[a['shape'] for a in args];rank=max(map(len,shapes),default=0)
    assert rank<=1
    dims={s[0] for s in shapes if s and s[0]!=1}
    assert len(dims)<=1,'incompatible source broadcast'
    return [next(iter(dims)) if dims else 1] if rank else []
def result(op,args,attrs):
    shape=broadcast(args)
    if op in ('FADD','FMUL','DIV','SQRT','FMAX','FMIN','BITCAST_F','I2F','LDEXP','FP8_UNPACK'):dtype=F32
    elif op=='BITCAST_U' or op.startswith('FCMP_'):dtype=U32
    elif op=='F2I':dtype=I64
    elif op=='FP8_PACK':dtype=U8
    elif op=='COPY':dtype=args[0]['dtype']
    elif op=='SELECT':dtype={'U32':U32,'I64':I64,'F32':F32}[attrs['dtype']]
    else:dtype=I64 if attrs.get('dtype')=='I64' or (attrs.get('dtype')!='U32' and any(a['dtype']==I64 for a in args)) else U32
    return value(dtype,shape)
def seeds(template):
    if template in ('add','mul'):
        # Real leaf calls: scalar reductions, vectors, vector/scalar broadcasts.
        seen=set()
        for n in range(1,129):
            for sa,sb in (((),()),((n,),()),((),(n,)),((n,),(n,)),((n,),(1,)),((1,),(n,))):
                key=(sa,sb)
                if key not in seen:seen.add(key);yield dict(a=value(F32,sa),b=value(F32,sb))
    elif template in ('rsqrt','maximum','argmax','winner'):
        names={'rsqrt':['variance'],'maximum':['a','b'],'argmax':['candidate','best'],'winner':['a','b','ai','bi']}[template]
        yield {n:value(U32 if n in ('ai','bi') else F32) for n in names}
    else:
        dtype=I8 if template=='convert' else U8 if template=='fp8unpack' else F32
        for n in range(1,129):yield dict(x=value(dtype,(n,)))
        if template in ('neg','reciprocal'):yield dict(x=value(dtype))
def count(a):return a['shape'][0] if a['shape'] else 1
def key(descriptor,args):
    counts=sum(count(a)<<(8*i) for i,a in enumerate(args))
    types=sum(TYPES[a['dtype']]<<(3*i) for i,a in enumerate(args))
    ranks=sum(bool(a['shape'])<<i for i,a in enumerate(args))
    return descriptor|(len(args)<<8)|(types<<11)|(counts<<23)|(ranks<<55)
def canonical_descriptor(row,args,out):
    return dict(template=row['template'],ordered_step=row['ordered_step'],source_node=row['source_node'],
                lowered_primitive=row['lowered_primitive'],attrs=row['attrs'],explicit_shape=None,
                operands=args,source_result_dtype=out['dtype'],result_shape=out['shape'])
def build():
    source=compile_source();by_template={}
    for r in source['descriptors']:by_template.setdefault(r['template'],{}).setdefault(r['ordered_step'],[]).append(r)
    profiles={}
    for template,steps in by_template.items():
        for env0 in seeds(template):
            env=dict(env0)
            for step,rows in steps.items():
                node=rows[0]['source_node'];args=[expression(t,env) for t in node['src']]
                for row in rows:
                    if node['op']=='NEG':
                        if row['substep']==0:args=[value(F32,args[0]['shape'])]
                        elif row['substep']==1:args=[out,value(U32)]
                        else:args=[out]
                    out=result(row['lowered_primitive'],args,row['attrs'])
                    descriptor=canonical_descriptor(row,args,out);h=hashlib.sha256(canonical(descriptor)).hexdigest()
                    k=key(row['id'],args);r=dict(descriptor_id=row['id'],source_key=k,descriptor=descriptor,sha256=h,
                                              result_elements=count(out),result_type=TYPES[out['dtype']],result_vector=bool(out['shape']),
                                              compatible_controller=all(TYPES[a['dtype']]<4 or (a['dtype']==I8 and row['lowered_primitive']=='I2F') for a in args))
                    assert k not in profiles or profiles[k]==r,'source key does not uniquely select exact shape'
                    profiles[k]=r
                env[node['dst']]=out
    # Compact immutable address translation; no scan/comparator per profile.
    # source rank_mask and count>1 mask distinguish []/[1]/[N] broadcasts.
    groups={}
    for k,p in profiles.items():
        args=p['descriptor']['operands'];ranks=sum(bool(a['shape'])<<i for i,a in enumerate(args));vary=sum((count(a)>1)<<i for i,a in enumerate(args))
        address=p['descriptor_id']*256+ranks*16+vary
        anchor=max((count(a) for a in args),default=1);ordinal=anchor-2 if anchor>1 else 0
        assert ordinal not in groups.setdefault(address,{});groups[address][ordinal]=p
    emitted=[];base=[0]*(len(source['descriptors'])*256)
    for address,variants in sorted(groups.items()):
        start=len(emitted);base[address]=(1<<16)|start
        for ordinal in range(max(variants)+1):
            p=variants.get(ordinal)
            if p is None:emitted.append(dict(word='0'*83,valid=False));continue
            # record328 = valid1 + compatible1 + result_vector1 + type3 + elements8 + key59 + sha256
            word=int(p['sha256'],16)|(p['source_key']<<256)|(p['result_elements']<<315)|(p['result_type']<<323)|(int(p['result_vector'])<<326)|(int(p['compatible_controller'])<<327)|(1<<328)
            emitted.append(dict(p,valid=True,word=f'{word:083x}'))
    return source,base,emitted

def emit(out,endpoints):
    source,base,profiles=build();out.mkdir(parents=True,exist_ok=True)
    (out/'shape_base.mem').write_text(''.join(f'{v:05x}\n' for v in base))
    (out/'shape_profile.mem').write_text(''.join(p['word']+'\n' for p in profiles))
    (out/'profiles.json').write_bytes(canonical(dict(program_sha256=PROGRAM_SHA,profiles=profiles)))
    rom_bits=len(base)*17+len(profiles)*329+len(source['descriptors'])*24+1737*16
    model=dict(schema='opentallas.native.shape.authority.model.v1',program_sha256=PROGRAM_SHA,before_RTL=False,before_build=True,
               source='released13 recipes + VMrun_qwen attrs and expression/type/broadcast metadata; no operand values evaluated',
               profiles=len(profiles),translation_entries=len(base),bits_per_profile=329,translation_word_bits=17,
               ROM_bits_per_readport=rom_bits,installed_readports=4,factory_services=1,endpoint_count=endpoints,installed_ROM_bits=rom_bits,
               shared_ROM_credit=0,extra_mutable_state_bits=0,registered_edges_added=0,
               boundary_input_bits_per_actor=363,boundary_output_bits_per_actor=580,
               counts_compare_mux_inputs=4,translation_mux_inputs=len(base),profile_mux_inputs=len(profiles),
               area_um2=None,macro_slot_fit=None,power_W=None,wire_stage_cycles=None,CDC_cycles=None,
               routed_corridor_capacity=None,loaded_SS60_FF25_clock=None,token_gain=None,
               estimate='ESTIMATE: actual behavioral ROM mux upper bound plus decode/source select/return/compare. No macro area credit, measured delay, clock, gain or adoption.',
               default_enabled=False,adopt=False,
               unsupported_profiles=sum(p.get('valid',False) and not p.get('compatible_controller',False) for p in profiles),
               controller_successor=dict(original46_unchanged=True,extra_coded_command_words=0,new_profile_fields_fit_existing_padding=True,extra_control_state_bits=0,read_operand_export_bits=2,read_page_export_bits=1,write_page_export_bits=1,additional_wire_area=None,I8_datapath_owner='Ampere',authority_profile_compare_logic_area=None),
               unsupported_reason='Released convert input signed INT8 is retained as |i1. Signed I8 literal requires independently sourced profileflag with U8 raw carrier and Ampere actual signed-I8 delegate; no U8 semantic alias.',
               upstream_required='Nash actualheldroot/full239+source descriptor/types/counts/ranks from source cursor/lease metadata, independent ofcmd fields; sourcelease/aperture collector separatelyowned')
    # Before build cost: one physical service, conservatively mapped as mux ROMs.
    # Unit cells follow tools/uarch_model.py DFF and the existing NAND/INV ledger.
    mux_um2=3*0.08748+0.04374
    rom_mux_bits=(len(base)-1)*17+(len(profiles)-1)*329+(len(source['descriptors'])-1)*24+(1737-1)*16
    decode_gate_count=len(base)*15+len(profiles)*14+len(source['descriptors'])*7+1737*11
    source_mux_bits=(endpoints-1)*362
    return_gate_count=endpoints*580
    compare_gate_count=4096  # explicit conservative allowance, not measured synthesis
    logic_um2=(rom_mux_bits+source_mux_bits)*mux_um2+(decode_gate_count+return_gate_count+compare_gate_count)*0.08748
    tracks=endpoints*(363+580)
    model.update(area_um2_ESTIMATE=logic_um2,area_breakdown_ESTIMATE=dict(
        bit_mux_um2=mux_um2,ROM_mux_bit_count=rom_mux_bits,ROM_mux_um2=rom_mux_bits*mux_um2,
        decode_NAND2_count=decode_gate_count,decode_um2=decode_gate_count*0.08748,
        source_select_bit_mux_count=source_mux_bits,source_select_um2=source_mux_bits*mux_um2,
        return_gates=return_gate_count,return_um2=return_gate_count*0.08748,
        priority_key_compare_NAND2_allowance=compare_gate_count,priority_key_compare_um2=compare_gate_count*0.08748),
        controller_successor_compare_allowance_um2_ESTIMATE=2048*0.08748,
        boundary_track_connections=tracks,wire_pitch_um_ESTIMATE=0.048,
        wire_metal_area_um2_per_um_span_ESTIMATE=tracks*0.048,
        wire_stage_cost='For actual routed span L um, at least ceil(L/430) outward + ceil(L/430) return stages if that stage budget closes. RTL currently combinational, so no registered-wire timing credit.',
        ROM_logic_levels_ESTIMATE=15+14,source_mux_levels_ESTIMATE=6,
        serial_latency_model='Existing source cursor remains selected until advance. Actor wait is sum of preceding held cursor durations, not zero. Selected request has source mux + dependent base/profile ROM + key compare + return wire delay. No numerical service cycle added in this combinational source-only artifact; loaded timing unqualified.',
        composed_latency_model='For each actual RPC: existing controller read/execute/write/visibility/reverse edges + selected-source lookup timing or any physical stages + serialization wait; then enclosing SM consume/credit/CDC/refresh. No measured token rate or gain.',
        dynamic_power_model_ESTIMATE='P=sum(alpha*C*V^2*f) for priced mux/decode/select/return cells and all boundary wires; capacitance/activity/voltage/frequency require physical context. Unknown is excluded from adoption, never zero.',
        pricing_status='ESTIMATE, not fit/signoff. Behavioral ROM area upper bound charged; no synthesized or macro implementation claimed.')
    (out/'model.json').write_bytes(canonical(model));print(json.dumps({k:model[k] for k in ('profiles','translation_entries','ROM_bits_per_readport','unsupported_profiles')}))
    return model
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--endpoints',type=int,required=True);a=p.parse_args();assert a.endpoints>0;emit(a.out,a.endpoints)
