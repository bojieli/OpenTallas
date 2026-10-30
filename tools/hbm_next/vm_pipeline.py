#!/usr/bin/env python3
"""Compose bounded native VM regions, retaining actual downstream sector inputs.

The region cut list is explicit. A reverse row dependency needs a source cut;
this compiler never silently accepts it or claims a whole-programme fit.
"""
import argparse,json,sys,subprocess
from pathlib import Path
import numpy as np
from vm_value_phase import build,infer_static_boundary,engine_span
from vm_phase_region import merge_intervals


def intervals(mask):
    points=np.flatnonzero(mask)
    return [[int(a[0]),int(a[-1])+1]for a in np.split(points,np.flatnonzero(np.diff(points)!=1)+1)if len(a)]


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for k in ('image','compiler-tools','out-dir'):ap.add_argument('--'+k,required=k!='compiler-tools')
    ap.add_argument('--extra-live-out',help='JSON list of bounded final source-word intervals')
    ap.add_argument('--cuts',required=True,help='first:last comma separated adjacent source ranges')
    ap.add_argument('--scratch-base',type=lambda s:int(s,0),required=True)
    a=ap.parse_args()
    from isa_loader import load_isa
    IR,IC=load_isa(a.compiler_tools)
    import hashlib
    raw=Path(a.image).read_bytes();rr=IC.decode_all(raw);out=Path(a.out_dir);out.mkdir(parents=True,exist_ok=True)
    cuts=[tuple(map(int,v.split(':')))for v in a.cuts.split(',')]
    if any(x[1]+1!=y[0]for x,y in zip(cuts,cuts[1:])):raise ValueError('source ranges must be adjacent')
    needed=np.zeros(1<<19,bool)
    live=infer_static_boundary(rr,cuts[-1][1],IR)['known_boundary_intervals']
    if a.extra_live_out:live+=json.loads(Path(a.extra_live_out).read_text())
    for lo,hi in live:
        if not 0<=lo<hi<=len(needed):raise ValueError('declared live-out exceeds source VM ABI')
        needed[lo//8*8:(hi+7)//8*8]=True
    for stage,(first,last)in reversed(list(enumerate(cuts))):
        d=out/f'values{stage}';d.mkdir(exist_ok=True);phases=[];boundary=intervals(needed)
        for start in(0,3):
            blob,info=build(rr,first,last,start,3,IR,boundary);name=f'value_{start}.hgi1r';(d/name).write_bytes(blob);info['fragment']=name;phases.append(info)
        packet=dict(schema='opentallas.hbm.vm_value_phase.v1',source_sha256=hashlib.sha256(raw).hexdigest(),source_record_range=[first,last],boundary=dict(known_boundary_intervals=boundary,whole_programme_fit=None),phases=phases)
        (d/'values.json').write_text(json.dumps(packet,indent=1)+'\n')
        # A previous stage supplies every external load, plus live boundary
        # sectors not completely produced by this stage. Rounded sectors retain
        # neighbours needed by native partial-output publication.
        written=np.zeros(len(needed),bool)
        for index in range(first,last+1):
            for _,row in IR.expand(rr[index][1],rr[index][2]):
                for k in IR.written_operands(row):
                    if k in row.desc and row.desc[k].space=='VM':
                        lo,hi=engine_span(row,k);written[lo:hi]=True
        prev=needed&~written
        for ph in phases:
            for load in ph['boundary_loads']:
                lo,hi=load['source_words'];prev[lo:hi]=True
        needed=prev
    upstream=None
    for stage,_ in enumerate(cuts):
        values=out/f'values{stage}'/'values.json';shadow=out/f'shadow{stage}'
        common=['--image',a.image]
        if a.compiler_tools:common+=['--compiler-tools',a.compiler_tools]
        subprocess.run([sys.executable,str(Path(__file__).with_name('vm_phase_shadow.py')),*common,'--values',str(values),'--scratch-base',hex(a.scratch_base+stage*0x1000000),'--out-dir',str(shadow)],check=True)
        if upstream is None:
            # Start with an ordinary native component; the linker accepts it.
            upstream=shadow/'shadow.json'
        else:
            link=out/f'link{stage}'
            subprocess.run([sys.executable,str(Path(__file__).with_name('vm_phase_link.py')),*common,'--upstream',str(upstream),'--downstream',str(shadow/'shadow.json'),'--downstream-values',str(values),'--out-dir',str(link)],check=True)
            upstream=link/'chain.json'
    print(json.dumps(dict(chain=str(upstream),source_ranges=cuts,whole_programme_executable=False,scratch_reserved=False)))

if __name__=='__main__':main()
