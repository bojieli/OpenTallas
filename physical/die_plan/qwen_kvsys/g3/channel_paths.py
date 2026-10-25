#!/usr/bin/env python3
"""Route KV feedthrough centroids in hard-core-free channels; publish station/cycle proposal.

A station is placed at every bend so no implied rectilinear station-to-station
leg crosses a core.  This is a plan proposal, not a replacement for per-bit GRT.
Latency/R8 must be regenerated before adopting the emitted plan.
"""
import argparse
import heapq
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3] / 'tools/die_plan'))
import check as C
import schema as S
from gen_phys import type_pins

CLEAR = 8.64
REACH = 405.0

def boxes(t):
    out=[]
    for c in t.get('hard_cores',[]):
        dx,dy=c.get('track_offset_um',[0.,0.])
        x,y=c['origin_um'][0]+dx,c['origin_um'][1]+dy
        out.append((x-CLEAR,y-CLEAR,x+c['outline_um'][0]+CLEAR,y+c['outline_um'][1]+CLEAR))
    return out

def blocked(a,b,obs):
    if abs(a[0]-b[0]) < 1e-5:
        return any(x0+1e-5<a[0]<x1-1e-5 and max(min(a[1],b[1]),y0)<min(max(a[1],b[1]),y1)-1e-5 for x0,y0,x1,y1 in obs)
    if abs(a[1]-b[1]) < 1e-5:
        return any(y0+1e-5<a[1]<y1-1e-5 and max(min(a[0],b[0]),x0)<min(max(a[0],b[0]),x1)-1e-5 for x0,y0,x1,y1 in obs)
    raise ValueError('non-rectilinear segment')

def legal_hop(a,b,obs):
    # Either L is usable if the physical router chooses that bend.
    return any(not blocked(a,c,obs) and not blocked(c,b,obs)
               for c in ((a[0],b[1]),(b[0],a[1])))

def compact(points):
    out=[]
    for p in points:
        if out and p==out[-1]: continue
        if len(out)>1 and ((abs(out[-2][0]-out[-1][0])<1e-5 and abs(out[-1][0]-p[0])<1e-5) or
                           (abs(out[-2][1]-out[-1][1])<1e-5 and abs(out[-1][1]-p[1])<1e-5)):
            out[-1]=p
        else: out.append(p)
    return out

def route(a,b,t,obs):
    W,H=t['outline_um']
    # Gap centres avoid skimming macros and leave physical room for the bundle.
    xb=sorted({0.0,W,*[v for o in obs for v in (max(0.,o[0]),min(W,o[2]))]})
    yb=sorted({0.0,H,*[v for o in obs for v in (max(0.,o[1]),min(H,o[3]))]})
    xs=sorted({a[0],b[0],*[round((u+v)/2,6) for u,v in zip(xb,xb[1:])]})
    ys=sorted({a[1],b[1],*[round((u+v)/2,6) for u,v in zip(yb,yb[1:])]})
    start=(xs.index(a[0]),ys.index(a[1]),0)
    goal=(xs.index(b[0]),ys.index(b[1]))
    dist={start:0.}; prev={}; q=[(0.,start)]
    while q:
        cost,state=heapq.heappop(q)
        if cost != dist[state]: continue
        i,j,d=state
        if (i,j)==goal:
            path=[]
            while True:
                path.append((xs[state[0]],ys[state[1]]))
                if state==start: break
                state=prev[state]
            return compact(list(reversed(path)))
        p=(xs[i],ys[j])
        for ni,nj,nd in ((i-1,j,1),(i+1,j,1),(i,j-1,2),(i,j+1,2)):
            if not (0<=ni<len(xs) and 0<=nj<len(ys)): continue
            np=(xs[ni],ys[nj])
            if blocked(p,np,obs): continue
            nc=cost+abs(p[0]-np[0])+abs(p[1]-np[1])+(40 if d and d!=nd else 0)
            ns=(ni,nj,nd)
            if nc<dist.get(ns,float('inf')):
                dist[ns]=nc;prev[ns]=state;heapq.heappush(q,(nc,ns))
    return None

