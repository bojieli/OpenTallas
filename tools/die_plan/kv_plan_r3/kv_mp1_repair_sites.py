#!/usr/bin/env python3
"""Re-site moved KV MP1 FT registers with the same priced station counts.

Moving a face window does not make translated per-bit register sites legal.
For each affected bit, solve a macro-free reach-bounded chain and allocate
actual row footprints. Existing legal sites are occupied, not reused. A slot
that cannot keep its old register depth remains unchanged and is reported
FAIL; no added latency is hidden in this geometric post-pass.
"""
import argparse
import copy
import json
import sys
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tools/die_plan'))
import schema as S
import ft_sites_unblock as U
from gen_phys import type_pins
from tools.die_trial.legal_sites import RowAllocator


def overlap(x,y,cw,ch,boxes):
    return any(x < c and x+cw > a and y < d and y+ch > b for a,b,c,d in boxes)



def allocate_between(al,target,prev,nxt):
    """Nearest unoccupied row footprint inside BOTH exact405um hop diamonds."""
    import math
    lo=max(al.ix0,math.ceil((max(prev[0],nxt[0])-405-al.ox-al.cw/2)/al.cp))
    hi=min(al.ix1,math.floor((min(prev[0],nxt[0])+405-al.ox-al.cw/2)/al.cp))
    ly=max(al.iy0,math.ceil((max(prev[1],nxt[1])-405-al.oy-al.ch/2)/al.rp))
    hy=min(al.iy1,math.floor((min(prev[1],nxt[1])+405-al.oy-al.ch/2)/al.rp))
    ix,iy=np.meshgrid(np.arange(lo,hi+1),np.arange(ly,hy+1));ix=ix.ravel();iy=iy.ravel()
    x=al.ox+ix*al.cp+al.cw/2;y=al.oy+iy*al.rp+al.ch/2;ids=(iy-al.iy0)*al.nx+ix-al.ix0
    ok=(np.abs(x-prev[0])+np.abs(y-prev[1])<=405.+1e-7)&(np.abs(x-nxt[0])+np.abs(y-nxt[1])<=405.+1e-7)
    for a,b,c,d in al.blocks:ok &= ~((x-al.cw/2<c-1e-8)&(x+al.cw/2>a+1e-8)&(y-al.ch/2<d-1e-8)&(y+al.ch/2>b+1e-8))
    ok &= np.fromiter((int(i) not in al.used for i in ids),bool,count=len(ids))
    valid=np.flatnonzero(ok)
    if not len(valid):raise ValueError('no free row footprint within both405um hop diamonds')
    cost=np.abs(x[valid]-target[0])+np.abs(y[valid]-target[1]);j=valid[np.lexsort((ids[valid],cost))[0]]
    al.used.add(int(ids[j]));return np.array([[x[j],y[j]]])


