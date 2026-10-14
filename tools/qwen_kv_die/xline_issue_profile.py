#!/usr/bin/env python3
"""Audit actual emitted ME operands and derive TP8 ROM source-bandwidth bounds.
Derived bounds are not runtime throughput qualification.
"""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import hdc_isa as I

def split_for(n,k,g):
    tiles=(n+127)//128
    candidates=[(((tiles+g//s-1)//(g//s))*(k//s)*8,s)
                for s in (1<<b for b in range(g.bit_length())) if k%s==0]
    return min(candidates)[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--program',type=Path)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    native=[]
    for name,n,k in [('qkv',768,4096),('o',4096,512),('gu',3072,4096),('down',4096,1536),('head',18992,4096)]:
        s=split_for(n,k,3072);kc=k//s
        rounds=((n+127)//128+3072//s-1)//(3072//s)
        native.append(dict(name=name,rows=n,input_elements=k,split=s.bit_length()-1,k_per_split=kc,
                           rounds=rounds,issue_edges=rounds*kc*8,distinct_quad_lines=s//4,
                           source_quad_packets_per_input=(s//4)*kc,
                           roots32_phases_per_k=(s//4+31)//32,
                           roots2_full_input_edges=((s//4)*kc+1)//2,
                           cache_bytes_per_tile=kc*128//8))
    emitted=[]
    if a.program:
        for pc,word in enumerate(a.program.read_text().splitlines()):
            f=I.decode(int(word,16))
            if f['unit']!=I.UNIT_ME:continue
            keep={k:v for k,v in f.items() if k in ('me_nout','me_tiles','me_k','me_wsrc','me_split','me_xbase','me_xks','me_xjs','me_xcs','me_d_k','me_d_tiles','me_d_nout')}
            emitted.append(dict(pc=pc,fields=keep,x_varies_with_k=f['me_xks']!=0,x_varies_with_j=f['me_xjs']!=0))
    report=dict(status='source_derived_not_native_runtime_qualification',
                native_geometry=dict(tp=8,groups=3072,W=16,IL=8,tiles=768,NXL=512),
                native_ROM_policy_profiles=native,emitted_program=str(a.program),emitted_ME_operands=emitted,
                immutable_issue_invariant='xbase+c*xcs+k*xks+j*xjs changes during one instruction; snapshot hold is insufficient',
                source_requirement='32 roots can cover native split<=9 in<=4 phases per k, repeated8 j slots; split11 needs16 phases and requires fullpreload cache or more source bandwidth',
                physical_payload_bits=dict(two_snapshot_roots=256,roots32=4096,full128quad_parallel=16384,full512quad_parallel=65536))
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
