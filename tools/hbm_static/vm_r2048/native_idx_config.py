#!/usr/bin/env python3
"""Publish explicit role-local INDEX operands through actual col_idx F20 rows.

An input must name all four roles. This is a configuration packet, not evidence
that any operand has been written into VM. No pointer is relabelled or replicated.
"""
import argparse,json
from pathlib import Path
ROLES=('SW','SE','NW','NE')

def sector_ok(s,sid):
    if type(s) is not int or not 0 <= s < 1<<17:
        return False
    return ((s >> 13) & 3)==0 and not(s & 0x8000) if s & 0x10000 else ((s >> 13)&3)==sid

def compile_config(d):
    if set(d['roles']) != set(ROLES): raise ValueError('all four explicit roles required')
    n,p=d['nrows'],d['row_pitch']
    if type(n) is not int or not 1 <= n <=16 or type(p) is not int or not 0<=p<4096 or (n>1 and p==0):
        raise ValueError('invalid nrows/row_pitch')
    bits=n<<272|p<<277
    rows=[]
    for sid,role in enumerate(ROLES):
        f=d['roles'][role]
        if set(f)!=set(('weight_sector','query_sector','weight_row_stride','query_row_stride')):
            raise ValueError('explicit pointers and strides required for '+role)
        vals=[f[k] for k in ('weight_sector','query_sector','weight_row_stride','query_row_stride')]
        if any(type(x) is not int or not 0<=x<1<<17 for x in vals):raise ValueError('17-bit field outside ABI')
        for base,stride,count in ((vals[0],vals[2],4),(vals[1],vals[3],512)):
            mirror=base>>16
            for r in range(n):
                for k in range(count):
                    s=base+r*stride+k
                    if s>>16 != mirror or not sector_ok(s,sid):
                        raise ValueError(f'{role}: used sector {s} crosses role/mirror/capacity boundary')
        bits |= sum(v<<(sid*68+i*17) for i,v in enumerate(vals))
        rows.append({'role':role,'sid':sid,**f})
    return {'schema':'ot.idx.native_cfg289.v1','target':120,'frames':[{'address':2054+i,'data':f'{(bits>>(256*i))&((1<<256)-1):064x}'} for i in range(2)],'roles':rows,'nrows':n,'row_pitch':p,'extra_configuration_frames':2,'extra_steady_cycles':0,'vm_data_publication_qualified':False,'selected_source_changed':False}

def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('input',type=Path);a.add_argument('--out',required=True,type=Path);q=a.parse_args()
    out=compile_config(json.loads(q.input.read_text()));q.out.write_text(json.dumps(out,indent=2)+'\n')
if __name__=='__main__':main()
