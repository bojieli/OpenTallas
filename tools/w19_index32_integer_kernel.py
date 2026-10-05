#!/usr/bin/env python3
"""Bounded standard GPU INT32 block lowering candidate; no RTL or decoder credit.

Inputs are exact signed twice-E2M1 units, scales are UE8M0 exponents.
All numerical work executes the published two-source instruction program.
Packed decode, full score reduction/top-k, transport, and physical fit pending.
"""
import argparse
import hashlib
import json
from pathlib import Path

UNITS=(0,1,2,3,4,6,8,12,0,-1,-2,-3,-4,-6,-8,-12)
ARITY={'MOV':1,'LOAD':1,'CLZ':1,'IADD':2,'ISUB':2,'IMUL':2,'AND':2,'OR':2,'SHL':2,'SHR':2}


def ins(op,dst,*src): return {'op':op,'dst':dst,'src':list(src)}
def branch(op,a,b,yes,no):return {'op':op,'src':[a,b],'yes':yes,'no':no}


def program():
    p=[ins('MOV','acc',0)]
    for j in range(32):
        p += [ins('LOAD','q',f'q{j}'),ins('LOAD','k',f'k{j}'),ins('IMUL','p','q','k'),ins('IADD','acc','acc','p')]
    # Absolute integer coefficient <=4608, at most13 significant bits.
    body=[ins('MOV','mag','acc'),ins('MOV','sign',0),
          branch('BLT','acc',0,[ins('ISUB','mag',0,'acc'),ins('MOV','sign',0x80000000)],[]),
          ins('CLZ','lz','mag'),ins('ISUB','top',31,'lz'),ins('IADD','power','eq','ek'),
          ins('ISUB','power','power',2),ins('IADD','exp','power','top')]
    normal=[ins('IADD','biased','exp',127),ins('ISUB','shift',23,'top'),ins('SHL','mant','mag','shift'),
            ins('AND','mant','mant',0x7fffff),ins('SHL','biased','biased',23),ins('OR','bits','biased','mant')]
    round_up=[ins('IADD','bits','bits',1)]
    sub=[ins('IADD','shift','power',149)]
    right=[ins('ISUB','shift',0,'shift'),
           branch('BGT','shift',14,[ins('MOV','bits',0)],
             [ins('SHR','bits','mag','shift'),ins('SHL','back','bits','shift'),ins('ISUB','rem','mag','back'),
              ins('ISUB','hs','shift',1),ins('SHL','half',1,'hs'),
              branch('BGT','rem','half',round_up,
                [branch('BEQ','rem','half',[ins('AND','odd','bits',1),branch('BEQ','odd',1,round_up,[])],[])])])]
    sub += [branch('BLT','shift',0,right,[ins('SHL','bits','mag','shift')])]
    body += [branch('BGT','exp',127,[ins('MOV','bits',0x7f800000)],
                   [branch('BLT','exp',-126,sub,normal)]),
             branch('BEQ','bits',0,[],[ins('OR','bits','bits','sign')])]
    return p+[branch('BEQ','acc',0,[ins('MOV','bits',0)],body)]


def execute(q,k,eq,ek):
    if len(q)!=32 or len(k)!=32:raise ValueError('exact32terms')
    if any(x not in UNITS for x in list(q)+list(k)):raise ValueError('E2M1 normalized units')
    if not (-126<=eq<=127 and -126<=ek<=127):raise ValueError('producer finite-scale range')
    # No claim that every code at every exponent is a finite BF16 producer value.
    if any(abs(x)*(2.0**(e-1))>3.3895313892515355e38 for xs,e in [(q,eq),(k,ek)] for x in xs):
        raise ValueError('nonfinite BF16 producer')
    regs={'eq':eq,'ek':ek};mem={**{f'q{i}':int(x) for i,x in enumerate(q)},**{f'k{i}':int(x) for i,x in enumerate(k)}};trace=[]
    def signed(x):return x-(1<<32) if x&(1<<31) else x
    def val(x):return x&0xffffffff if isinstance(x,int) else regs[x]
    def run(p):
        for i in p:
            op=i['op']
            if op=='LOAD':args=[mem[i['src'][0]]&0xffffffff]
            else:args=[val(x) for x in i['src']]
            if op.startswith('B'):
                a,b=[signed(x) for x in args];take=(a==b) if op=='BEQ' else (a<b) if op=='BLT' else (a>b)
                trace.append({'op':op,'src':i['src'],'taken':take});run(i['yes'] if take else i['no']);continue
            if len(args)!=ARITY[op]:raise ValueError('opcodearity')
            a=args[0];b=args[1] if len(args)==2 else None
            if op in ['LOAD','MOV']:r=a
            elif op=='CLZ':r=32-a.bit_length()
            elif op=='IADD':r=a+b
            elif op=='ISUB':r=a-b
            elif op=='IMUL':r=a*b
            elif op=='AND':r=a&b
            elif op=='OR':r=a|b
            elif op in ['SHL','SHR']:
                if not 0<=b<32:raise ValueError('unbounded GPUshift')
                r=a<<b if op=='SHL' else a>>b
            regs[i['dst']]=r&0xffffffff;trace.append({**i,'bits':regs[i['dst']]})
    run(program());return regs['bits'],trace


def worst(p):
    return sum(1+max(worst(i['yes']),worst(i['no'])) if i['op'].startswith('B') else 1 for i in p)


def build():
    root=Path(__file__).resolve().parents[1]
    return {'schema':'opentallas.w19.index32.integer-kernel.v1','status':'BOUNDED_BLOCK_CANDIDATE_NOT_ADMITTED',
      'source_pins':{p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in ['tools/w19_index32_integer_kernel.py','tools/hdc_golden_v41.py']},
      'program':program(),'signed_units':list(UNITS),'integer_product_max':144,'integer_sum_abs_max':4608,
      'rounding':'single FP32 RNE per32term block, normal/subnormal/overflow; canonical positive zero',
      'ports':{'RF_read':2,'RF_write':1,'symbolic_register_names_including_two_scales':21,'reserved_address_loop_registers':8,'RF_register_limit':32,'shared_warp_bytes':128,'query_load_bytes_per_lane_block':128,'key_load_bytes_per_lane_block':128},
      'calendar':{'worst_path_warp_instructions':worst(program()),'serialized_candidate_cycles':3*worst(program()),
                  'INT_and_branch_latency_including_RF_candidate':3,'clock_GHz_candidate':0.9,
                  'parallel_warps_credited':0,'packed_decode_cost':None,'branch_divergence_reconvergence_cost':None},
      'boundaries_pending':['packed E2M1/UE8M0 decode honoring BF16 producer rounding','four block results sequential csum8 from+0 with four paddedzero adds',
       'BF16score then exact max(score,+0) wrapper then weights product/BF16','32head chunk8/tree and BF16final',
       'global row ownership (i//8)%96, finite outerloop preserving globalIDs','selection metadata and actual finite read/write service'],
      'INT_area_mm2':None,'route_fit':None,'full_token_cycles':None,'RTL_qualified':False,'adopted':False}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args()
    Path(a.out).write_text(json.dumps(build(),indent=2)+'\n')
