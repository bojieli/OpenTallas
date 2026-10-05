#!/usr/bin/env python3
"""Golden max/min lowered to standard GPU two-source INT/FCMP instructions.

No native fmax/min credit, no three-read-port select. Model candidate only;
standard INT/compare backend area/clock and whole-token fit remain unresolved.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import w19_gpu_attention_finish as C

ROOT=Path(__file__).resolve().parents[1]
EXTRA={'OR':2,'IEQ':2,'INE':2,'ISUB':2,'FCMP_GT':2,'FCMP_LT':2}
CONST={'@EXP_MASK':0x7f800000,'@MANT_MASK':0x007fffff,'@U_ZERO':0,'@U_ONE':1,'@ALL_ONES':0xffffffff}


def op(code,dst,src,**attrs):
    return dict(op=code,dst=dst,src=list(src),latency=5 if code.startswith('FCMP') else 3,
                shared=False,attributes=attrs)


def compare(dst,a,b,maximum,prefix,predicate=None):
    p=[]
    for side,operand in [('a',a),('b',b)]:
        r=lambda n:prefix+side+'_'+n
        p += [op('AND',r('exp'),[operand,'@EXP_MASK']),op('IEQ',r('exp_all'),[r('exp'),'@EXP_MASK']),
              op('AND',r('mant'),[operand,'@MANT_MASK']),op('INE',r('mant_nonzero'),[r('mant'),'@U_ZERO']),
              op('AND',r('nan'),[r('exp_all'),r('mant_nonzero')])]
    r=lambda n:prefix+n
    p += [op('FCMP_GT' if maximum else 'FCMP_LT',r('ordered_cmp'),[a,b]),
          op('XOR',r('b_not_nan'),[r('b_nan'),'@U_ONE']),
          op('AND',r('ordered_a'),[r('ordered_cmp'),r('b_not_nan')]),
          op('OR',r('choose_a'),[r('a_nan'),r('ordered_a')]),
          op('ISUB',r('mask'),['@U_ZERO',r('choose_a')]),
          op('XOR',r('inverse_mask'),[r('mask'),'@ALL_ONES']),
          op('AND',r('a_bits'),[a,r('mask')]),op('AND',r('b_bits'),[b,r('inverse_mask')]),
          op('OR',dst,[r('a_bits'),r('b_bits')],typed_bit_view=True,**({'predicate':predicate} if predicate else {}))]
    return p


def lower(program):
    p=[]
    for pc,i in enumerate(program):
        if i['op'] in ['FMAX','FMIN']:
            p.extend(compare(i['dst'],*i['src'],i['op']=='FMAX',f'cmp{pc}_',i['attributes'].get('predicate')))
        else:p.append(i)
    return p


def calendar(program,active_lanes):
    if not 1<=active_lanes<=32:raise ValueError('warp32 active count')
    arity={**C.ARITY,**EXTRA};const=C.CONSTANTS|CONST.keys()
    ready={};t=0;retire=0;slots=set();divfree=0;counts=Counter();shared=0
    for i in program:
        if i['op'] in ['FMAX','FMIN']:raise ValueError('unlowered nativeMAX/MIN')
        if i['op'] not in arity or len(i['src'])!=arity[i['op']]:raise ValueError('arity')
        if i['dst'] in const:raise ValueError('readonly constant')
        if (i['dst'] is None)!=(i['op'] in ['STORE16','STORE32']):raise ValueError('destination')
        if any(s not in ready and s not in const for s in i['src']):raise ValueError('unwritten/unknownconst')
        start=max([t]+[ready.get(s,0) for s in i['src']]);lat=i['latency']+(active_lanes-1 if i['op']=='DIV' else 0)
        if i['op']=='DIV':start=max(start,divfree)
        end=start+lat
        while i['dst'] and end in slots:start+=1;end+=1
        if i['op']=='DIV':divfree=start+2+active_lanes
        if i['dst']:ready[i['dst']]=end;slots.add(end)
        t=start+1;retire=max(retire,end);counts[i['op']]+=1;shared+=int(i['shared'])
    live=set();peak=0
    for i in reversed(program):
        peak=max(peak,len(live|({i['dst']} if i['dst'] else set())))
        live.discard(i['dst']);live.update(s for s in i['src'] if s not in const)
        peak=max(peak,len(live))
    if peak+8>32:raise ValueError('RF32register bound')
    return dict(cycles=max(t,retire),warp_instructions=dict(counts),RF_write_slots=len(slots),shared_issue_cycles=shared,
                active_lanes=active_lanes,peak_live_value_registers=peak,reserved_address_loop_regs=8,
                RF_read_ports=2,RF_write_ports=1,immediate_operand_mux_required=True)


def build():
    profiles=[]
    for rows in [128,640]:
        original=C.profile(rows);recipes={name:lower(p) for name,p in original['recipes'].items()}
        profiles.append(dict(rows=rows,recipes=recipes,
            calendars={name:calendar(p,original['calendars'][name]['active_lanes']) for name,p in recipes.items()},
            original_calendar_cycles={name:x['cycles'] for name,x in original['calendars'].items()},
            events=original['events']))
    hc_prepost=[C.ins('LOAD','z',shared=True,source='actual HCpre/post affine sigmoid inputs8'),
                C.ins('XOR','x',['z','@SIGN'])]+C.exp_program()+[C.ins('STORE32',src=['e'],shared=True)]
    hc_max=C.max_program(2);hc_max[0]['attributes']['source']='actual HCcomb four4term rows paddedwarp32'
    hc_max[-1]['attributes']['predicate']='lane%4==0'
    hc_comb=[C.ins('LOAD','comb',shared=True,source='actualHCcomb affine16'),
             C.ins('LOAD','mb',shared=True,source='actualfour rowmax broadcasts'),
             C.ins('XOR','negmb',['mb','@SIGN']),C.ins('FADD','x',['comb','negmb'])]+C.exp_program()+[
             C.ins('STORE32',src=['e'],shared=True)]
    hc={k:dict(active_lanes=n,recipe=lower(p),calendar=calendar(lower(p),n)) for k,p,n in
        [('prepost_EXP',hc_prepost,8),('comb_rowmax',hc_max,16),('comb_EXP',hc_comb,16)]}
    paths=['tools/w19_gpu_compare_lowering.py','tools/w19_gpu_attention_finish.py','tools/hdc_golden_v41.py',
           'results/rtl/w19_checkpoint_production_20261001/gpu-attention-finish-r1.json']
    return dict(schema='opentallas.w19.gpu-exact-compare-lowering.v1',status='MODEL_INSTRUCTION_CANDIDATE_NOT_ADMITTED',
        source_pins={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
        standard_instructions_per_compare=19,constants=CONST,profiles=profiles,HC_EXP_groups=hc,
        HC_group_contract='SM0 ordinarywarp;pre/post8 independentvalues groupedonlyafteractualaffineinputsready;comb16valuesafteractualfourrowmax/broadcast.80operators;24values/operator are NOT24serializedEXPwarps.',
        ports=dict(SMs=32,SIMD_lanes_SM=128,warp_partitions=4,issue_per_partition_cycle=1,
                   RF_two_reads_one_write=True,shared_bytes_cycle_SM=128,registers_thread=32,
                   integer_F32_share_issue=True,extra_integer_lane_replicas_credited=0,
                   maximum_primitive_sources=2,three_port_select=False,
                   lane_operand_read_bits_cycle=8192,lane_write_bits_cycle=4096),
        latencies_candidate=dict(INT_including_RF=3,FCMP_including_RF=5,FADD_FMUL_including_RF=9),
        precision='leftNaN rawbits; otherwise rightNaN rawbits;orderedties RIGHT bits. FCMP produces0/1 falseonunordered; integerbitmaskselect preservespayloads andsignedzero.',
        unpriced=['actual standardGPU INT/FCMP backend area/clock/routes and immediate mux; no free INT service fromFP32budget',
                  'RF macro/mux/fanout ownership once againstSIMTaggregate','Ram composedgraph admission withcorrectedphase costs'],
        physical_qualified=False,full_token_cycles=None,adopted=False)


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    if a.out.exists():ap.error('refuse overwrite')
    a.out.write_text(json.dumps(build(),indent=2)+'\n')
