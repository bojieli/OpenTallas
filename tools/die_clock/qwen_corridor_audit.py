#!/usr/bin/env python3
"""Audit one failed strict clock corridor against actual hard rectangles.

This is a geometry witness, never a routing/placement waiver. Only reset repeater
cells gain exact sub-grid placement bays; every hard rectangle remains forbidden
to clock cells. Existing clock/std-cell occupancy still needs the actual ODB.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hbm_die_v15'))
from die_clock_tree import Grid, GRID

XP, YP = 1.620, 0.270


def overlap(a,b):
    return a[0]<b[2] and b[0]<a[2] and a[1]<b[3] and b[1]<a[3]


def bay(cell,rects):
    x0,y0=cell[0]*GRID,cell[1]*GRID
    # A whole legal site must fit in this cell; do not count a wire-only sliver.
    for iy in range(math.ceil(y0/YP),math.floor((y0+GRID-YP+1e-9)/YP)+1):
        for ix in range(math.ceil(x0/XP),math.floor((x0+GRID-XP+1e-9)/XP)+1):
            r=(ix*XP,iy*YP,(ix+1)*XP,(iy+1)*YP)
            if not any(overlap(r,b) for b in rects):return [round(r[0],3),round(r[1],3)]
    return None


def audit(blocks,width,height,start,end,occupancy=None):
    rows=[]
    for line in Path(blocks).read_text().splitlines():
        n,m,*v=line.split('\t');rows.append((n,m,tuple(map(float,v))))
    hard=list(rows)
    if occupancy:
        occ=json.loads(Path(occupancy).read_text())
        dims=occ['masters']['BUFx24_ASAP7_75t_R']
        if dims is None or dims[0]>XP or dims[1]>YP:raise ValueError('clock master exceeds exact bay footprint')
        rows.extend((n,'placed_std',tuple(v)) for n,*v in occ['placed_std'])
    g=Grid(width,height,[r for _,_,r in rows])
    # Restrict exact checks to cells covered by reset repeater hard macros.
    reset=[r for n,_,r in rows if n.startswith('rstt_')]
    affected=set()
    for x0,y0,x1,y1 in reset:
        affected.update((i,j) for i in range(int(x0//GRID),math.ceil(x1/GRID))
                        for j in range(int(y0//GRID),math.ceil(y1/GRID)))
    buckets={c:[] for c in affected}
    for _,_,r in rows:
        for i in range(max(0,int(r[0]//GRID)),min(g.nx,math.ceil(r[2]/GRID))):
            for j in range(max(0,int(r[1]//GRID)),min(g.ny,math.ceil(r[3]/GRID))):
                c=(i,j)
                if c in buckets:buckets[c].append(r)
    restored={}
    for c,rr in buckets.items():
        p=bay(c,rr)
        if p is not None:restored[c]=p;g.blk[c[1]*g.nx+c[0]]=0
    path=g._route(tuple(start),tuple(end),380)
    # Witness stations every <=300um of routed path, plus each endpoint.
    # Original coarse-free cells also receive exact rectangle checks.
    def point(c):
        if c in restored:return restored[c]
        if not g.free(c):return None
        box=(c[0]*GRID,c[1]*GRID,(c[0]+1)*GRID,(c[1]+1)*GRID)
        return bay(c,[r for _,_,r in rows if overlap(box,r)])
    stops=[];indices=[0]
    while indices[-1]<len(path)-1:
        last=indices[-1]
        pa=point(path[last]);ca=g.xy(path[last])
        eligible=[]
        for k in range(last+1,min(last+40,len(path)-1)+1):
            pb=point(path[k]);cb=g.xy(path[k])
            if pb is not None and (k-last)*GRID+sum(abs(pa[i]-ca[i])+abs(pb[i]-cb[i]) for i in (0,1))<=405:
                eligible.append(k)
        if not eligible:raise ValueError('no reachable exact repeater bay at '+str((last,path[last])))
        indices.append(max(eligible))
    for k in indices:
        c=path[k];p=point(c)
        if p is None:raise ValueError('witness stop has no legal exact bay: '+str(c))
        stops.append(dict(path_index=k,cell=c,site=p))
    lengths=[(b['path_index']-a['path_index'])*GRID+
             sum(abs(a['site'][i]-g.xy(tuple(a['cell']))[i])+abs(b['site'][i]-g.xy(tuple(b['cell']))[i]) for i in (0,1))
             for a,b in zip(stops,stops[1:])]
    return dict(schema='opentallas.qwen.exact_corridor_geometry.v1',
                blocks_sha256=hashlib.sha256(Path(blocks).read_bytes()).hexdigest(),
                occupancy_sha256=hashlib.sha256(Path(occupancy).read_bytes()).hexdigest() if occupancy else None,
                clock_master_um=occ['masters'] if occupancy else None,
                placed_std_count=len(occ['placed_std']) if occupancy else None,
                start=start,end=end,grid_um=GRID,strict_blocked_run_um=380,
                restored_reset_bay_cells=len(restored),path_steps=len(path)-1,
                witness_stations=stops,conservative_route_segment_um=lengths,
                max_conservative_segment_um=max(lengths),reach_pass=max(lengths)<=405,
                placement_qualified=False,physical_retry_admitted=False,
                remaining=['Recompute exact bays after placing all765 new local root trees (failed run has no ODB)',
                           'Use exact bays during actual placement and check placed routed stage lengths <=405um',
                           'Rebuild whole spine and sign off actual TT/FF plus SS sensitivity'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--blocks',required=True)
    p.add_argument('--width',type=float,required=True);p.add_argument('--height',type=float,required=True)
    p.add_argument('--start',type=int,nargs=2,default=[1940,854]);p.add_argument('--end',type=int,nargs=2,default=[1691,877])
    p.add_argument('--occupancy');p.add_argument('--out',required=True);a=p.parse_args()
    Path(a.out).write_text(json.dumps(audit(a.blocks,a.width,a.height,a.start,a.end,a.occupancy),indent=1)+'\n')