def stations(path,min_count,tail_span=0.0):
    pts=[]
    for i,(a,b) in enumerate(zip(path,path[1:])):
        budget=REACH-tail_span if i==len(path)-2 else REACH
        if budget<=0: raise ValueError("output pin span exceeds one registered hop")
        n=max(1,math.ceil((abs(a[0]-b[0])+abs(a[1]-b[1]))/budget-1e-8))
        pts.extend([(a[0]+(b[0]-a[0])*i/n,a[1]+(b[1]-a[1])*i/n) for i in range(n)])
    while len(pts)<min_count:
        seq=pts+[path[-1]]
        j=max(range(len(pts)),key=lambda j:abs(seq[j][0]-seq[j+1][0])+abs(seq[j][1]-seq[j+1][1]))
        pts.insert(j+1,((seq[j][0]+seq[j+1][0])/2,(seq[j][1]+seq[j+1][1])/2))
    return [[round(x,6),round(y,6)] for x,y in pts]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('plan');ap.add_argument('out');ap.add_argument('--types',nargs='*');a=ap.parse_args()
    raw=json.load(open(a.plan));P=S.Plan(raw);report={'types':{},'failed':[],'changed':[],'retained_slots':0,'baseline_blocked_bits':0}
    for tn,t in raw['partition_types'].items():
        if not t.get('hard_cores') or not t.get('ft_slots') or a.types and tn not in a.types: continue
        obs=boxes(t);bt=C._bus_targets(P,tn);tr=[]
        pinxy={}
        for bus,bit,layer,x,y,face in type_pins(P,tn):pinxy.setdefault(bus,[]).append((x,y))
        for s in t['ft_slots']:
            aa=bt.get(s['name']+'_i');bb=bt.get(s['name']+'_o')
            if not aa or not bb: continue
            p,q=tuple(aa[1]),tuple(bb[1]);oldk=s['stations']
            seg=C.zroute(p,q,s.get('in_face','W'),s.get('out_face','E'))
            oldst=[tuple(v) for v in s.get('regs_um',[])] or [C.point_at(seg,C.plen(seg)*j/oldk) for j in range(oldk)]
            oldseq=oldst+[q]
            outbits=pinxy.get(s['name']+'_o',[])
            tail_span=max((C.plen([q,v]) for v in outbits),default=0)
            tail_hop=max((C.plen([oldst[-1],v]) for v in outbits),default=0)
            hazardous=tail_hop>REACH+1e-6 or any(not legal_hop(u,v,obs) for u,v in zip(oldseq,oldseq[1:]))
            if not hazardous:
                report['retained_slots']+=1
                continue
            report['baseline_blocked_bits']+=s['width']
            path=route(p,q,t,obs)
            if path is None:
                report['failed'].append([tn,s['name']]);continue
            st=stations(path,oldk,tail_span)
            s['regs_um']=st;s['stations']=len(st)
            rec={'slot':s['name'],'width':s['width'],'stations':[oldk,len(st)],'path':path,'length_um':C.plen(path),'max_hop_um':max(C.plen([u,v]) for u,v in zip(st,st[1:]+[q])),
                 'worst_output_bit_hop_um':max((C.plen([st[-1],v]) for v in outbits),default=0)}
            tr.append(rec)
            if oldk!=len(st): report['changed'].append({'type':tn,**rec})
        report['types'][tn]=tr
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    (out/'die_plan.json').write_text(json.dumps(raw,indent=1)+'\n')
    (out/'channel_paths.json').write_text(json.dumps(report,indent=1)+'\n')
    print(json.dumps({'types':len(report['types']),'changed_slots':len(report['changed']),'failed_slots':len(report['failed']),'added_type_slot_cycles':sum(r['stations'][1]-r['stations'][0] for r in report['changed'])}))
    if report['failed']:raise SystemExit(1)

if __name__=='__main__':main()
