"""H-DIE r2 2026-10-15: band_lanes.py PINS.json P.json OUT_LANES.json [SLACK_um=600]
lane plan: every non-local die link whose pins are > MIN apart along its major axis gets a lane (H links: a y; V links:
an x) inside [pin span +- SLACK], chosen greedily (largest bits*length first) to minimise the max 100-um bin load along
the link's extent (tie: max sliding-1-mm window). Lanes = where the link's relay homes sit (relay plan input)."""
import json,sys,math,collections
import numpy as np
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent)); import pin_cut as pincut
pins=json.load(open(sys.argv[1])); P=json.load(open(sys.argv[2])); out=sys.argv[3]
SLACK=float(sys.argv[4]) if len(sys.argv)>4 else 600.0
HOMES=len(sys.argv)>5 and 'homes' in sys.argv[5].split(',')   # H-DIE r3: reject lanes whose route crosses a block > REACH (no relay home)
# H-DIE-V790 10-16: 'legs' also charges the lane's two perpendicular legs (pin -> lane) against the 1-mm sliding windows
# of the cut lines they cross, so a lane is not chosen whose legs overload a hub corner (default off: v5/v6 reproduce)
LEGS=len(sys.argv)>5 and 'legs' in sys.argv[5].split(',')
REACH=480.0
BLK=[(k,r['x'],r['y'],r['x']+r['w'],r['y']+r['h']) for k,r in P.items()]
FEEDV=('su_',)   # v5 grant: SU slices reserve a 40 um vertical feedthrough relay column
FEEDH=()
HOMES_CLS=set()   # H-DIE-V790: homescls=A+B applies the 'homes' rule to those link classes only
for _t in (sys.argv[5].split(',') if len(sys.argv)>5 else []):
  if _t.startswith('homescls='):
    HOMES=True; HOMES_CLS=set(x for x in _t[9:].split('+') if x)
# H-DIE-V790 10-16: mode token feed=PFX[+PFX] replaces the relay-legal feedthrough prefixes (both directions), e.g.
# feed=sm_ = the granted 40-um SM feedthrough column/row (H-SM carve) and NO SU feedthrough
for _t in (sys.argv[5].split(',') if len(sys.argv)>5 else []):
  if _t.startswith('feed='):
    FEEDV=tuple(x for x in _t[5:].split('+') if x); FEEDH=FEEDV
def xcost(segs,skip):
  c=0.0
  for t,cc,s0,s1 in segs:
    s0,s1=sorted((s0,s1))
    for k,a,b,cx,dy in BLK:
      if k in skip: continue
      if t=='h' and b<cc<dy: L=min(s1,cx)-max(s0,a)
      elif t=='v' and a<cc<cx: L=min(s1,dy)-max(s0,b)
      else: continue
      if L>REACH and not (t=='v' and k.startswith(FEEDV)) and not (t=='h' and FEEDH and k.startswith(FEEDH)): c+=L
  return c
