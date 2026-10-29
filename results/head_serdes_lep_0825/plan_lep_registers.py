"""Connected register placement proposal for the resized LEP child; no route claim.

Starts from the actual canonical netlist geometry. New pins and the exact macro
plan are fixed; first boundary registers are placed at their actual pins. Other
registers are projected into the 380-um endpoint reach envelope and legal sites.
Combinational placement remains the global placer's job.
"""
import argparse,inspect,json,math,sys
from collections import deque
from pathlib import Path

ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--dump',type=Path,required=True)
ap.add_argument('--child',type=Path,required=True);ap.add_argument('--pins',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
a=ap.parse_args();sys.path.insert(0,str(a.repo/'tools/autopilot'));import geom_rules as G
D=G.Design(a.dump);oldframe=D.die;child=json.loads(a.child.read_text())['child_type'];W,H=child['outline_um'];D.die=(0.,0.,W,H)
newpins={p['name']:p for p in json.loads(a.pins.read_text())['pins']}
newpins['clk']=dict(x=W/2+.096,y=H/2)
for p in D.pins:
 if p['name'] in newpins:p.update({q:newpins[p['name']][q] for q in ('x','y')})
macros={p['inst']:p for p in child['contents']};macrocount=0
for i,c in list(D.cells.items()):
 if c[0]!='M':continue
 m=macros[c[6].replace('\\','')];x,y=m['origin_um'];D.cells[i]=c[:2]+(x,y,x+c[4]-c[2],y+c[5]-c[3])+c[6:];macrocount+=1
assert macrocount==55
ff={i:c for i,c in D.cells.items() if c[0]=='S'}
desired={i:((c[2]+c[4])/2*W/oldframe[2],(c[3]+c[5])/2*H/oldframe[3]) for i,c in ff.items()}
anchor={}
def capture(n):
 q=deque([n]);seen=set();out=set()
 while q:
  n=q.popleft()
  if n in seen:continue
  seen.add(n)
  for r in D.nets[n][2]:
   if r[0]!='i' or r[2]:continue
   i=r[1];k=D.kind(i)
   if k=='S':out.add(i)
   elif k in 'BLK':q.extend(D.drives.get(i,[]))
 return out
for p in D.pins:
 if p['sig']=='CLOCK':continue
 n=D.pin_net.get(p['k'])
 if n is None:continue
 if p['io']=='INPUT': targets=capture(n)
 else:
  targets=set();q=deque([n]);seen=set()
  while q:
   n=q.popleft()
   if n in seen:continue
   seen.add(n);r=D.nets[n][1]
   if not r or r[0]!='i':continue
   i=r[1];k=D.kind(i)
   if k=='S':targets.add(i)
   elif k in 'BLK':q.extend(nn for nn,ck in D.cell_in.get(i,[]) if not ck)
 for i in targets:anchor.setdefault(i,[]).append((p['x'],p['y']))
for i,pts in anchor.items():desired[i]=(sum(x for x,y in pts)/len(pts),sum(y for x,y in pts)/len(pts))
src=inspect.getsource(G.r2r_metrics)
# Expose endpoint violations from the existing exact combinational traversal.
# Including the complete physical memory box is a conservative planning bound,
# not a replacement for the typed-memory gate or its actual pin inventory.
src=src.replace('memories=set(); unknown=[]','memories={i for i,c in D.cells.items() if c[0]=="M"}; unknown=[]')
src=src.replace('st = {}','st = {}; bad = []').replace('n_gt += 1','n_gt += 1; bad.append((mx,src,cap))')
src=src.replace('return dict(r2r_memory_instances=', 'return dict(bad=bad,r2r_memory_instances=')
ns=dict(G.__dict__);exec(src,ns);census=ns['r2r_metrics']
X0,Y0,X1,Y1=4.32,4.32,W-4.32,H-4.32;SX,SY=.054,.27
NX=int(round((X1-X0)/SX));NY=int(round((Y1-Y0)/SY));base=[bytearray(NX) for _ in range(NY)]
boxes=[(c[2]-4.32,c[3]-4.32,c[4]+4.32,c[5]+4.32) for c in D.cells.values() if c[0]=='M']
boxes.append((W/2-3,H/2-3,W/2+3,H/2+3))
for x0,y0,x1,y1 in boxes:
 lo=max(0,int(math.floor((x0-X0)/SX)));hi=min(NX,int(math.ceil((x1-X0)/SX)))
 for j in range(max(0,int(math.floor((y0-Y0)/SY))),min(NY,int(math.ceil((y1-Y0)/SY)))):base[j][lo:hi]=b'\1'*(hi-lo)
order=sorted(ff,key=lambda i:(i not in anchor,i))
def pack():
 occ=[bytearray(x) for x in base];assigned={}
 for i in order:
  c=ff[i];w=int(math.ceil((c[4]-c[2]+.54-.00001)/SX));tx,ty=desired[i]
  ix=max(0,min(NX-w,int(round((tx-(c[4]-c[2])/2-X0)/SX))));iy=max(0,min(NY-1,int(round((ty-.135-Y0)/SY))));z=b'\0'*w;best=None
  for radius in (0,8,40,160,NY):
   for j in range(max(0,iy-radius),min(NY,iy+radius+1)):
    if best is not None and abs((j-iy)*SY)>best[0]:continue
    for k in (occ[j].rfind(z,0,min(NX,ix+w)),occ[j].find(z,ix,NX)):
     if k<0:continue
     v=(abs((j-iy)*SY)+abs((k-ix)*SX),j,k)
     if best is None or v<best:best=v
   if best is not None and radius*SY>=best[0]:break
  if best is None:raise RuntimeError(('no row sites',i))
  _,j,k=best;occ[j][k:k+w]=b'\1'*w;x=X0+k*SX;y=Y0+j*SY;assigned[i]=(x,y)
  D.cells[i]=c[:2]+(x,y,x+c[4]-c[2],y+c[5]-c[3])+c[6:]
 return assigned
hist=[];seen=set();assigned=pack()
for it in range(40):
 r=census(D);mark=(r['r2r_captures_gt405'],r['r2r_max']);hist.append(dict(iteration=it,violations=mark[0],max_um=mark[1]));print(hist[-1],flush=True)
 if not r['bad'] or mark in seen:break
 seen.add(mark)
 for i in ff:desired[i]=G.ctr(D.cells[i])
 for dist,sa,ca in sorted(r['bad'],reverse=True):
  fixeda=sa in anchor or sa not in ff;fixedb=ca in anchor or ca not in ff
  if fixeda and fixedb:continue
  xa,ya=desired.get(sa,G.ctr(D.cells[sa]));xb,yb=desired.get(ca,G.ctr(D.cells[ca]));d=abs(xa-xb)+abs(ya-yb)
  if d<=380:continue
  f=(d-380)/d
  if fixeda:desired[ca]=(xb+(xa-xb)*f,yb+(ya-yb)*f)
  elif fixedb:desired[sa]=(xa+(xb-xa)*f,ya+(yb-ya)*f)
  else:desired[sa]=(xa+(xb-xa)*f/2,ya+(yb-ya)*f/2);desired[ca]=(xb+(xa-xb)*f/2,yb+(ya-yb)*f/2)
 assigned=pack()
r=census(D);a.out.mkdir(parents=True,exist_ok=True)
rep=dict(kind='ANALYTIC_REGISTER_PLAN',outline_um=[W,H],macros=55,registers=len(ff),boundary_anchored=len(anchor),history=hist,
 final={k:v for k,v in r.items() if k!='bad'},remaining=[dict(distance=d,source=D.cells[s][6],capture=D.cells[c][6],source_fixed=s in anchor or s not in ff,capture_fixed=c in anchor or c not in ff) for d,s,c in r['bad']],
 sites=[dict(name=D.cells[i][6],master=D.cells[i][1],xy=list(assigned[i])) for i in ff])
(a.out/'register_plan.json').write_text(json.dumps(rep,indent=1)+'\n')
print(json.dumps({k:v for k,v in rep.items() if k not in ('sites','remaining')}),flush=True)
