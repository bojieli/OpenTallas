#!/usr/bin/env python3
"""Static, source-derived first-BF failure trace; no RTL execution or expectation edits."""
import hashlib
import importlib.util
import json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
O=load('numerical_oracle_diagnosis','tools/dsrom_actual_element_numerical_oracle.py')
G=load('golden_diagnosis','tools/hdc_golden.py')
def bmul_stages(a,b):
    def dec(code):
        e=(code>>7)&255;m=code&127
        if e:return 128+m,e-127
        p=max(0,m.bit_length()-1);return m<<(7-p),-133+p
    sa,ea=dec(a);sb,eb=dec(b)
    lo=sa*(sb&15);hi=sa*(sb>>4);hs=hi+(lo>>4);pq=(hs<<4)|(lo&15)
    upper=bool(pq&32768);f=((pq&32767)<<8) if upper else ((pq&16383)<<9)
    be=ea+eb+(128 if upper else 127);sign=((a^b)>>15)&1
    zero=(a&32767)==0 or (b&32767)==0;nf=((a>>7)&255)==255 or ((b>>7)&255)==255
    bad=not (zero and not nf) and (nf or be>254 or be<-6)
    if zero and not nf or bad:y=0
    elif be>=1:y=(sign<<31)|(be<<23)|f
    else:y=(sign<<31)|(((0x800000|f)>>((1-be)&15))&0x7fffff)
    return dict(a=f'{a:04x}',b=f'{b:04x}',s1_a=sa,s1_b=sb,s1_e=ea+eb,s1_zero=zero,s1_nonfinite=nf,s2_lo=lo,s2_hi=hi,s3_hi_sum=hs,s3_product=pq,s3_fraction=f,s3_biased_exponent=be,s4_bad=int(bad),s4_y=f'{y:08x}',s5_fault=int(bad),reason='zero' if zero and not nf else 'nonfinite' if nf else 'overflow' if be>254 else 'low_exponent_refusal' if be<-6 else 'accepted')
def golden_mul(a,b):
    with np.errstate(under='ignore',over='ignore',invalid='ignore'):
        return int(G.bits(G.mul(G.from_bits(a<<16),G.from_bits(b<<16))))
def trace():
    image=json.loads((ROOT/'results/rtl/dsrom_actual_element_numerical_prepare_20261002/input_fixture.json').read_text());p=image['profiles'][3]
    stages=[];lanes=[]
    for lane in range(16):
        total=0;error=0;steps=[]
        for block in range(8):
            addr=O.word_address(p,0,0,block);word=int(image['ROM_words']['0'][str(addr)],16);a=(word>>(16*lane))&65535;b=O.xbcode(0,0,block,lane)
            s=bmul_stages(a,b);s.update(lane=lane,block=block,logical_address=addr,PP_bank=addr&1,PP_row=addr>>1,ROM_word_hex=f'{word:069x}',golden_product=f'{golden_mul(a,b):08x}')
            assert int(s['golden_product'],16)==O.mul(a<<16,b<<16)
            term=int(s['s4_y'],16);before=total;total=O.add(total,term);error|=s['s5_fault']
            assert total==int(G.bits(G.add(G.from_bits(before),G.from_bits(term))))
            steps.append(dict(block=block,acc_before=f'{before:08x}',term=f'{term:08x}',acc_after=f'{total:08x}',term_fault=s['s5_fault'],sticky_error=error,adder_error=0))
            stages.append(s)
        lanes.append(dict(lane=lane,sum=f'{total:08x}',error=error,chain=steps))
    nodes=[(int(l['sum'],16),l['error']) for l in lanes];levels=[]
    while len(nodes)>1:
        operations=[];next_nodes=[]
        for i in range(0,len(nodes),2):
            a,af=nodes[i];b,bf=nodes[i+1];v=O.add(a,b);e=af|bf
            assert v==int(G.bits(G.add(G.from_bits(a),G.from_bits(b))))
            operations.append(dict(left=f'{a:08x}',right=f'{b:08x}',sum=f'{v:08x}',left_error=af,right_error=bf,adder_error=0,output_error=e));next_nodes.append((v,e))
        levels.append(operations);nodes=next_nodes
    assert nodes==[(0xcbfffffc,1)]
    faults=[s for s in stages if s['s5_fault']];differences=[s for s in stages if s['s4_y']!=s['golden_product']]
    assert not differences and faults and all(s['reason']=='low_exponent_refusal' for s in faults)
    witnesses=[]
    for a,b in [(0x0080,0x3380),(0x0080,0x0080),(0x0080,0x3b80),(0x0080,0x3c00)]:
        s=bmul_stages(a,b);s['golden_product']=f'{golden_mul(a,b):08x}';witnesses.append(s)
    return dict(status='STATIC_SOURCE_TRACE_NOT_NEW_RTL_RUN',first_partial=dict(phase=3,macro=0,segment=0,position=0,source_modeled_value=f'{nodes[0][0]:08x}',source_modeled_error=nodes[0][1],oracle_value=f'{O.partial(image,3,0,0,0):08x}',observed='expected=ref=cand=cbfffffc referr=canderr=1'),products=stages,lanes=lanes,lane_tree=levels,fault_products=faults,product_bit_differences=differences,primitive_witnesses=witnesses,checks=dict(products_exact_golden_crosschecked=128,chain_adds_golden_crosschecked=128,lane_tree_adds_golden_crosschecked=15,nonfinite_inputs=0,overflow_products=0,low_exponent_refusals=len(faults)),limitation='Internal stages are modeled from pinned source and actual immutable input image, not recorded runtime waveform. No error recalibration, RTL correction, compile or retry.')
if __name__=='__main__':print(json.dumps(trace(),indent=2,sort_keys=True))
