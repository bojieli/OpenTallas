#!/usr/bin/env python3
"""Diagnose autonomous quant-train conflicts; solve static release slots, not RTL.

Inputs are norm_q_report.py's measured geometry/root report.  A release solution
is a conditional contract: it does not assert that NORMR shifts can produce the
same root slots, or that release control already exists in the hardware.
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path
import norm_q as Q


def solve_report(report, max_delay=512):
    sl=report['slices']; names=sorted(sl,key=lambda n:sl[n]['sid'])
    pos={i:(sl[i]['sid']>>1,sl[i]['sid']&1) for i in names}
    byct={v:k for k,v in pos.items()}
    geo=dict(pos=pos,partner={i:byct[(c,1-t)] for i,(c,t) in pos.items()},
             age={(i,s):report['line_age'][i+'.'+s] for i in names for s in ('e','w') if i+'.'+s in report['line_age']})
    Q.V_ASM={i:2+report['v_age'][i] for i in names}
    footprints={}
    for i in names:
        occ,cl,oa=Q.allgather({i:0},geo)
        if cl or oa:raise ValueError(f'intrinsic single-train collision {i}')
        f=defaultdict(set)
        for n,s,e in occ:f[(n,s)].add(e)
        # own-vs-assembled arbitration is shared even when line directions differ.
        for j,d in enumerate(Q.TRAIN):
            f[(i,'own_asm')].add(d)
            f[(geo['partner'][i],'own_asm')].add(d+Q.V_ASM[i])
        footprints[i]=f
    forbidden={}
    for i in names:
        for j in names:
            if i==j:continue
            f=set()
            for resource in footprints[i].keys() & footprints[j].keys():
                # q_i+a = q_j+b is forbidden, therefore q_i-q_j = b-a.
                f.update(b-a for a in footprints[i][resource] for b in footprints[j][resource])
            forbidden[i,j]=f
    lower={i:sl[i]['root_rel'] for i in names}; nodes=0
    domains={i:set(range(lower[i],lower[i]+max_delay+1)) for i in names}
    def visit(domains,picked):
        nonlocal nodes
        nodes+=1
        if not domains:return picked
        i=min(domains,key=lambda n:(len(domains[n]),-sum(len(forbidden[n,j]) for j in domains if j!=n),sl[n]['sid']))
        for q in sorted(domains[i]):
            nxt={};valid=True
            for j,options in domains.items():
                if j==i:continue
                keep={r for r in options if q-r not in forbidden[i,j]}
                if not keep:valid=False;break
                nxt[j]=keep
            if valid:
                result=visit(nxt,{**picked,i:q})
                if result is not None:return result
        return None
    answer=visit(domains,{})
    doc=dict(max_delay=max_delay,search_nodes=nodes,calibration='Q_AFTER_ROOT common constant omitted; V_ASM=2+per-slice age',
             qualification='release-slot solution only; NORMR attainability and hardware release control NOT PROVEN')
    if answer is None:return dict(doc,verdict='NO_SOLUTION_WITHIN_BOUND')
    occ,cl,oa=Q.allgather(answer,geo)
    assert not cl and not oa
    return dict(doc,verdict='PREDICTED_RELEASE_SLOTS_PASS',line_collision_edges=len(cl),own_asm_same_edge=len(oa),
                releases={i:dict(sid=sl[i]['sid'],root_rel=lower[i],q_rel=answer[i],delay=answer[i]-lower[i]) for i in names},
                release_span=max(answer.values())-min(answer.values()),maximum_delay=max(answer[i]-lower[i] for i in names))


def main():
    p=argparse.ArgumentParser();p.add_argument('report');p.add_argument('--out',required=True);p.add_argument('--max-delay',type=int,default=512)
    a=p.parse_args();r=solve_report(json.loads(Path(a.report).read_text()),a.max_delay)
    Path(a.out).write_text(json.dumps(r,indent=1)+'\n');print(json.dumps(r,indent=1))
if __name__=='__main__':main()
