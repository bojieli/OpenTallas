#!/usr/bin/env python3
"""Offline fixed-calendar migration for the compact native VM ABI, preserving every edge.

Retired resources are errors. No runtime adapter or rescheduling is introduced.
The caller must compile the result using the new authoritative quadrant ABI.
"""
import argparse,copy,json
from pathlib import Path

def chunks(value,width,count):
    if not isinstance(value,int) or not 0<=value<(1<<(width*count)):raise ValueError("value exceeds source ABI width")
    return [(value>>(width*k))&((1<<width)-1) for k in range(count)]
def packed(values,width):
    return sum(v<<(width*k) for k,v in enumerate(values))
def migrate(schedule,quadrant):
    out=copy.deepcopy(schedule)
    for cycle in out['cycles']:
        for k,v in cycle.items():
            if isinstance(v,str):cycle[k]=int(v,0)
        if quadrant=='NW':
            # The former client3 is retired. Replay client4 becomes client3.
            for field,width in [('client_seq',2),('response_enable',1),('response_seq',2)]:
                if field in cycle:
                    values=chunks(cycle[field],width,5)
                    if values[3]:raise ValueError(f'{field} references retired NW client3')
                    cycle[field]=packed(values[:3]+values[4:],width)
            for field,count,enable in [('bank_client',8,'bank_enable'),('hub_ring_client',2,'hub_ring_enable')]:
                if field in cycle:
                    values=chunks(cycle[field],3,count)
                    for lane,v in enumerate(values):
                        if v>4:raise ValueError('NW client code exceeds old ABI')
                        if v==3 and (cycle.get(enable,0)>>lane)&1:raise ValueError('active retired NW client3')
                    cycle[field]=packed([3 if v==4 else (0 if v==3 else v) for v in values],2)
        if quadrant in ('NW','NE') and 'rslot' in cycle:
            values=chunks(cycle['rslot'],3,8)
            for bank,v in enumerate(values):
                if v>6:raise ValueError('read code exceeds old ABI')
                # Request groups are zero-based; retired group3 has code3. Packet codeRG also decrements.
                if v==3 and (cycle.get('rslot_v',0)>>bank)&1:raise ValueError('active retired read group3')
            cycle['rslot']=packed([v-1 if v>=4 else (0 if v==3 else v) for v in values],3)
        if quadrant in ('SW','SE') and 'wslot' in cycle:
            values=chunks(cycle['wslot'],3,8)
            for v in values:
                if v>5:raise ValueError('write code exceeds old ABI')
            cycle['wslot']=packed([v+1 if v else 0 for v in values],3)
    out['abi_migration']='native-compact-0253; offline only, cycles unchanged'
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument('quadrant',choices=['SW','SE','NW','NE']);ap.add_argument('input',type=Path);ap.add_argument('output',type=Path);a=ap.parse_args()
    result=migrate(json.loads(a.input.read_text()),a.quadrant)
    a.output.write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
