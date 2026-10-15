#!/usr/bin/env python3
"""Emit actual ot_vms_calendar_static W44 programme words for one HC component.

Cycles are consumer clock edges. The actual registered SRAM issuer places
word0 at its outputs start+4, and the HC engine samples it start+5. Caller
supplies the absolute first consumer edge and the measured sink/core phase.
These are component images, not a whole-layer schedule or rate certificate.
"""
import argparse,json
from pathlib import Path
FIELDS={'clear':(0,1),'row_launch':(1,1),'row_raw_read':(2,1),'row_weight_slot':(3,1),
        'row_id':(4,5),'tail_launch':(9,1),'sink_launch':(10,1),'sink_capture':(11,1),'norm_eps':(12,32)}
def pack(**kw):
    word=0
    for k,v in kw.items():
        lo,n=FIELDS[k]
        if not 0<=v<1<<n:raise ValueError(k)
        word|=v<<lo
    return word

def lower(kind,*,first_consumer_cycle,sink_divisor,sink_phase,row=0,slot=0,eps=0x358637bd,clear=False):
    if first_consumer_cycle<5 or sink_divisor<1 or not 0<=sink_phase<sink_divisor:raise ValueError('clock calendar')
    if not 0<=row<24 or slot not in (0,1):raise ValueError('row/slot')
    if kind=='row':
        payload=[pack(norm_eps=eps,row_weight_slot=slot,row_id=row) for _ in range(356)]
        payload[0]|=pack(row_launch=1,clear=int(clear))
        for c in (180,340):payload[c]|=pack(row_raw_read=1)
        events={'launch':0,'raw_ss':180,'raw_row':340,'result':345,'next_row_earliest':356}
    elif kind=='tail':
        # e_ready at197; reserve a separate edge after readiness, then the
        # exact41Sinkhorn edges and2coreedges of stable return visibility.
        sk=first_consumer_cycle+198
        sk+=(sink_phase-sk)%sink_divisor
        capture=sk+41*sink_divisor+2
        end=capture-first_consumer_cycle+3
        if end>1024:raise ValueError('tail image exceeds actual programme SRAM')
        payload=[0]*end
        payload[0]=pack(tail_launch=1)
        payload[sk-first_consumer_cycle]=pack(sink_launch=1)
        payload[capture-first_consumer_cycle]=pack(sink_capture=1)
        events={'launch':0,'exponentials_ready':197,'sink_launch':sk-first_consumer_cycle,
                'sink_capture':capture-first_consumer_cycle,'result':capture-first_consumer_cycle+1}
    else:raise ValueError(kind)
    words=[(0xc7a1<<240)|(pc<<224)|p for pc,p in enumerate(payload)]
    return words,{'kind':kind,'instruction_payload_bits':44,'field_lsb_width':FIELDS,
        'first_consumer_cycle':first_consumer_cycle,'programme_start_edge':first_consumer_cycle-5,
        'start_base':0,'start_limit':len(words),'start_loops':1,'sink_divisor':sink_divisor,'sink_phase':sink_phase,
        'events_relative_consumer0':events,'scope':'fixed HC component image; full layer and physical phase integration pending'}
def main():
    a=argparse.ArgumentParser();a.add_argument('kind',choices=['row','tail']);a.add_argument('--output',type=Path,required=True)
    a.add_argument('--first-consumer-cycle',type=int,required=True);a.add_argument('--sink-divisor',type=int,required=True)
    a.add_argument('--sink-phase',type=int,required=True);a.add_argument('--row',type=int,default=0)
    a.add_argument('--slot',type=int,default=0);a.add_argument('--clear',action='store_true');x=a.parse_args()
    words,meta=lower(x.kind,first_consumer_cycle=x.first_consumer_cycle,sink_divisor=x.sink_divisor,
        sink_phase=x.sink_phase,row=x.row,slot=x.slot,clear=x.clear)
    x.output.parent.mkdir(parents=True,exist_ok=True)
    x.output.write_text(''.join(f'{w:064x}\n' for w in words))
    x.output.with_suffix('.json').write_text(json.dumps(meta,indent=2)+'\n')
if __name__=='__main__':main()
