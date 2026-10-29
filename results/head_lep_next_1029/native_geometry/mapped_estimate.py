"""Logical mapped-graph placement estimate. Not actual placement or route admission.
No TAPCELL/body ledger yet; any result remains HOLD pending native-kit floorplan.
"""
import argparse,json,math,collections,sys
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--mapped',required=True);ap.add_argument('--model',required=True);ap.add_argument('--pins',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
z=json.load(open(a.mapped));model=json.load(open(a.model));pp=json.load(open(a.pins));top=z['modules'][model['module']];mods=z['modules'];W,H=model['outline_um'];out=Path(a.out);out.mkdir(exist_ok=True)
mac={q['inst']:q for q in model['macro_placement']};cells={};ids={};points={};fixed=set();pins={};drivers={};sinks=collections.defaultdict(list);edges=collections.defaultdict(list)
for i,(name,c) in enumerate(top['cells'].items(),1):
 typ=c['type']
 if typ=='$scopeinfo':continue
 ids[name]=i
 if name in mac:
  q=mac[name];x,y=q['origin_um'];w,h=q['size_um'];kind='M';fixed.add(i)
 else:
  area=float(mods[typ]['attributes']['area']);w=round(area/.27,6);h=.27;x=W/2-w/2;y=H/2-h/2
  kind='S' if typ.startswith(('DFF','SDFF')) else ('B' if typ.startswith(('INV','BUF','CLKBU')) else 'L')
 cells[i]=(kind,typ,x,y,x+w,y+h,name);points[i]=(x+w/2,y+h/2)
 for p,bs in c['connections'].items():
  ck=p in ('CLK','clk','wclk','rclk')
  for b in bs:
   if isinstance(b,str):continue
   if c['port_directions'][p]=='output':
    if b in drivers:raise ValueError(('multiple drivers',b))
    drivers[b]='i'+str(i)
   else:sinks[b].append('i'+str(i)+('c' if ck else ''))
assert len(fixed)==len(mac),(len(fixed),len(mac),set(mac)-set(ids))
for k,p in enumerate(pp):
 n=p['name'];bus=n.split('[')[0];ix=int(n.split('[')[1][:-1]) if '[' in n else 0;b=top['ports'][bus]['bits'][ix];di=top['ports'][bus]['direction'];pins[k]=dict(p,io=di.upper(),bit=b);points[-k-1]=(p['x'],p['y']);fixed.add(-k-1)
 if di=='input':
  assert b not in drivers,('input driver',n);drivers[b]='p'+str(k)
 else:sinks[b].append('p'+str(k))
def key(s):return -int(s[1:])-1 if s[0]=='p' else int(s[1:].rstrip('c'))
for b,ss in sinks.items():
 if b not in drivers:continue
 dr=drivers[b];u=key(dr)
 for s in ss:
  if s.endswith('c') and s[0]=='i':continue
  v=key(s)
  if u==v:continue
  edges[u].append(v);edges[v].append(u)
# Pin-neighbor anchors include only actual one-stage leaf cells; no invented flops.
anchors={}
for p in pins:
 u=-p-1
 for i in edges[u]:
  if i>0 and cells[i][0]=='S':anchors.setdefault(i,[]).append(points[u])
for i,ps in anchors.items():points[i]=(sum(p[0] for p in ps)/len(ps),sum(p[1] for p in ps)/len(ps));fixed.add(i)
for step in range(100):
 nxt={}
 for i,c in cells.items():
  if i in fixed or not edges[i]:continue
  ps=[points[j] for j in edges[i]];x=sum(p[0] for p in ps)/len(ps);y=sum(p[1] for p in ps)/len(ps);ox,oy=points[i];nxt[i]=(.3*ox+.7*x,.3*oy+.7*y)
 points.update(nxt)
# Legal discrete-row estimate; macro halos and clock entry are real exclusions.
X0,Y0,X1,Y1=4.32,4.32,W-4.32,H-4.32;SX,SY=.054,.27;NX=round((X1-X0)/SX);NY=round((Y1-Y0)/SY);occ=[bytearray(NX) for _ in range(NY)]
def occupy(box):
 x0,y0,x1,y1=box;lo=max(0,math.floor((x0-X0)/SX));hi=min(NX,math.ceil((x1-X0)/SX))
 for row in range(max(0,math.floor((y0-Y0)/SY)),min(NY,math.ceil((y1-Y0)/SY))):occ[row][lo:hi]=b'\1'*(hi-lo)
for i,c in cells.items():
 if c[0]=='M':occupy((c[2]-4.32,c[3]-4.32,c[4]+4.32,c[5]+4.32))
cx,cy=model['clock_root_um'];occupy((cx-2.16,cy-2.16,cx+2.16,cy+2.16))
order=sorted((i for i,c in cells.items() if c[0]!='M'),key=lambda i:(0 if i in anchors else 1 if cells[i][0]=='S' else 2,-len(edges[i]),i))
for i in order:
 c=cells[i];w=math.ceil((c[4]-c[2]-1e-6)/SX);assert abs(c[5]-c[3]-.27)<1e-5
 tx,ty=points[i];ix=max(0,min(NX-w,round((tx-(c[4]-c[2])/2-X0)/SX)));iy=max(0,min(NY-1,round((ty-.135-Y0)/SY)));needle=b'\0'*w;best=None
 for radius in (0,8,40,160,NY):
  for row in range(max(0,iy-radius),min(NY,iy+radius+1)):
   if best and abs(row-iy)*SY>best[0]:continue
   for k in (occ[row].rfind(needle,0,min(NX,ix+w)),occ[row].find(needle,ix,NX)):
    if k<0:continue
    v=(abs(row-iy)*SY+abs(k-ix)*SX,row,k)
    if best is None or v<best:best=v
  if best and radius*SY>=best[0]:break
 if best is None:raise ValueError(('no free legal sites',i))
 _,row,k=best;occ[row][k:k+w]=b'\1'*w;x=X0+k*SX;y=Y0+row*SY;cells[i]=c[:2]+(x,y,x+c[4]-c[2],y+.27)+c[6:]
rows=['D\t0\t0\t'+str(W)+'\t'+str(H),'R\t4.32\t4.32\t'+str(W-4.32)+'\t'+str(H-4.32)]
for lay,di,p in [('M1','VERTICAL',.036),('M2','HORIZONTAL',.036),('M3','VERTICAL',.036),('M4','HORIZONTAL',.048),('M5','VERTICAL',.048),('M6','HORIZONTAL',.064),('M7','VERTICAL',.064)]:rows.append(f'T\t{lay}\t{di}\t{p}')
for i,c in cells.items():rows.append('\t'.join(map(str,('C',i,*c))))
for k,p in pins.items():rows.append('\t'.join(map(str,('P',k,p['name'],p['io'],'CLOCK' if p['name']=='clk' else 'SIGNAL',p['layer'],p['x'],p['y']))))
for b,ss in sinks.items():rows.append('\t'.join(('N',str(b),drivers.get(b,'-'),*ss)))
(out/'estimate.tsv').write_text('\n'.join(rows)+'\n');(out/'receipt.json').write_text(json.dumps(dict(kind='MAPPED_GRAPH_ANALYTIC_ESTIMATE_NOT_ACTUAL_PLACEMENT',cells=len(cells),ff=sum(c[0]=='S' for c in cells.values()),macros=len(mac),direct_boundary_anchors=len(anchors),status='HOLD: exact TAPCELL/body ledger, macro pin geometry, clock taps and real placement pending'),indent=2)+'\n')
print((out/'receipt.json').read_text())
