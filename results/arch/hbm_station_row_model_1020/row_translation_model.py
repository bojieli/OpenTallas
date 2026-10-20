#!/usr/bin/env python3
"""Exact convex row-origin feasibility of captured L1 point/rectangle terms.
This is a geometric lower-bound model: SYNTH missing pins and fixed-neighbor assumptions
remain explicit. It does not qualify full placement or waive an overreach.
"""
import argparse,itertools,json,math
from pathlib import Path
import numpy as np

def region(d,radius,placed_only=False):
    g=d['geometry']; W,H=d['die_um']
    lo=dict(x=0.,y=0.,u=-math.inf,v=-math.inf)
    hi=dict(x=W-g['rw'],y=H-g['rh'],u=math.inf,v=math.inf)
    witness={}
    for _,(dx,dy),geo,kind,label in d['terms']:
        if placed_only and kind!='placed':continue
        if geo[0]=='pt': x0=x1=geo[1];y0=y1=geo[2]
        else:_,x0,y0,x1,y1=geo
        lower=dict(x=x0-radius-dx,y=y0-radius-dy,u=x0+y0-radius-dx-dy,v=x0-y1-radius-dx+dy)
        upper=dict(x=x1+radius-dx,y=y1+radius-dy,u=x1+y1+radius-dx-dy,v=x1-y0+radius-dx+dy)
        for k in lo:
            if lower[k]>lo[k]:lo[k]=lower[k];witness[k+'_lower']=label
            if upper[k]<hi[k]:hi[k]=upper[k];witness[k+'_upper']=label
    normal=dict(x=(1,0),y=(0,1),u=(1,1),v=(1,-1))
    A=[]
    for k,(a,b) in normal.items():
        if math.isfinite(hi[k]):A.append((a,b,hi[k]))
        if math.isfinite(lo[k]):A.append((-a,-b,-lo[k]))
    vertices=[]
    for (a,b,c),(e,f,h) in itertools.combinations(A,2):
        det=a*f-b*e
        if not det:continue
        x=(c*f-b*h)/det;y=(a*h-c*e)/det
        if all(a*x+b*y<=c+1e-7 for a,b,c in A):
            if not any(abs(x-u)+abs(y-v)<1e-6 for u,v in vertices):vertices.append((x,y))
    return dict(feasible=bool(vertices),bounds={k:[lo[k],hi[k]] for k in lo},vertices=vertices,witness=witness)

def minimum(d,placed_only):
    low,high=0.,100000.
    for _ in range(50):
        mid=(low+high)/2
        if region(d,mid,placed_only)['feasible']:high=mid
        else:low=mid
    return round(high,6)

def occupancy(d,cap):
    g=d['geometry']; C=d['cell_um'];R=d['reach_um'];x0=g['site'][0]-g['rw']/2;y0=g['site'][1]-g['rh']/2
    grid=np.load(cap/(d['row']+'_occupancy.npz'))['grid'];ny,nx=grid.shape
    nw,nh=math.ceil(g['rw']/C),math.ceil(g['rh']/C);r=math.ceil(R/C)
    i0=max(0,int(x0/C)-r);j0=max(0,int(y0/C)-r)
    i1=min(nx-nw,int(x0/C)+r);j1=min(ny-nh,int(y0/C)+r)
    if i1<i0 or j1<j0:return dict(free_candidates=0)
    sub=(grid[j0:j1+nh,i0:i1+nw]!=0).astype(np.int32)
    ii=np.zeros((sub.shape[0]+1,sub.shape[1]+1),dtype=np.int32);ii[1:,1:]=sub.cumsum(0).cumsum(1)
    h=j1-j0+1;w=i1-i0+1
    sums=ii[nh:nh+h,nw:nw+w]-ii[:h,nw:nw+w]-ii[nh:nh+h,:w]+ii[:h,:w]
    jj,xx=np.nonzero(sums==0);X=(i0+xx)*C;Y=(j0+jj)*C
    mx=np.zeros(len(X))
    for _,(dx,dy),geo,kind,label in d['terms']:
        if kind!='placed':continue
        if geo[0]=='pt':span=np.abs(X+dx-geo[1])+np.abs(Y+dy-geo[2])
        else:
            _,a,b,c,e=geo
            span=np.maximum(0,np.maximum(a-X-dx,X+dx-c))+np.maximum(0,np.maximum(b-Y-dy,Y+dy-e))
        mx=np.maximum(mx,span)
    k=int(np.argmin(mx)) if len(mx) else None
    return dict(free_candidates=len(X),feasible_placed_candidates=int((mx<=R-d['margin_um']).sum()),
                least_worst_span_um=round(float(mx[k]),6) if k is not None else None,
                least_worst_origin=[float(X[k]),float(Y[k])] if k is not None else None)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('capture',type=Path);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();rows=[]
    for p in sorted(a.capture.glob('rf*.json')):
        d=json.loads(p.read_text());g=d['geometry']
        rows.append(dict(row=d['row'],tiles=len(g['tiles']),row_um=[g['rw'],g['rh']],site=g['site'],
          missing_own_pin_geometry=[n for n,v in d['own_views'].items() if v['pins'] is None],
          at_405_all=region(d,405),at_405_fixed=region(d,405,True),
          minimum_centroid_radius_all_um=minimum(d,False),minimum_centroid_radius_fixed_um=minimum(d,True),
          occupancy=occupancy(d,a.capture),original_failure=d['original_failure']))
    a.out.write_text(json.dumps(dict(qualification=False,scope='Exact captured pre-place row-origin lower-bound model; no full-pin/whole-die/native/calendar admission',rows=rows),indent=2)+'\n')
    print('ROW_MODEL diagnostic rows',len(rows),'qualification=false')
if __name__=='__main__':main()
