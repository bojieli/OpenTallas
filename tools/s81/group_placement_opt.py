#!/usr/bin/env python3
"""Screen rigid group moves using actual pins; never certify a physical layout.

A plan is pin_align JSON (full Inst or compact rows). Every selected group is
moved as a unit. All incident buses count, including edges that get longer.
The output is a reproducible placement patch, not an adopted floorplan.
"""
import argparse
import copy
import gzip
import hashlib
import itertools
import json
import math
from pathlib import Path
import sys
import types
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hier_contract'))
import pin_align as PA


def read(path):
    raw=path.read_bytes()
    return gzip.decompress(raw).decode() if path.suffix=='.gz' else raw.decode()


def intersects(a,b,halo):
    return a[0] < b[0]+b[2]+halo-1e-6 and a[0]+a[2]+halo > b[0]+1e-6 and a[1] < b[1]+b[3]+halo-1e-6 and a[1]+a[3]+halo > b[1]+1e-6


class Model:
    def __init__(self, plan, lefs, die, halo=20., reach=500.):
        self.plan,self.die,self.halo,self.reach=plan,die,halo,reach
        self.pins=PA.read_pins(lefs)
        self.insts={}
        for r in plan['insts']:
            full=len(r)>=7
            w,h=(r[4],r[5]) if full else self.pins[r[1]][:2]
            self.insts[r[0]]=types.SimpleNamespace(name=r[0],master=r[1],x=r[2],y=r[3],w=w,h=h,orient=r[6] if full else r[4])
        self.edges=[]; self.missing=[]
        for bus,cls,bits,ends in plan['buses']:
            if cls in PA.EXEMPT_CLS or len(ends)<2: continue
            for dst in ends[1:]:
                e=dict(bus=bus,cls=cls,bits=bits,ends=[ends[0],dst])
                try:
                    e['points']=[self.points(n,p,bits) for n,p in e['ends']]
                    if any(len(v)!=bits for v in e['points']):raise ValueError('pin count does not match bus width')
                except (KeyError,ValueError) as ex:
                    self.missing.append(dict(bus=bus,ends=e['ends'],error=str(ex))); continue
                self.edges.append(e)

    def points(self,n,port,bits):
        it=self.insts[n];w,h,pp=self.pins[it.master]
        if abs(w-it.w)>0.002 or abs(h-it.h)>0.002:raise ValueError('LEF and placement outline disagree')
        names=self.plan.get('pins',{}).get(n+'|'+port)
        if names is None:
            part=PA._PSL.match(port);base=part.group(1) if part else port;lo=int(part.group(2)) if part else 0
            alias=self.plan.get('port_aliases',{}).get(it.master,{}).get(base)
            names=alias[lo:lo+bits] if alias is not None else PA.default_names(n,port,bits)
        return [PA.place(it,w,h,pp[k]) for k in names]

    def legal(self,moves):
        # Only changed-to-unchanged or differently moved pairs need checking.
        boxes={n:(it.x+moves.get(n,(0,0))[0],it.y+moves.get(n,(0,0))[1],it.w,it.h) for n,it in self.insts.items()}
        for n in moves:
            x,y,w,h=boxes[n]
            if x<self.halo-1e-6 or y<self.halo-1e-6 or x+w>self.die[0]-self.halo+1e-6 or y+h>self.die[1]-self.halo+1e-6:return False
            for m in boxes:
                if n==m or moves.get(n)==moves.get(m):continue
                if intersects(boxes[n],boxes[m],self.halo):return False
        return True

    def metrics(self,edges,moves=None):
        moves=moves or {}; total=0.;worst=0.;fail=0;extra=0;over=0;routes=[]
        for e in edges:
            aa,bb=([tuple(v+delta for v,delta in zip(p[:2],moves.get(n,(0,0))))+tuple(p[2:]) for p in ps] for (n,_),ps in zip(e['ends'],e['points']))
            ll=[abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(aa,bb)]
            s=sum(ll);mx=max(ll);q=PA.bundle(aa,bb)
            total+=s;worst=max(worst,mx);fail+=q['verdict']=='FAIL';over+=sum(v>self.reach+1e-6 for v in ll)
            extra+=e['bits']*max(0,math.ceil(mx/self.reach)-1)
            routes.append(dict(bus=e['bus'],ends=e['ends'],bits=e['bits'],sum_bit_um=s,max_um=mx,alignment=q))
        return dict(sum_bit_um=total,max_um=worst,alignment_failures=fail,over_reach_bits=over,relay_bit_stage_lower_bound=extra,
                    top20_routes=sorted(routes,key=lambda x:x['sum_bit_um'],reverse=True)[:20])

    def proposal(self,label,moves):
        if not self.legal(moves):return None
        incident=[e for e in self.edges if any(n in moves for n,_ in e['ends'])]
        missing=[e for e in self.missing if any(n in moves for n,_ in e['ends'])]
        if missing or not incident:return None # Never optimize a favorable subset of a group.
        before=self.metrics(incident);after=self.metrics(incident,moves)
        if after['sum_bit_um']>=before['sum_bit_um']-1e-6:return None
        regressions=[k for k in ['alignment_failures','over_reach_bits','relay_bit_stage_lower_bound'] if after[k]>before[k]]
        return dict(label=label,before=before,after=after,saved_bit_um=before['sum_bit_um']-after['sum_bit_um'],
                    geometric_regressions=regressions,
                    moves={n:list(d) for n,d in sorted(moves.items())},
                    placement_patch=[dict(instance=n,x_um=self.insts[n].x+d[0],y_um=self.insts[n].y+d[1],orientation=self.insts[n].orient) for n,d in sorted(moves.items())],
                    status='GEOMETRIC_PROPOSAL_ONLY: no aggregate cuts/obstacle-aware wire paths/clock delivery or routing/timing proof')


