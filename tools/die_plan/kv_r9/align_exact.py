#!/usr/bin/env python3
"""Joint finite-domain lattice alignment. The R9 coordinate search starts all module
patterns empty, so a feasible solution requiring TWO nonempty patterns can never be
reached. This solver chooses every pattern and every core origin/orientation together.
It preserves order, outline and per-axis gaps; a complete 2-D candidate needs a final
core-overlap census before adoption. No plan is changed by this model.
"""
import argparse, json, math, sys
from collections import defaultdict
from pathlib import Path
import z3


def candidates(lines, extent, width, origin, quantum, maximum_move, offset_step=2.0, margin=5.):
    """Finite candidates keyed by the FULL reflected local site pattern, not its first site."""
    out={}
    offsets=[None]+[margin+i*offset_step for i in range(int((extent-2*margin)/offset_step)+1)]
    for u in offsets:
        if u is None:
            pp=[]
            for a,b in zip([-1e9]+lines,lines+[1e9]):
                lo=max(0.,a+margin);hi=min(width-extent,b-margin-extent)
                if lo<=hi:
                    pp += [(max(lo,min(hi,origin)),False),(lo,False),(hi,False)]
        else:
            pp=[(x-u,False) for x in lines]+[(x+u-extent,True) for x in lines]
        for p,flip in pp:
            p=round(round(p/quantum)*quantum,3)
            if not -1e-6<=p<=width-extent+1e-6 or abs(p-origin)>maximum_move:continue
            local=sorted((p+extent-x if flip else x-p) for x in lines if p-.5<=x<=p+extent+.5)
            if any(not margin<=v<=extent-margin for v in local):continue
            pattern=tuple(round(v*2)/2 for v in local)
            # Same 0.5-um site quantization used by the inherited census. Full-site
            # coordinate legality is checked again on the eventual mesh build.
            out[(p,flip,pattern)]=1
    return sorted(out)


def solve(P,M,family,axis,gap=20.,max_move=500.,core_grid=None):
    points=[tuple(d['ideal']) for d in M['drivers'].values()]
    ptypes=sorted(t for t in P.types if t.startswith(family) and P.types[t].get('hard_cores'))
    lat={}
    for part,p in P.parts.items():
        if p['type'] not in ptypes or p['type'] in lat:continue
        t=P.types[p['type']];w,h=t['outline_um'];loc=[P.to_type(part,q) for q in points]
        lat[p['type']]=sorted({round(q[axis],3) for q in loc if -500<=q[axis]<=t['outline_um'][axis]+500})
    # Equivalent partition variants impose identical constraints. Share those
    # variables exactly, then expand the result back to every type. This avoids
    # repeating hundreds of identical disjunctions without weakening a gate.
    groups={}
    for tn in ptypes:
        sig=(tuple(P.types[tn]['outline_um']),tuple(lat[tn]),tuple(sorted((c['inst'],c['module'],tuple(c['origin_um']),tuple(c['outline_um']),c.get('orient','R0')) for c in P.types[tn]['hard_cores'])))
        groups.setdefault(sig,[]).append(tn)
    aliases={ts[0]:ts for ts in groups.values()}
    ptypes=list(aliases)
    items=[]
    for tn in ptypes:
        groups=defaultdict(list)
        for hc in P.types[tn]['hard_cores']:
            groups[(round(hc['origin_um'][axis],3),hc['outline_um'][axis])].append(hc)
        for (old,e),hc in groups.items():
            cs=candidates(lat[tn],e,P.types[tn]['outline_um'][axis],old,core_grid or (.054,.27)[axis],max_move)
            if core_grid and core_grid < P.grid:
                cs=[c for c in cs if abs(c[0]-round(c[0]/P.grid)*P.grid)<2.16-1e-6]
            items.append(dict(type=tn,old=old,extent=e,cores=hc,candidates=cs))
    # Distinct hard-core modules that occupy the same coordinate/extent share a pattern.
    patterns=sorted({c[2] for it in items for c in it['candidates']})
    patid={p:i for i,p in enumerate(patterns)}
    mods={c['module'] for it in items for c in it['cores']};mv={m:z3.Int('m_'+m) for m in mods}
    s=z3.Solver(); pos=[];fl=[];delta=z3.Real('max_move')
    s.add(delta>=0)
    for i,it in enumerate(items):
        x=z3.Real('x_'+str(i)); f=z3.Bool('flip_'+str(i)); g=z3.Int('p_'+str(i));pos.append(x);fl.append(f)
        s.add(z3.Or(*[z3.And(x==z3.RealVal(str(p)),f==flip,g==patid[pat]) for p,flip,pat in it['candidates']]))
        for hc in it['cores']:s.add(g==mv[hc['module']])
        s.add(x-it['old']<=delta,it['old']-x<=delta)
    oa=1-axis
    for i,a in enumerate(items):
        for j in range(i):
            b=items[j]
            if a['type']!=b['type']:continue
            overlap=any(c['origin_um'][oa]<d['origin_um'][oa]+d['outline_um'][oa]-1e-6 and d['origin_um'][oa]<c['origin_um'][oa]+c['outline_um'][oa]-1e-6 for c in a['cores'] for d in b['cores'])
            if overlap:s.add(pos[j]+b['extent']+gap<=pos[i] if b['old']<a['old'] else pos[i]+a['extent']+gap<=pos[j])
    stat=s.check()
    out=dict(family=family,axis='xy'[axis],status=str(stat),gap_um=gap,site_quantum_um=.5,core_origin_quantum_um=core_grid,items=len(items),candidates=sum(len(it['candidates']) for it in items),checked='UNCHECKED')
    if stat!=z3.sat:return out
    best=s.model()
    # Feasibility first, then binary-search an upper bound in physical 0.27-um steps.
    hi=float(best.eval(delta).as_decimal(12).replace('?',''));lo=0.
    while hi-lo>.27:
        mid=(lo+hi)/2;s.push();s.add(delta<=mid);r=s.check()
        if r==z3.sat:best=s.model();hi=mid
        else:lo=mid
        s.pop()
    fv=lambda x:float(best.eval(x).as_decimal(12).replace('?',''))
    out.update(max_move_um=round(hi,3),patterns={m:list(patterns[best.eval(v).as_long()]) for m,v in mv.items()},placements=[dict(type=tn,cores=[c['inst'] for c in it['cores']],old=it['old'],new=fv(pos[i]),flip=z3.is_true(best.eval(fl[i]))) for i,it in enumerate(items) for tn in aliases[it['type']]])
    return out

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('build');ap.add_argument('tools');ap.add_argument('family');ap.add_argument('axis',choices=['x','y']);ap.add_argument('out');ap.add_argument('--gap',type=float,default=20.);ap.add_argument('--core-grid',type=float);a=ap.parse_args()
    sys.path.insert(0,a.tools);import schema as S
    P=S.Plan(S.load(str(Path(a.build)/'plan.json')));M=json.load(open(Path(a.build)/'mesh.json'))
    result=solve(P,M,a.family,'xy'.index(a.axis),a.gap,core_grid=a.core_grid);Path(a.out).write_text(json.dumps(result,indent=1)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ('patterns','placements')}))
