#!/usr/bin/env python3
"""Encode an already scheduled actual-SM calendar; this is not an op scheduler."""
import argparse,json
from pathlib import Path
FIELDS={'xaddr':(0,7),'slot':(7,3),'group_last':(10,1),'row':(11,12),
        'last':(23,1),'first':(24,1),'issue':(25,1),'format':(26,2),
        'format_launch':(28,1),'packet_valid':(29,1),'packet_tag':(30,10),
        'request_tag':(40,10),'request_address':(50,32),'request_valid':(82,1)}
def pack(values):
    unknown=set(values)-set(FIELDS)
    if unknown:raise ValueError(f'Unknown SM calendar fields: {sorted(unknown)}')
    word=0
    for name,(lo,bits) in FIELDS.items():
        v=values.get(name,0)
        if isinstance(v,str):v=int(v,0)
        if not isinstance(v,int) or not 0<=v<1<<bits:raise ValueError(f'{name} must fit {bits} bits')
        word|=v<<lo
    if values.get('issue',0) and not values.get('packet_valid',0):raise ValueError('A real issue must reserve a real packet')
    if values.get('format',0)==3:raise ValueError('INT8 static conversion is not implemented')
    return word

def compile_program(schedule):
    base=schedule.get('base',0);loops=schedule.get('loops',1);cycles=schedule['cycles']
    if not(0<=base<1024 and cycles and base+len(cycles)<=1024):raise ValueError('Nonempty calendar must fit actual1024-word SRAM')
    if not 1<=loops<=65535:raise ValueError('Loops must fit nonzero16-bit counter')
    writes=[]
    for index,cycle in enumerate(cycles):
        pc=base+index;command=pack(cycle);word=(0xc7a1<<240)|(pc<<224)|command
        writes.append(dict(addr=pc,data=f'{word:064x}'))
    return dict(schema='opentallas.hbm.actual-sm-static-program.v1',configuration_writes=writes,
                start=dict(base=base,limit=base+len(cycles),loops=loops),output_slots=len(cycles)*loops,
                first_calendar_after_start=4,first_s1_hop_after_start=6,
                qualification='ABI encoding only; caller must supply a proven operation and memory schedule')
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--schedule',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    result=compile_program(json.loads(a.schedule.read_text()));a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n')
