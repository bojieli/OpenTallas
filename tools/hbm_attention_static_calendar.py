#!/usr/bin/env python3
"""Compile ATT engine issue cycles, independently of ready/credit observations.

Engine phase zero follows an explicitly priced double-buffer prefetch phase.
Query VM words are FP32; gather strips upper BF16, exactly as the released unit.
"""
import argparse,json,math
from pathlib import Path

def schedule(H=16,D=512,TD=64,NL=4,T=640,mode='qk'):
    if D%TD or TD%NL or TD%H or T<1 or T>640:raise ValueError('unsupported exact production shape')
    events={};S=D//TD;dpt=TD//NL;fillc=TD//NL;R=TD//H
    def put(c,event):events.setdefault(c,[]).append(event)
    put(0,'job')
    for c in range(math.ceil(T/NL)):put(1+c,'kv')
    if mode=='qk':
        for h in range(H):put(1+h,'q')
        qk0=H+1
        for c in range(math.ceil(T/NL)):put(qk0+c,'qk')
        last=qk0+math.ceil(T/NL)-1
    elif mode=='pv':
        blocks=math.ceil(T/TD);plast=-1;lasts=[];filllast=0
        guardp=1+max(max(0,3*((R*g+j)%8-1)) - g for g in range(H) for j in range(R))
        for b in range(blocks):
            nw=math.ceil(min(T-b*TD,TD)/R)
            # Three real stationary banks: no bank is overwritten before last
            # read plus the exact chunk-position write-after-read guard.
            start=max(plast+1,1,lasts[b-3]+guardp if b>=3 else 1)
            for c in range(nw):put(start+c,'p')
            plast=start+nw-1
            fs=max(filllast+1,2,lasts[b-2] if b>=2 else 2)
            filllast=fs+fillc-1
            for c in range(fillc):put(fs+c,'fill')
            first=max(fs+fillc+1,plast+1,lasts[-1]+1 if lasts else 1)
            for c in range(dpt):put(first+c,'pv')
            lasts.append(first+dpt-1)
        last=lasts[-1]
    else:raise ValueError('mode')
    bits={'job':0,'q':1,'kv':2,'p':3,'fill':4,'qk':5,'pv':6}
    words=[sum(1<<bits[e] for e in events.get(c,[])) for c in range(last+1)]
    return dict(H=H,D=D,TD=TD,NL=NL,T=T,mode=mode,events={str(k):v for k,v in sorted(events.items())},words=words,last_issue_cycle=last,issue_period=last+1)

def model(H=16,D=512,NL=4):
    prefetch=H*D*4//256
    shapes=[schedule(H,D,64,NL,T,m) for T in (128,640) for m in ('qk','pv')]
    return dict(schema='opentallas.hbm_attention.static_model.v1',heads=H,dim=D,row_lanes=NL,engine='actual ot_hdc_v41x_attn arithmetic, PHYS0, SRAM_MACRO1',controller='absolute compiler events job/q/kv/p/fill/qk/pv; no ready/credits',query_source='actual FP32 VM sectors upper16 extraction, unchanged precision',VM_group='NE RG3 of RG7; 8banks rq17/rr257; n+6 response, n+7 capture plus unqualified physical stations',query_prefetch_edges=prefetch,query_prefetch_bytes=H*D*4,query_gather=dict(macros=64,master='ot_sram_1r1w_32x128_m1',depth=32,width=128,banks=2,heads_per_bank=16,useful_bytes=2*16*512*2,macro_area_um2=64*51.408*20.790,read_edges=1),staging=dict(macros=NL*math.ceil((D//32*265)/256),master='ot_sram_1r1w_256x256_m2_r2c2',row_payload_bits=D//32*265,rows=640),traffic=dict(query_VM_payload_bits_per_edge=2048,query_head_bits=D*16,PS_packed_rows_bits_per_edge=NL*(D//32)*265,probability_word_bits=64*16),clock_period_ps=833.333,price_immutable={128:147.144,640:339.144},calendar_shapes=[{k:v for k,v in s.items() if k not in ('events','words')} for s in shapes],service_bound='max(query-prefetch phase, actual engine issue period, real PS staging fill) plus allocated source/boundary schedule; numerical/throughput unverified',qualification=False,remaining=['Measured full H16 arithmetic + actual mapped staging/gather proof','Actual PS producer burst/allocation; no hypothetical wide VM row port','Native programme SRAM image/VM request schedule and physical station edges','Actual controller/gather mapped footprint, clock-root census, slot and route','Actual score/PV VM output drain/commit schedule'])
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    (a.out/'model.json').write_text(json.dumps(model(),indent=2)+'\n')
    for T in (128,640):
        for mode in ('qk','pv'):
            s=schedule(T=T,mode=mode);(a.out/f'{mode}{T}.json').write_text(json.dumps(s,indent=2)+'\n');(a.out/f'{mode}{T}.hex').write_text(''.join(f'{w:02x}\n' for w in s['words']))