def search(model,groups,radius,step):
    out=[];blocked=[];tradeoffs=[]
    for label,names in groups.items():
        if any(any(n in names for n,_ in e['ends']) for e in model.missing):
            blocked.append(label);continue
        best=None
        extent=int(radius//step)
        for ix,iy in itertools.product(range(-extent,extent+1),repeat=2):
            if ix==iy==0:continue
            p=model.proposal(label,{n:(ix*step,iy*step) for n in names})
            if p and p['geometric_regressions']:
                tradeoffs.append(p);continue
            if p and (best is None or p['saved_bit_um']>best['saved_bit_um']):best=p
        if best:out.append(best)
    for (la,aa),(lb,bb) in itertools.combinations(groups.items(),2):
        if set(aa)&set(bb):continue
        xa=min(model.insts[n].x for n in aa);ya=min(model.insts[n].y for n in aa)
        xb=min(model.insts[n].x for n in bb);yb=min(model.insts[n].y for n in bb)
        moves={**{n:(xb-xa,yb-ya) for n in aa},**{n:(xa-xb,ya-yb) for n in bb}}
        p=model.proposal(la+' <-> '+lb,moves)
        if p and p['geometric_regressions']:tradeoffs.append(p)
        elif p:out.append(p)
    return sorted(out,key=lambda p:p['saved_bit_um'],reverse=True),blocked,sorted(tradeoffs,key=lambda p:p['saved_bit_um'],reverse=True)[:20]


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan',type=Path);ap.add_argument('--lef',type=Path,action='append',required=True)
    ap.add_argument('--group',action='append',required=True,help='LABEL=instance_prefix[,prefix...]')
    ap.add_argument('--die',type=float,nargs=2,required=True);ap.add_argument('--halo',type=float,default=20.)
    ap.add_argument('--reach',type=float,default=500.);ap.add_argument('--radius',type=float,default=400.)
    ap.add_argument('--step',type=float,default=86.4);ap.add_argument('--scope',choices=['canonical','diagnostic'],required=True)
    ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    if a.step<=0 or a.radius<0 or a.halo<0 or a.reach<=0:ap.error('invalid geometry bounds')
    plan=json.loads(read(a.plan));model=Model(plan,[read(p) for p in a.lef],a.die,a.halo,a.reach)
    groups={}
    for spec in a.group:
        name,pp=spec.split('=',1);prefixes=pp.split(',')
        names=[n for n in model.insts if any(n.startswith(p) for p in prefixes)]
        if not names:ap.error('empty group '+name)
        groups[name]=names
    candidates,blocked,tradeoffs=search(model,groups,a.radius,a.step)
    files=[a.plan,*a.lef]
    report=dict(schema='opentallas.s81.group_geometry.v1',scope=a.scope,
                input_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
                die_um=a.die,halo_um=a.halo,reach_lower_bound_um=a.reach,groups=groups,
                missing=model.missing,groups_blocked_by_missing_pins=blocked,baseline=model.metrics(model.edges),
                candidates=candidates,tradeoffs_with_geometric_regressions=tradeoffs,
                limitations=['Candidates are independent alternatives, not cumulative patches',
                             'Bit-distance is unweighted by traffic or schedule criticality',
                             '500um stage counts are lower bounds; source pin timing can reduce reach',
                             'Clock and reset positions translate too; delivered phases must be regenerated',
                             'Actual LEF routing obstructions and aggregate cut capacity not checked',
                             'Canonical scope is caller-declared and must be verified against2417/BF519/PHW10/81stages'])
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,indent=1)+'\n')
    print(json.dumps(dict(edges=len(model.edges),missing=len(model.missing),candidates=len(candidates),blocked=blocked)))
if __name__=='__main__':main()