def repair(raw):
    P=S.Plan(raw); report=[]
    for tn,ty in raw['partition_types'].items():
        slots=[s for s in ty.get('ft_slots',[]) if s.get('bit_sites_um')]
        if not slots:continue
        boxes=list(S.placed_macro_boxes(ty,halo=0).values())
        if not boxes:continue
        W,H=ty['outline_um'];U.FRAME[:]=[W,H]
        pins={}
        for bus,bit,_l,x,y,face in type_pins(P,tn):pins.setdefault(bus,{})[bit]=(x,y,face)
        badslots=[]
        for s in slots:
            cw,ch=s['bit_site_cell_um'];hits=sum(overlap(x,y,cw,ch,boxes) for st in s['bit_sites_um'] for x,y in st)
            if hits:badslots.append((s,hits))
        if not badslots:continue
        grow=[(a-4.32,b-4.32,c+4.32,d+4.32) for a,b,c,d in boxes]
        # Reserve every surviving physical register once; a failed re-site never frees it.
        al=RowAllocator((4.32,4.32,W-4.32,H-4.32),blocked=grow,cell_size=U.CELL,column_pitch=2.16,row_pitch=.27,origin=(4.32,4.32))
        for s in slots:
            cw,ch=s['bit_site_cell_um']
            for st in s['bit_sites_um']:
                for x,y in st:
                    if not overlap(x,y,cw,ch,boxes):al.reserve_rectangle((x,y,x+cw,y+ch))
        g=np.mgrid[8.64:W-4.32:2.16,8.64:H-4.32:2.16].reshape(2,-1).T
        ok=np.ones(len(g),bool)
        for a,b,c,d in grow:ok &= ~((g[:,0]>a)&(g[:,0]<c)&(g[:,1]>b)&(g[:,1]<d))
        free=g[ok]
        for s,hits in badslots:
            old=copy.deepcopy(s);cw,ch=s['bit_site_cell_um'];name=s['name'];k=s['stations'];pts={}
            try:
                for bit in range(s['width']+1):
                    A,B=pins[name+'_i'][bit],pins[name+'_o'][bit]
                    inset=lambda p: {'E':(p[0]-1,p[1]),'W':(p[0]+1,p[1]),'N':(p[0],p[1]-1),'S':(p[0],p[1]+1)}[p[2]]
                    a,b=inset(A),inset(B);r=U.C.zroute(a,b,A[2],B[2]);ps=[(st[bit][0]+cw/2,st[bit][1]+ch/2) for st in s['bit_sites_um']]
                    pts[bit]=(a,b,r,U.C.plen(r),ps)
                moved=U._move(pts,list(pts),k,grow,free,395.,tn,name)
                # A moved endpoint can invalidate otherwise macro-free old
                # stations. Re-solve that bit at the same depth as well.
                for bit,(a,b,r,L,ps) in list(pts.items()):
                    chain=[a,*ps,b]
                    if max(U.man(u,v) for u,v in zip(chain,chain[1:]))>395.:
                        pts[bit]=(a,b,r,L,U.layered(a,b,ps,k,grow,395.,tn,name,bit))
                new=copy.deepcopy(s['bit_sites_um'])
                for bit,(a,b,r,L,ps) in pts.items():
                    for stage,p in enumerate(ps):
                        x,y=old['bit_sites_um'][stage][bit]
                        if overlap(x,y,cw,ch,boxes) or abs(x+cw/2-p[0])+abs(y+ch/2-p[1])>1e-5:
                            try:q,_=al.allocate(np.array(p),1,max_radius_um=12.)
                            except ValueError:
                                prev=a if stage==0 else (new[stage-1][bit][0]+cw/2,new[stage-1][bit][1]+ch/2)
                                nxt=b if stage==len(ps)-1 else ps[stage+1]
                                q=allocate_between(al,p,prev,nxt)
                            new[stage][bit]=[round(float(q[0][0]-cw/2),6),round(float(q[0][1]-ch/2),6)]
                worst=0.
                for bit,(a,b,*_) in pts.items():
                    chain=[a,*[(st[bit][0]+cw/2,st[bit][1]+ch/2) for st in new],b]
                    worst=max(worst,max(U.man(a,b) for a,b in zip(chain,chain[1:])))
                if worst>405.+1e-6:raise ValueError(f'actual paired-bit hop {worst:.3f}>405')
                if any(overlap(x,y,cw,ch,boxes) for st in new for x,y in st):raise ValueError('footprint remains inside macro')
                s['bit_sites_um']=new
                row=dict(type=tn,slot=name,status='PASS',repaired_hits=hits,moved=moved,stations=k,max_hop_um=worst,added_cycles=0)
            except (ValueError,SystemExit) as e:
                s.clear();s.update(old);row=dict(type=tn,slot=name,status='FAIL',original_macro_hits=hits,reason=str(e),added_cycles=0)
            report.append(row);print(json.dumps(row),flush=True)
    return report


def main():
    ap=argparse.ArgumentParser(description=__doc__.splitlines()[0]);ap.add_argument('plan');ap.add_argument('--out',required=True);ap.add_argument('--report',required=True);a=ap.parse_args()
    raw=json.loads(Path(a.plan).read_text());rows=repair(raw)
    Path(a.out).write_text(json.dumps(raw,indent=1)+'\n');Path(a.report).write_text(json.dumps(rows,indent=1)+'\n')
    print(f"REPAIR slots={len(rows)} PASS={sum(x['status']=='PASS' for x in rows)} FAIL={sum(x['status']=='FAIL' for x in rows)}",flush=True)

if __name__=='__main__':main()
