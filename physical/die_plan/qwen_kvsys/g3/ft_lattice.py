#!/usr/bin/env python3
"""Generate explicit per-bit Manhattan FT stations for a core-free KV soft type.

Every route starts at its input face, has paired register bands at each turn,
and ends beside its output face. Additional pipeline stages are reported and
must be priced/rebound by the batched plan owner before a kit is built.
"""
import argparse
import json
import math
from pathlib import Path
import ft_bit_sites_gen as F

REACH = 405.0
FACE = 12.0


def bundle_targets(A, B, fi, fo, W, H, extras=None):
    """Straight registered bands plus a two-band registered turn box.

    Each stage shares its travel-axis coordinate across every bit. The turn
    box is bounded by the complete input/output pin windows rather than by
    independently interpolating every bit's route.
    """
    n=len(A);out={i:[] for i in A};labels=[];leg_id=0;extras=extras or {}
    def span(a,b):return max(1,math.ceil(abs(b-a)/REACH))
    def band(axis,coord,which,label=-1):
        labels.append(label)
        for i in A:
            out[i].append((coord,which[i][1]) if axis=='x' else (which[i][0],coord))
    def leg(axis,a,b,which):
        nonlocal leg_id
        label=leg_id;leg_id+=1
        m=span(a,b)+extras.get(label,0)
        for j in range(1,m+1):band(axis,a+(b-a)*j/m,which,label)
    if (fi in 'EW') != (fo in 'EW'):
        if fi in 'EW':
            kx=(max(p[0] for p in B.values())+10) if fi=='E' else (min(p[0] for p in B.values())-10)
            ky=(max(p[1] for p in A.values())+10) if fo=='N' else (min(p[1] for p in A.values())-10)
            leg('x',W-FACE if fi=='E' else FACE,kx,A)
            band('y',ky,B)
            leg('y',ky,H-FACE if fo=='N' else FACE,B)
        else:
            ky=(max(p[1] for p in B.values())+10) if fi=='N' else (min(p[1] for p in B.values())-10)
            kx=(max(p[0] for p in A.values())+10) if fo=='E' else (min(p[0] for p in A.values())-10)
            leg('y',H-FACE if fi=='N' else FACE,ky,A)
            band('x',kx,B)
            leg('x',kx,W-FACE if fo=='E' else FACE,B)
    else:
        # Opposite faces: two central registered columns/rows bound the jog.
        ew=fi in 'EW';extent=W if ew else H
        x1=extent/2+(50 if fi in 'EN' else -50);x2=extent-x1
        leg('x' if ew else 'y',extent-FACE if fi in 'EN' else FACE,x1,A)
        av=[p[1 if ew else 0] for p in A.values()];bv=[p[1 if ew else 0] for p in B.values()]
        lo,hi=min(av+bv),max(av+bv)
        if hi-lo+100>REACH:
            # Shared orthogonal rows between the windows keep each registered
            # span below reach; bit lanes occupy distinct ordered tracks.
            mids=max(1,math.ceil((hi-lo)/(REACH-100)))
            order=sorted(A,key=lambda i:A[i][1 if ew else 0])
            for j in range(1,mids+1):
                c=lo+(hi-lo)*j/(mids+1)
                labels.append(-1)
                for r,i in enumerate(order):
                    v=x1+(x2-x1)*(r+.5)/n
                    out[i].append((v,c) if ew else (c,v))
        band('x' if ew else 'y',x2,B)
        leg('x' if ew else 'y',x2,extent-FACE if fo in 'EN' else FACE,B)
    return out,labels


