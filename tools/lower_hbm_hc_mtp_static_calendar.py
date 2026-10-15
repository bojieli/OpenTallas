#!/usr/bin/env python3
"""Emit actual ot_hgi_sfu_program_stripe_static W51 programme words for one PMAX8 HC component.

Cycles are consumer clock edges. The actual registered SRAM issuer places
word0 at its outputs start+4, and the HC engine samples it start+5. Caller
supplies the absolute first consumer edge and the measured sink/core phase.
These are component images, not a whole-layer schedule or rate certificate.
"""
import argparse,json
from pathlib import Path
FIELDS={'clear':(0,1),'row_launch':(1,1),'row_raw_read':(2,1),'row_weight_slot':(3,1),
        'row_id':(4,5),'tail_launch':(9,1),'sink_launch':(10,1),'sink_capture':(11,1),'norm_eps':(12,32),'row_npos':(44,4),'tail_position':(48,3)}
def pack(**kw):
    word=0
    for k,v in kw.items():
        lo,n=FIELDS[k]
        if not 0<=v<1<<n:raise ValueError(k)
        word|=v<<lo
    return word

def lower(kind,*,first_consumer_cycle,sink_divisor,sink_phase,row=0,slot=0,eps=0x358637bd,clear=False,npos=8,tail_position=0):
    if first_consumer_cycle<5 or sink_divisor<1 or not 0<=sink_phase<sink_divisor:raise ValueError('clock calendar')
    if not 0<=row<24 or slot not in (0,1) or not 1<=npos<=8 or not 0<=tail_position<8:raise ValueError('row/slot/positions')
    if kind=='row':
        period=max(322,300+160*(npos-1))
        payload=[pack(norm_eps=eps,row_weight_slot=slot,row_id=row,row_npos=npos) for _ in range(period)]
        payload[0]|=pack(row_launch=1,clear=int(clear))
        ss=[180+160*p for p in range(npos)]
        rr=[284+160*p for p in range(npos)]
        for c in ss+rr:payload[c]|=pack(row_raw_read=1)
        events={'launch':0,'raw_ss':ss,'raw_row':rr,'results':[c+5 for c in rr],'next_row_earliest':period}
    elif kind=='tail':
        # e_ready at197; reserve a separate edge after readiness, then the
        # exact41Sinkhorn edges and2coreedges of stable return visibility.
        sk=first_consumer_cycle+198
        sk+=(sink_phase-sk)%sink_divisor
        capture=sk+41*sink_divisor+2
        end=capture-first_consumer_cycle+3
        if end>2048:raise ValueError('tail image exceeds actual two-page programme SRAM')
        payload=[0]*end
        payload[0]=pack(tail_launch=1,tail_position=tail_position)
        payload[sk-first_consumer_cycle]=pack(sink_launch=1)
        payload[capture-first_consumer_cycle]=pack(sink_capture=1)
        events={'launch':0,'exponentials_ready':197,'sink_launch':sk-first_consumer_cycle,
                'sink_capture':capture-first_consumer_cycle,'result':capture-first_consumer_cycle+1}
    else:raise ValueError(kind)
    words=[(0xc7a1<<240)|(pc<<223)|p for pc,p in enumerate(payload)]
    return words,{'kind':kind,'instruction_payload_bits':51,'field_lsb_width':FIELDS,
        'first_consumer_cycle':first_consumer_cycle,'programme_start_edge':first_consumer_cycle-5,
        'start_base':0,'start_limit':len(words),'start_loops':1,'programme_pages':2,'global_PC_lsb':223,'npos':npos,'tail_position':tail_position,'sink_divisor':sink_divisor,'sink_phase':sink_phase,
        'events_relative_consumer0':events,'scope':'fixed HC component image; full layer and physical phase integration pending'}
def main():
    a=argparse.ArgumentParser();a.add_argument('kind',choices=['row','tail']);a.add_argument('--output',type=Path,required=True)
    a.add_argument('--first-consumer-cycle',type=int,required=True);a.add_argument('--sink-divisor',type=int,required=True)
    a.add_argument('--sink-phase',type=int,required=True);a.add_argument('--row',type=int,default=0)
    a.add_argument('--slot',type=int,default=0);a.add_argument('--npos',type=int,default=8);a.add_argument('--tail-position',type=int,default=0);a.add_argument('--clear',action='store_true');x=a.parse_args()
    words,meta=lower(x.kind,first_consumer_cycle=x.first_consumer_cycle,sink_divisor=x.sink_divisor,
        sink_phase=x.sink_phase,row=x.row,slot=x.slot,clear=x.clear,npos=x.npos,tail_position=x.tail_position)
    x.output.parent.mkdir(parents=True,exist_ok=True)
    x.output.write_text(''.join(f'{w:064x}\n' for w in words))
    x.output.with_suffix('.json').write_text(json.dumps(meta,indent=2)+'\n')
if __name__=='__main__':main()
