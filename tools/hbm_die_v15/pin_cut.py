"""H-DIE r2 2026-10-15: honest planning cut (replaces the closest-point, 1-mm-grid cut of hbm_globalfp for die specs).
   pin_cut.py PINS.json P.json [LANES.json]   -> worst sliding-window ratio, lines/windows over 0.60
"""
"""pin-based cut: each link routed from its src pin segment to its dst pin segment (half HV, half VH), bits spread
uniformly along each pin span; vertical/horizontal cut lines every 100 um; demand per sliding 1 mm window (step 100);
supply TRK tracks/um (as hbm_globalfp), zero inside PHY. Optional lanes: link -> lane y (horizontal leg at lane)."""
import json,sys,math,collections
import numpy as np
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));import hbm_globalfp as F
def run(pins, P, lanes=None, step=100.0, win=1000.0, detail_line=None):
    W,H=pins['die_outline_um']
    nx,ny=int(W//step)+1,int(H//step)+1
    V=np.zeros((nx,ny)); Hh=np.zeros((ny,nx))   # V[i,j]: bits crossing vertical line x=i*step within y-bin j
    ends=collections.defaultdict(list)
    for b,v in pins['blocks'].items():
        for f,fx in v['faces'].items():
            for p in fx['pins']:
                ends[p['link']].append((b,f,p))
    who=collections.Counter()
    for lk,e in ends.items():
        if len(e)!=2: continue
        (b1,f1,p1),(b2,f2,p2)=e
        bits=p1['bits']
        def samples(f,p):
            n=max(1,int(p['span_um']//step)+1); out=[]
            for k in range(n):
                t=(k+0.5)/n*p['span_um']-p['span_um']/2
                out.append((p['x']+t,p['y']) if f in 'NS' else (p['x'],p['y']+t))
            return out
        s1,s2=samples(f1,p1),samples(f2,p2)
        n=max(len(s1),len(s2)); wb=bits/n/2
        for k in range(n):
            a=s1[k*len(s1)//n]; c=s2[k*len(s2)//n]
            for (u,v) in ((a,c),(c,a)):
                ly = lanes.get(lk) if lanes else None
                if isinstance(ly, dict) and 'v' in ly:   # vertical lane: horizontal at u.y to lane x, vertical, horizontal at v.y
                    lx=ly['v']; segsH=[(u[0],lx,u[1]),(lx,v[0],v[1])]; segsV=[(lx,u[1],v[1])]
                elif isinstance(ly, dict):
                    ly=ly['h']; segsH=[(u[0],v[0],ly)]; segsV=[(u[0],u[1],ly),(v[0],ly,v[1])]
                elif ly is None:
                    hy=u[1]; vx=v[0]
                    segsH=[(u[0],v[0],hy)]; segsV=[(vx,u[1],v[1])]
                else:   # Z: vertical at u.x to lane, horizontal at lane, vertical at v.x
                    segsH=[(u[0],v[0],ly)]; segsV=[(u[0],u[1],ly),(v[0],ly,v[1])]
                for (x0,x1,y) in segsH:
                    x0,x1=sorted((x0,x1)); i0,i1=int(math.ceil(x0/step)),int(math.floor(x1/step))
                    if i1>=i0: V[i0:i1+1,min(ny-1,int(y//step))]+=wb
                    if detail_line and i0*step<=detail_line[0]<=i1*step and detail_line[1]<=y<detail_line[2]: who[p1['cls']]+=wb
                for (x,y0,y1) in segsV:
                    y0,y1=sorted((y0,y1)); j0,j1=int(math.ceil(y0/step)),int(math.floor(y1/step))
                    if j1>=j0: Hh[j0:j1+1,min(nx-1,int(x//step))]+=wb
    nw=int(win//step)
    def windows(A, phys_axis):
        # sliding sum over nw bins along axis 1
        c=np.cumsum(np.pad(A,((0,0),(1,0))),axis=1); return c[:,nw:]-c[:,:-nw]
    WV=windows(V,0); WH=windows(Hh,1)
    sup=F.TRK*win
    # PHY supply zero: mask windows inside PHY (approx: any line through PHY interior with window overlapping -> scale)
    phys=[(r['x'],r['y'],r['x']+r['w'],r['y']+r['h']) for k,r in P.items() if k.startswith('phy_')]
    SV=np.full(WV.shape,sup); SH=np.full(WH.shape,sup)
    for (x0,y0,x1,y1) in phys:
        for i in range(int(math.ceil(x0/step)),min(WV.shape[0],int(x1//step)+1)):
            for j in range(WV.shape[1]):
                ov=max(0,min(j*step+win,y1)-max(j*step,y0)); SV[i,j]=F.TRK*max(0,win-ov)
        for i in range(int(math.ceil(y0/step)),min(WH.shape[0],int(y1//step)+1)):
            for j in range(WH.shape[1]):
                ov=max(0,min(j*step+win,x1)-max(j*step,x0)); SH[i,j]=F.TRK*max(0,win-ov)
    with np.errstate(divide='ignore',invalid='ignore'):
        RV=np.where(SV>0,WV/SV,np.where(WV>0,9.99,0)); RH=np.where(SH>0,WH/SH,np.where(WH>0,9.99,0))
    iv=np.unravel_index(np.argmax(RV),RV.shape); ih=np.unravel_index(np.argmax(RH),RH.shape)
    res=dict(worst_v=dict(ratio=round(float(RV[iv]),3),x=iv[0]*step,y=[iv[1]*step,iv[1]*step+win]),
             worst_h=dict(ratio=round(float(RH[ih]),3),y=ih[0]*step,x=[ih[1]*step,ih[1]*step+win]),
             lines_over_060=int((RV.max(1)>0.6).sum()+(RH.max(1)>0.6).sum()),
             windows_over_060=int((RV>0.6).sum()+(RH>0.6).sum()))
    return res, who
if __name__=='__main__':
    pins=json.load(open(sys.argv[1])); P=json.load(open(sys.argv[2]))
    lanes=json.load(open(sys.argv[3])) if len(sys.argv)>3 and sys.argv[3]!='-' else None
    r,who=run(pins,P,lanes)
    print(json.dumps(r))
