#!/usr/bin/env python3
"""Ordinary GPU attention dependent instruction/port calendars, model only.

Every phase consumes actual predecessor output, never a golden cut. No tensor
evaluation or approximate EXP. Transport/physical/event providers are unresolved.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from w19_gpu_norm_calendar import bf16_round

ROOT=Path(__file__).resolve().parents[1]
ARITY={'LOAD':0,'STORE16':1,'STORE32':1,'WIDEN':1,'FADD':2,'FMUL':2,'DIV':2,
       'FMAX':2,'FMIN':2,'SHFL':1,'XOR':2,'SHR':2,'SHL':2,'AND':2,'IADD':2,'F2I':1}
CONSTANTS={'@ZERO','@NEG_INF','@SIGN','@EXP_MIN','@EXP_MAX','@LOG2E','@MAGIC','@NEG_MAGIC',
           '@LN2_HI','@LN2_LO','@U23','@ONE','@ATTN_SCALE','@U16','@U1','@U7FFF','@UFFFF0000'}|{f'@POLY{i}' for i in range(7)}


def ins(code,dst=None,src=(),shared=False,**attrs):
    lat=9 if code in ['FADD','FMUL'] else 5 if code in ['FMIN','FMAX'] else 21 if code=='DIV' else 2 if code=='LOAD' else 3
    return dict(op=code,dst=dst,src=list(src),latency=lat,shared=shared,attributes=attrs)


def calendar(p,active_lanes):
    if not 1<=active_lanes<=32:raise ValueError('one finite warp with explicit active count')
    ready={};cycle=0;retire=0;writes=set();divider_free=0;counts=Counter();shared=0
    for i in p:
        if i['op'] not in ARITY or len(i['src'])!=ARITY[i['op']]:raise ValueError('arity')
        if (i['dst'] is None)!=(i['op'] in ['STORE16','STORE32']):raise ValueError('destination')
        if i['dst'] in CONSTANTS:raise ValueError('readonly constant')
        if any(s not in ready and s not in CONSTANTS for s in i['src']):raise ValueError('unwritten/unknown constant')
        start=max([cycle]+[ready.get(s,0) for s in i['src']])
        latency=i['latency']+(active_lanes-1 if i['op']=='DIV' else 0)
        if i['op']=='DIV':start=max(start,divider_free)
        end=start+latency
        while i['dst'] and end in writes:start+=1;end+=1
        if i['op']=='DIV':divider_free=start+2+active_lanes
        if i['dst']:ready[i['dst']]=end;writes.add(end)
        retire=max(retire,end);cycle=start+1;counts[i['op']]+=1
        shared+=int(i['shared'])
    live=set();peak=0
    for i in reversed(p):
        peak=max(peak,len(live|({i['dst']} if i['dst'] else set())))
        live.discard(i['dst']);live.update(s for s in i['src'] if s not in CONSTANTS)
        peak=max(peak,len(live))
    if peak+8>32:raise ValueError('RF32 regs/thread exceeded')
    return dict(cycles=max(cycle,retire),warp_instructions=dict(counts),active_lanes=active_lanes,
                shared_issue_cycles=shared,RF_write_slots=len(writes),RF_read_ports=2,RF_write_ports=1,
                peak_live_value_registers=peak,address_loop_registers=8,
                divider='one ordinary FP32RNE divider/SM II1/LAT19; active lanes serialized, RF2 included; never32 lane divider replicas')


def exp_program():
    p=[ins('FMAX','xlo',['x','@EXP_MIN']),ins('FMIN','xc',['xlo','@EXP_MAX']),
       ins('FMUL','t',['xc','@LOG2E']),ins('FADD','u',['t','@MAGIC']),
       ins('FADD','n',['u','@NEG_MAGIC']),ins('FMUL','nhi',['n','@LN2_HI']),
       ins('FMUL','nlo',['n','@LN2_LO']),ins('XOR','neghi',['nhi','@SIGN']),
       ins('XOR','neglo',['nlo','@SIGN']),ins('FADD','rhi',['xc','neghi']),
       ins('FADD','r',['rhi','neglo'])]
    for i in range(1,7):
        p += [ins('FMUL','prod',['p' if i>1 else '@POLY0','r']),ins('FADD','p',['prod',f'@POLY{i}'])]
    # Golden casts integral F32 n to int64, shifts23, adds bits(p), castsU32.
    # n bounded by EXPclamp -> signed32 conversion and modulo32 shift/add
    # yield identical low32bits; no floating power/EXP instruction substituted.
    p += [ins('F2I','ni',['n'],mode='exact integral signed32'),ins('SHL','delta',['ni','@U23']),
          ins('IADD','e',['p','delta'],typed_bit_view=True)]
    return p


def max_program(levels,global_collect=False):
    p=[ins('LOAD','v',shared=True,source='SMpartialmax paddedNEG_INF' if global_collect else 'scaledQK scores paddedNEG_INF')]
    for l in range(levels):
        p += [ins('SHFL','other',['v'],offset=1<<l),
              ins('FMAX','v',['v','other'],predicate=f'lane%{1<<(l+1)}==0')]
    return p+[ins('STORE32',src=['v'],shared=True,predicate='lane==0')]


def probabilities():
    return [ins('LOAD','s',shared=True,source='actual scaledQK'),ins('LOAD','mb',shared=True,source='actual globalmax'),
            ins('XOR','negmb',['mb','@SIGN']),ins('FADD','x',['s','negmb'])]+exp_program()+[
            ins('STORE32',src=['e'],shared=True,source='unroundedEXP for denominator'),
            *bf16_round('e','eb'),ins('STORE16',src=['eb'],shared=True,source_bits='31:16',source='roundedEXP forPV')]


def den_local(chunks):
    p=[]
    for j in range(chunks):
        for k in range(8):
            p += [ins('LOAD','v',shared=True,source=f'actual EXP at SMbase+{j*8+k}'),
                  ins('FADD',f'c{j}',[f'c{j}' if k else '@ZERO','v'])]
    level=0;nodes=[f'c{j}' for j in range(chunks)]
    while len(nodes)>1:
        nxt=[]
        for j in range(0,len(nodes),2):
            dst=f't{level}_{j//2}';p.append(ins('FADD',dst,[nodes[j],nodes[j+1]]));nxt.append(dst)
        nodes=nxt;level+=1
    return p+[ins('STORE32',src=nodes,shared=True,predicate='one lane active')]


def den_global(levels):
    p=[ins('LOAD','v',shared=True,source='actual contiguous SM sum subtrees; remaining leaves +0')]
    for l in range(levels):
        p += [ins('SHFL','other',['v'],offset=1<<l),ins('FADD','v',['v','other'],predicate=f'lane%{1<<(l+1)}==0')]
    return p+[ins('STORE32',src=['v'],shared=True,predicate='lane==0')]


def sink():
    return [ins('LOAD','sink',shared=True,source='checkpoint attn_sink[head]'),
            ins('LOAD','mb',shared=True,source='actualglobalmax'),ins('XOR','negmb',['mb','@SIGN']),
            ins('FADD','x',['sink','negmb'])]+exp_program()+[
            ins('LOAD','den',shared=True,source='actual unrounded EXP chunk8 tree'),
            ins('FADD','total',['den','e']),ins('STORE32',src=['total'],shared=True)]


def output():
    return [ins('LOAD','pv',shared=True,source='actual PV result'),ins('LOAD','den',shared=True,source='actual denominator+sink'),
            ins('DIV','out',['pv','den'])]+bf16_round('out','ob')+[
            ins('STORE16',src=['ob'],shared=True,source_bits='31:16')]


def inverse_rope():
    p=[ins('LOAD','ab',shared=True,source='outputBF16dim448+pair*2'),ins('LOAD','bb',shared=True,source='outputBF16dim449+pair*2'),
       ins('WIDEN','a',['ab']),ins('WIDEN','b',['bb']),
       ins('LOAD','c',shared=True,source='actual position coefficient COS'),ins('LOAD','s',shared=True,source='actual position coefficient SIN'),
       ins('FMUL','ac',['a','c']),ins('FMUL','bs',['b','s']),ins('FADD','re',['ac','bs']),
       ins('FMUL','bc',['b','c']),ins('FMUL','as',['a','s']),ins('XOR','negas',['as','@SIGN']),
       ins('FADD','im',['bc','negas'])]
    return p+bf16_round('re','reb')+[ins('STORE16',src=['reb'],shared=True,source_bits='31:16')]+bf16_round('im','imb')+[
        ins('STORE16',src=['imb'],shared=True,source_bits='31:16')]


def profile(rows):
    if rows not in [128,640]:raise ValueError('actual attention profiles only')
    chunks=1 if rows==128 else 4
    recipes={'score_scale':[ins('LOAD','qk',shared=True,source='actualQK'),ins('FMUL','s',['qk','@ATTN_SCALE']),ins('STORE32',src=['s'],shared=True)],
             'max_local':max_program(2 if rows==128 else 5),'max_global':max_program(5,True),
             'probabilities':probabilities(),'den_local':den_local(chunks),'den_global':den_global(4 if rows==128 else 5),
             'sink_den':sink(),'output_div_bf16':output(),'inverse_rope':inverse_rope()}
    active={'score_scale':rows//32,'max_local':4 if rows==128 else 32,'max_global':32,
            'probabilities':rows//32,'den_local':1,'den_global':16 if rows==128 else 32,
            'sink_den':1,'output_div_bf16':16,'inverse_rope':8}
    return dict(rows=rows,recipes=recipes,calendars={k:calendar(v,active[k]) for k,v in recipes.items()},
        roles={'score_scale':'32SM each4/20 actual row lanes','max_local':'32SM localpadded4/32 lanes',
               'max_global':'SM0 one warp32 after32partials arrive','probabilities':'same rowSMs asQK',
               'den_local':'16SM one contiguous8EXP chunk for128;20SM contiguous32EXP/fourchunks for640, same total globaltree order',
               'den_global':'SM0 16partials or20partials padded32, actual collect required',
               'sink_den':'SM0 one active head lane','output_div_bf16':'32SM each16dim,16 serializedDIV lanes perSM',
               'inverse_rope':'SM28..31 each8 adjacentpairs, dimensions448..511'},
        events=[{'phase':'score_scale','wait':['QK output retired']},
                {'phase':'max_local','wait':['score_scale retired']},
                {'phase':'max_global','wait':['all32 localmax collected with finitecredit']},
                {'phase':'probabilities','wait':['actualmax broadcast accepted atall32SM']},
                {'phase':'den_local','wait':['actualEXP produced +finite contiguous EXP regrouping']},
                {'phase':'den_global','wait':['all16/20 localden subtrees collected']},
                {'phase':'sink_den','wait':['globalden result andactualglobalmax visible']},
                {'phase':'PV','wait':['BF16EXP+actual decoded rows staged; actual rowepoch validated']},
                {'phase':'output_div_bf16','wait':['actual PV andsink_den broadcast visible']},
                {'phase':'inverse_rope','wait':['outputDIV/BF16 stores committed','actual positioncos/sin available']},
                {'phase':'WOA_activation_publish','wait':['all512 outputs +inverseRoPE stores visible','allconsumercompletion/fences acknowledged']}],
        missing_costs=['NoC/CDC finite collectors/broadcasts, EXP regrouping, DMA/staging/drain/fences',
                       'positioncos/sin production service and residentformat/allocation, notgolden perlayerinjection',
                       'actualordinary FP32MAX/MIN/DIV/INT wrappers, clock/area/routes/fullshapeports'],
        full_attention_cycles=None,adopted=False)


def build():
    paths=['tools/w19_gpu_attention_finish.py','tools/w19_gpu_norm_calendar.py','tools/w19_hbm_tp96_isa.py',
           'tools/hdc_golden.py','tools/hdc_golden_v41.py','results/rtl/w19_hbm_tp96_program_oreduce.json',
           'results/rtl/w19_checkpoint_production_20261001/gpu-attention-dots-r1.json']
    g=json.loads((ROOT/paths[5]).read_text())
    return dict(schema='opentallas.w19.gpu-attention-finish.v1',status='INSTRUCTION_SERVICE_MODEL_NOT_ADMITTED',
        source_pins={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
        source_graph_binding=[dict(layer=l['layer'],op=o['id'],rows=640 if o['yarn'] else 128) for l in g['layers'] for o in l['ops']
                              if o['kind']=='local' and o['fn']=='attend'],
        upstream_formats={'Q':'linear_q toBF16 thenrope_tail BF16 at rotatedtail',
                          'window':'qdq_fp8 explicitto_bf16', 'selected':'qdq_fp4_e4m3 explicitto_bf16',
                          'dots':'F32multiply inputs directly; no newBF16round inserted',
                          'PV_probabilities':'explicit G.to_bf16(e); denominator uses originalF32 e'},
        precision='SeparateFADD/FMUL RNE canonical+0; XORneg preserves signzero. EXP golden19FP32ops/6Horneriterations+integerbit scale, no nativeapprox.',
        constants={'source':'hdc_golden EXP_POLY,EXP_MIN/MAX,LOG2E,LN2_HI/LO,MAGIC;readonly immediate operand mux costunqualified',
                   'ATTN_SCALE':'actual V.Model attn_scale F(head_dim**-0.5), productionconstantport required'},
        organisation={'SMs':32,'lanes_per_SM':128,'warp_partitions':4,'registers_per_thread':32,'shared_bytes_SM':65536,
                      'latencies_candidate':{'RF_operand':2,'FP32add_mul':7,'FP32DIV':19,'DIV_II':1,'INT_SHFL':3,'FP32cmp_select':3},
                      'FMA':False,'clock_GHz':.9},
        profiles=[profile(128),profile(640)],full_token_cycles=None,physical_qualified=False)


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    if a.out.exists():ap.error('refuse overwrite')
    a.out.write_text(json.dumps(build(),indent=2)+'\n')
