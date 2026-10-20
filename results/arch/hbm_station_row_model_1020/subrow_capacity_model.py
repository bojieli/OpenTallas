#!/usr/bin/env python3
"""Screen two ordered subrows on the exact pre-place occupancy/stand-in constraints.
No source/edge/stage changes, no full-pin or clock/physical qualification.
"""
import argparse,json,math
from pathlib import Path
import numpy as np

def candidates(d,grid,start,end):
    g=d['geometry'];C=d['cell_um'];R=d['reach_um']-d['margin_um'];dims=g['dims'][start:end]
    rw=max(x[0] for x in dims) if g['along_x'] else sum(x[0] for x in dims)
    rh=sum(x[1] for x in dims) if g['along_x'] else max(x[1] for x in dims)
    ox,oy=g['offs'][start];x0=g['site'][0]-g['rw']/2+ox;y0=g['site'][1]-g['rh']/2+oy
    nw,nh=math.ceil(rw/C),math.ceil(rh/C);r=math.ceil(d['reach_um']/C);ny,nx=grid.shape
    i0=max(0,int(x0/C)-r);j0=max(0,int(y0/C)-r);i1=min(nx-nw,int(x0/C)+r);j1=min(ny-nh,int(y0/C)+r)
    if i1<i0 or j1<j0:return np.zeros((0,2)),rw,rh
    sub=(grid[j0:j1+nh,i0:i1+nw]!=0).astype(np.int32)
    ii=np.zeros((sub.shape[0]+1,sub.shape[1]+1),np.int32);ii[1:,1:]=sub.cumsum(0).cumsum(1)
    h=j1-j0+1;w=i1-i0+1
    sums=ii[nh:nh+h,nw:nw+w]-ii[:h,nw:nw+w]-ii[nh:nh+h,:w]+ii[:h,:w]
    jj,xx=np.nonzero(sums==0);X=(i0+xx)*C;Y=(j0+jj)*C;ok=np.ones(len(X),dtype=bool)
    for k,(dx,dy),geo,kind,label in d['terms']:
        if not start<=k<end:continue
        dx-=ox;dy-=oy
        if geo[0]=='pt':span=np.abs(X+dx-geo[1])+np.abs(Y+dy-geo[2])
        else:
            _,a,b,c,e=geo
            span=np.maximum(0,np.maximum(a-X-dx,X+dx-c))+np.maximum(0,np.maximum(b-Y-dy,Y+dy-e))
        ok &= span<=R+1e-9
    p=np.column_stack((X[ok],Y[ok]));order=np.argsort(abs(p[:,0]-x0)+abs(p[:,1]-y0));return p[order],rw,rh

def main():
    ap=argparse.ArgumentParser();ap.add_argument('capture',type=Path);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();rows=[]
    for path in sorted(a.capture.glob('rf*.json')):
        d=json.loads(path.read_text());grid=np.load(a.capture/(d['row']+'_occupancy.npz'))['grid'];n=len(d['geometry']['tiles']);cuts=[]
        for cut in range(1,n):
            A,aw,ah=candidates(d,grid,0,cut);B,bw,bh=candidates(d,grid,cut,n);joint=None
            for x,y in A:
                good=(B[:,0]+bw<=x+1e-9)|(B[:,0]>=x+aw-1e-9)|(B[:,1]+bh<=y+1e-9)|(B[:,1]>=y+ah-1e-9)
                if good.any():
                    q=B[np.flatnonzero(good)[0]];joint=[[float(x),float(y),aw,ah],[float(q[0]),float(q[1]),bw,bh]];break
            cuts.append(dict(cut=cut,candidates=[len(A),len(B)],joint=joint))
        rows.append(dict(row=d['row'],cuts=cuts,any_joint=any(c['joint'] for c in cuts)))
    a.out.write_text(json.dumps(dict(qualification=False,scope='Exact snapshot occupancy and current surrogate port constraints only; subrow joint screen is not an adopted placement or full-pin/clock/reach certificate',rows=rows),indent=2)+'\n')
    print('SUBROW_MODEL',[(r['row'],r['any_joint']) for r in rows],'qualification=false')
if __name__=='__main__':main()