def apply(raw, tn, pins):
    t=raw['partition_types'][tn];W,H=t['outline_um']
    if t.get('hard_cores') or t.get('contents') or t.get('internal_stations'):
        raise ValueError('FT-only type without preallocated internal stations required; preserve occupied corridors separately')
    by={}
    for p in pins:by.setdefault(p['bus'],{})[p['bit']]=(p['x'],p['y'])
    F.FACE_KEEP_UM=7.0
    sites=F.Sites(W,H,[])
    report=dict(type=tn,cell_um=list(F.CELL),reach_target_um=REACH,slots=[],sampled_routes=[])
    for s in sorted(t['ft_slots'],key=lambda s:-s['width']):
        name=s['name'];A=by[name+'_i'];B=by[name+'_o'];n=s['width']+1
        if set(A)!=set(range(n)) or set(B)!=set(range(n)):raise ValueError(f'{name}: incomplete pins')
        fi,fo=s['in_face'],s['out_face'];axis=1 if fi in 'EW' else 0
        order=sorted(range(n),key=lambda i:A[i][axis]);rank={i:j for j,i in enumerate(order)}
        used_before=set(sites.used);extras={};trials=[]
        while True:
            sites.used=set(used_before)
            targets_by_bit,labels=bundle_targets(A,B,fi,fo,W,H,extras)
            old=int(s.get('stations',1));k=len(targets_by_bit[0])+1
            if k<old:raise ValueError(f'{name}: refusing to shorten an existing pipeline')
            stages=[[None]*n for _ in range(k-1)];maxhop=maxout=maxdisp=0.0;worst_index=None;draw=[]
            for i in order:
                targets=targets_by_bit[i]
                assert len(targets)==k-1
                placed=[]
                for j,target in enumerate(targets):
                    prev=targets[max(0,j-1)];horiz=abs(target[1]-prev[1])<1e-7
                    xy=sites.take(*target,horiz=horiz)
                    c=(xy[0]+F.CELL[0]/2,xy[1]+F.CELL[1]/2)
                    stages[j][i]=list(xy);placed.append(c);maxdisp=max(maxdisp,F.man(c,target))
                hops=[F.man(a,b) for a,b in zip([A[i]]+placed,placed+[B[i]])]
                if max(hops)>maxhop:maxhop=max(hops);worst_index=hops.index(maxhop)
                maxout=max(maxout,F.man(placed[-1],B[i]))
                if i%32==0:draw.append(dict(slot=name,bit=i,path=[A[i]]+targets+[B[i]],sites=placed))
            if maxout>20+1e-6:
                raise ValueError(f'{name}: output packing exceeds20um ({maxout:.3f}); add face capacity')
            if maxhop<=REACH+1e-6:break
            label=labels[worst_index] if worst_index<len(labels) else -1
            trials.append(dict(stations=k,max_hop_um=maxhop,failed_leg=label))
            if label<0:
                raise ValueError(f'{name}: registered turn box exceeds405um ({maxhop:.3f}); revise its channel')
            extras[label]=extras.get(label,0)+1
        report['sampled_routes'].extend(draw)
        s.update(stations=k,bit_sites_um=stages,bit_site_cell_um=list(F.CELL));s.pop('regs_um',None)
        report['slots'].append(dict(slot=name,bits=n,before=old,after=k,added_cycles=k-old,max_hop_um=maxhop,max_out_hop_um=maxout,max_displacement_um=maxdisp,actual_reach_repairs=trials))
    report.update(sites=len(sites.used),max_hop_um=max(s['max_hop_um'] for s in report['slots']),max_out_hop_um=max(s['max_out_hop_um'] for s in report['slots']))
    return report


def main():
    ap=argparse.ArgumentParser();ap.add_argument('plan');ap.add_argument('type');ap.add_argument('pins');ap.add_argument('out');ap.add_argument('--report',required=True)
    a=ap.parse_args();raw=json.loads(Path(a.plan).read_text());pins=json.loads(Path(a.pins).read_text());r=apply(raw,a.type,pins)
    Path(a.out).write_text(json.dumps(raw,indent=1)+'\n');Path(a.report).write_text(json.dumps(r,indent=1)+'\n')
    print(json.dumps({k:v for k,v in r.items() if k!='sampled_routes'}))

if __name__=='__main__':main()