MIN=600.0; step=100.0
W,H=pins['die_outline_um']; nx,ny=int(W//step)+1,int(H//step)+1
ends=collections.defaultdict(list)
for b,v in pins['blocks'].items():
  for f,fx in v['faces'].items():
    for p in fx['pins']: ends[p['link']].append((b,f,p))
LOCAL={'LG_SU','LG_HC','LG_SFU','HBM_K'}
V=np.zeros((nx,ny)); Hh=np.zeros((ny,nx))
def addH(x0,x1,y,b):
  x0,x1=sorted((x0,x1)); i0,i1=int(math.ceil(x0/step)),int(math.floor(x1/step))
  if i1>=i0: V[i0:i1+1,min(ny-1,max(0,int(y//step)))]+=b
def addV(x,y0,y1,b):
  y0,y1=sorted((y0,y1)); j0,j1=int(math.ceil(y0/step)),int(math.floor(y1/step))
  if j1>=j0: Hh[j0:j1+1,min(nx-1,max(0,int(x//step)))]+=b
cand=[]
for lk,e in ends.items():
  if len(e)!=2: continue
  (b1,f1,p1),(b2,f2,p2)=e
  dx,dy=abs(p1['x']-p2['x']),abs(p1['y']-p2['y'])
  if p1['cls'] not in LOCAL and max(dx,dy)>MIN: cand.append((lk,p1,p2,'h' if dx>=dy else 'v'))
  else:
    b=p1['bits']/2
    addH(p1['x'],p2['x'],p1['y'],b); addV(p2['x'],p1['y'],p2['y'],b)
    addH(p2['x'],p1['x'],p2['y'],b); addV(p1['x'],p2['y'],p1['y'],b)
phys=[(r['x'],r['y'],r['x']+r['w'],r['y']+r['h']) for k,r in P.items() if k.startswith('phy_')]
def inphy(x,y): return any(a<x<c and b<y<d for a,b,c,d in phys)
def hphy(x0,x1,y): return any(b-1<y<d+1 and x0<c and x1>a for a,b,c,d in phys)
def vphy(x,y0,y1): return any(a-1<x<c+1 and y0<d and y1>b for a,b,c,d in phys)
cand.sort(key=lambda c:-c[1]['bits']*max(abs(c[1]['x']-c[2]['x']),abs(c[1]['y']-c[2]['y'])))
lanes={}
for lk,p1,p2,t in cand:
  b=p1['bits']
  if t=='h':
    x0,x1=sorted((p1['x'],p2['x'])); i0,i1=int(math.ceil(x0/step)),int(math.floor(x1/step))
    lo=max(0,min(p1['y'],p2['y'])-SLACK); hi=min(H,max(p1['y'],p2['y'])+SLACK)
    js=[j for j in range(int(lo//step),int(hi//step)+1) if j<ny and not hphy(x0,x1,j*step+50)]
    if not js: js=[int(((p1['y']+p2['y'])/2)//step)]
    sk=(lk.split('>')[0],lk.split('>')[1].split(':')[0])
    hc=lambda j:(xcost([('v',p1['x'],p1['y'],j*step+50),('h',j*step+50,p1['x'],p2['x']),('v',p2['x'],j*step+50,p2['y'])],sk) if HOMES and (not HOMES_CLS or p1['cls'] in HOMES_CLS) else 0)
    def legs_h(j):
      if not LEGS: return 0
      y=j*step+step/2; w=0.0
      if i1>=i0: w=V[i0:i1+1,max(0,j-5):j+5].sum(1).max()+b
      for x,py in ((p1['x'],p1['y']),(p2['x'],p2['y'])):
        i=min(nx-1,int(x//step)); r0,r1=sorted((int(math.ceil(min(py,y)/step)),int(math.floor(max(py,y)/step))))
        if r1>=r0: w=max(w,Hh[r0:r1+1,max(0,i-5):i+5].sum(1).max()+b)
      return round(w/(14.0625*1000),2)
    best=min(js,key=lambda j:(hc(j),legs_h(j),(V[i0:i1+1,j].max() if i1>=i0 else 0),V[i0:i1+1,max(0,j-5):j+5].sum(1).max() if i1>=i0 else 0,abs(j*step-(p1['y']+p2['y'])/2)))
    y=best*step+step/2; lanes[lk]={'h':y}
    addH(x0,x1,y,b); addV(p1['x'],p1['y'],y,b/2); addV(p2['x'],p2['y'],y,b/2); addV(p2['x'],y,p2['y'],b/2); addV(p1['x'],y,p1['y'],b/2)
  else:
    y0,y1=sorted((p1['y'],p2['y'])); j0,j1=int(math.ceil(y0/step)),int(math.floor(y1/step))
    lo=max(0,min(p1['x'],p2['x'])-SLACK); hi=min(W,max(p1['x'],p2['x'])+SLACK)
    iss=[i for i in range(int(lo//step),int(hi//step)+1) if i<nx and not vphy(i*step+50,y0,y1)]
    if not iss: iss=[int(((p1['x']+p2['x'])/2)//step)]
    sk=(lk.split('>')[0],lk.split('>')[1].split(':')[0])
    vc=lambda i:(xcost([('h',p1['y'],p1['x'],i*step+50),('v',i*step+50,p1['y'],p2['y']),('h',p2['y'],i*step+50,p2['x'])],sk) if HOMES and (not HOMES_CLS or p1['cls'] in HOMES_CLS) else 0)
    def legs_v(i):
      if not LEGS: return 0
      x=i*step+step/2; w=0.0
      if j1>=j0: w=Hh[j0:j1+1,max(0,i-5):i+5].sum(1).max()+b
      for px,y in ((p1['x'],p1['y']),(p2['x'],p2['y'])):
        j=min(ny-1,int(y//step)); c0,c1=sorted((int(math.ceil(min(px,x)/step)),int(math.floor(max(px,x)/step))))
        if c1>=c0: w=max(w,V[c0:c1+1,max(0,j-5):j+5].sum(1).max()+b)
      return round(w/(14.0625*1000),2)
    best=min(iss,key=lambda i:(vc(i),legs_v(i),(Hh[j0:j1+1,i].max() if j1>=j0 else 0),Hh[j0:j1+1,max(0,i-5):i+5].sum(1).max() if j1>=j0 else 0,abs(i*step-(p1['x']+p2['x'])/2)))
    x=best*step+step/2; lanes[lk]={'v':x}
    addV(x,y0,y1,b); addH(p1['x'],x,p1['y'],b/2); addH(x,p2['x'],p2['y'],b/2); addH(p2['x'],x,p2['y'],b/2); addH(x,p1['x'],p1['y'],b/2)
json.dump(lanes,open(out,'w'))
r,_=pincut.run(pins,P,lanes); print('laned',len(lanes),json.dumps(r))
