#!/usr/bin/env python3
"""Exhaustive software NORMR shift feasibility on a compiled NX schedule.

Enumerates a relaxed superset of legal programmes: preserves five consecutive
leaf issues and forbids NX/CTL collisions, but lets non-NORMR commands move.
Therefore exhaustive no-solution proves no software fix within the stated shift
bound; a found candidate still needs normal compiler validation. No RTL change.
"""
import argparse
import json
import re
from pathlib import Path
import norm_q as Q


def run(schedule,report,bound,out,fast_lib=None):
    sl=report['slices']; names=sorted(sl,key=lambda n:sl[n]['sid']); bysid={sl[i]['sid']:i for i in names}
    pos={i:(sl[i]['sid']>>1,sl[i]['sid']&1) for i in names};byct={v:k for k,v in pos.items()}
    geo=dict(pos=pos,partner={i:byct[(c,1-t)] for i,(c,t) in pos.items()},age={(i,s):report['line_age'][i+'.'+s] for i in names for s in ('e','w') if i+'.'+s in report['line_age']})
    Q.V_ASM={i:2+report['v_age'][i] for i in names}
    en=schedule['smoke']['entry_norm']; old=en['g_shift']; G=en['G'];smoke=schedule['smoke']['slice']
    words=[]
    for e in schedule['events']:
        m=re.fullmatch(r'attn\.nx\.o(\d+)\.h(\d+)',e.get('tag',''))
        if not m:continue
        origin,h=map(int,m.groups());inst=e['inst'];col,tier=pos[inst]
        if e['port']=='vo':dst=geo['partner'][inst];age=report['v_age'][inst]
        else:
            side='e' if e['port']=='ro_e' else 'w'
            dst=byct[(col+(1 if side=='e' else -1),tier)];age=geo['age'][inst,side]
        words.append(dict(inst=inst,port=e['port'],edge=e['cycle'],hops=h,origin=origin,dst=dst,land=e['cycle']+age,own=inst==bysid[origin] and h in (8,7)))
    base=Q.arrivals(words); roots={i:Q.finish_root(base[i]) for i in names}
    assert all(roots[i]==sl[i]['root_wb'] for i in names),(roots,sl)
    finish=Q.finish_root
    if fast_lib:
        import ctypes
        library=ctypes.CDLL(str(Path(fast_lib).resolve()))
        compiled=library.norm_finish_root
        compiled.argtypes=[ctypes.POINTER(ctypes.c_int)];compiled.restype=ctypes.c_int
        def finish(dl):
            result=compiled((ctypes.c_int*16)(*(dl[5*i] for i in range(16))))
            if result<0:raise ValueError('compiled finisher did not complete')
            return result
        assert all(finish(base[i])==roots[i] for i in names)
    options={}
    for i in names:
        options[i]=[]
        for d in ([0] if i==smoke else range(bound+1)):
            shift=d-old.get(i,0);sid=sl[i]['sid'];tier=sid&1
            keys={(w['inst'],w['port'],w['edge']+shift) for w in words if w['origin']==sid}
            issue=G+d-en['lat'][i]
            keys.update((tier,'CTL',issue-k) for k in range(5))
            options[i].append((d,keys))
    nodes=complete=0;best=None;best_score=10**9
    def save(verdict,candidate=None):
        doc=dict(verdict=verdict,shift_max=bound,search_nodes=nodes,complete_candidates=complete,best_collision_score=best_score,best=best,
                 scope='relaxed superset: non-NORMR commands movable; provisionalV_ASM2+age; exhaustive only for stated shift bound')
        if candidate is not None:doc['candidate']=candidate
        Path(out).write_text(json.dumps(doc,indent=1)+'\n')
    def evaluate(picked):
        nonlocal complete,best,best_score
        complete+=1
        if complete%10000==0:print('PROGRESS',nodes,complete,best_score,flush=True);save('SEARCHING')
        delta={sl[i]['sid']:d-old.get(i,0) for i,d in picked.items()}
        root={i:finish({b:a+delta[b//5] for b,a in base[i].items()}) for i in names}
        _,cl,oa=Q.allgather(root,geo);score=len(cl)+len(oa)
        if score<best_score:
            best_score=score;best=dict(shifts=picked,line_collision_edges=len(cl),own_asm_same_edge=len(oa),root_spread=max(root.values())-min(root.values()))
            print('BEST',complete,best_score,best,flush=True);save('SEARCHING')
        return score==0
    def visit(domains,picked):
        nonlocal nodes
        nodes+=1
        if not domains:return picked if evaluate(picked) else None
        i=min(domains,key=lambda n:(len(domains[n]),sl[n]['sid']))
        for d,keys in domains[i]:
            nxt={};valid=True
            for j,opts in domains.items():
                if i==j:continue
                keep=[(e,k) for e,k in opts if keys.isdisjoint(k)]
                if not keep:valid=False;break
                nxt[j]=keep
            if valid:
                sol=visit(nxt,{**picked,i:d})
                if sol is not None:return sol
        return None
    answer=visit(options,{})
    save('SOFTWARE_CANDIDATE_FOUND' if answer is not None else 'NO_SOFTWARE_SOLUTION_WITHIN_BOUND',answer)
    print(Path(out).read_text(),flush=True)

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('schedule');a.add_argument('report');a.add_argument('--out',required=True);a.add_argument('--shift-max',type=int,default=6);a.add_argument('--fast-lib')
    p=a.parse_args();run(json.loads(Path(p.schedule).read_text()),json.loads(Path(p.report).read_text()),p.shift_max,p.out,p.fast_lib)
