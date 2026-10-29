"""Plan all register sites from boundary slots and the netlist's registered dataflow; no RTL/clock edits."""
import sys,json,re,math,inspect,statistics,copy
from pathlib import Path
sys.path.insert(0,'/srv/opentallas-scratch2/claude/wt/codex-head-lepwe/tools/autopilot')
import geom_rules as G
R=Path('/srv/opentallas-scratch2/claude/codex-head-lepwe');D=G.Design(R/'geom/geom.tsv')
ss=inspect.getsource(G.r2r_metrics).replace('if c[0] != "S":', 'if c[0] not in ("S","M"):').replace('if k == "S":','if k in ("S","M"):').replace('if D.kind(s[1]) == "S":','if D.kind(s[1]) in ("S","M"):').replace('if mx > R2R_MAX:', 'if mx > 390.0:').replace('st = {}','st = {}; bad = []').replace('n_gt += 1','n_gt += 1; bad.append((mx,src,cap))').replace('return dict(r2r_max=','return dict(bad=bad,r2r_max=')
ns=dict(G.__dict__);exec(ss,ns); census=ns['r2r_metrics']
for a in json.loads((R/'geom/macro_face_assignment.json').read_text()):
 for i,c in list(D.cells.items()):
  if c[0]=='M' and c[6]==a['name']:
   x,y=a['xy']; D.cells[i]=c[:2]+(x,y,x+c[4]-c[2],y+c[5]-c[3])+c[6:]
ff={i:c for i,c in D.cells.items() if c[0]=='S'}; original=dict(ff); fixed={i for i,c in D.cells.items() if c[0]=='M'}; desired={i:G.ctr(c) for i,c in ff.items()}
# Keep the actual boundary output registers fixed; detect directly through the
# same buffer-only chain as the existing face-register placement rule.
for p in D.pins:
 if p['io']!='OUTPUT':continue
 n=D.pin_net.get(p['k']);seen=set()
 for _ in range(5):
  if n is None or n in seen:break
  seen.add(n);dr=D.nets[n][1]
  if not dr or dr[0]!='i':break
  i=dr[1]
  if D.kind(i)=='S':fixed.add(i);break
  if D.kind(i)!='B':break
  ins=[q for q,ck in D.cell_in.get(i,[]) if not ck]
  if len(ins)!=1:break
  n=ins[0]
# Plan the entire K-side four-slot bank, not individual measured offenders.
# All three register groups use their own eight-bit face-window centre.
pin={p['name']:(p['x'],p['y']) for p in D.pins};group={};xmap={}
for d in ('kn','nk'):
 names=([f'k_lo_d[{i}]' for i in range(553)]+['k_lo_v','k_rxv','k_li_r']) if d=='kn' else ([f'k_li_d[{i}]' for i in range(553)]+['k_li_v','k_lo_r']+[f'k_flt[{i}]' for i in range(3)])
 for c in range((len(names)+7)//8):xmap[d,c]=(min(pin[p][0] for p in names[c*8:c*8+8] if p in pin)+max(pin[p][0] for p in names[c*8:c*8+8] if p in pin))/2
for i,c in ff.items():
 name=c[6].replace('\\','');m=re.match(r'u_land.u_(kn|nk).u_([wr]).g_chunk\[(\d+)\]',name)
 if not m:continue
 d,side,k=m[1],m[2],int(m[3])
 if d=='kn' and side!='w':continue
 if i in fixed:continue
 y=21.0 if d=='kn' else (200.0 if side=='w' else 12.0)
 xx=xmap[d,k]
 if d=='kn':
  bit=re.search(r'/data\[\d+\]\[(\d+)\]',name)
  if bit:
   b=k*8+int(bit[1]);pn=f'k_lo_d[{b}]' if b<553 else ['k_lo_v','k_rxv','k_li_r'][b-553];xx=pin[pn][0]
 desired[i]=(xx,y); group[i]=(d,side,k)
 if not (d=='nk' and side=='w'):fixed.add(i)
# Structural keepout/row model, matching the existing SRAM halo and core rows.
X0,Y0,X1,Y1=4.32,4.32,384.48,427.68; SX,SY=.054,.27
NX=int(round((X1-X0)/SX)); NY=int(round((Y1-Y0)/SY)); box=[]
for c in D.cells.values():
 if c[0]=='M':box.append((c[2]-4.32,c[3]-4.32,c[4]+4.32,c[5]+4.32))
box.append((192.0,213.84,196.8,218.16))
base=[bytearray(NX) for _ in range(NY)]
for x0,y0,x1,y1 in box:
 a=max(0,int(math.floor((x0-X0)/SX)));b=min(NX,int(math.ceil((x1-X0)/SX)))
 for j in range(max(0,int(math.floor((y0-Y0)/SY))),min(NY,int(math.ceil((y1-Y0)/SY)))):base[j][a:b]=b'\1'*(b-a)

def pack():
 occ=[bytearray(x) for x in base]; target=dict(desired); assigned={}
 # Boundary flops first, then all explicitly planned banks, then the remaining
 # register field. Global placement will place combinational logic around this.
 order=sorted(ff,key=lambda i:(0 if i in fixed and i not in group else 1 if i in group else 2,i))
 for i in order:
  c=ff[i];w=int(math.ceil((c[4]-c[2]-.0001)/SX));h=int(round((c[5]-c[3])/SY));assert h==1,(c[1],h)
  tx,ty=target[i];tx-=.5*(c[4]-c[2]);ty-=.5*(c[5]-c[3]); ix=max(0,min(NX-w,int(round((tx-X0)/SX))));iy=max(0,min(NY-1,int(round((ty-Y0)/SY))))
  z=b'\0'*w;best=None
  for radius in (0,8,40,160,NY):
   lo=max(0,iy-radius);hi=min(NY,iy+radius+1)
   for j in range(lo,hi):
    # The whole landing writer/read-control bank remains in its planned strip.
    if i in group:
     yy=Y0+j*SY;d=group[i][0]
     if d=='kn' and not 17.28<=yy<=24.3:continue
     if d=='nk' and group[i][1]=='r' and not 8.64<=yy<=15.66:continue
    if best is not None and abs((j-iy)*SY)>best[0]+.001:continue
    # Find nearest contiguous free run on each side of the target.
    for k in (occ[j].rfind(z,0,min(NX,ix+w)),occ[j].find(z,ix,NX)):
     if k<0:continue
     cost=abs((j-iy)*SY)+abs((k-ix)*SX)
     if best is None or (cost,j,k)<best:best=(cost,j,k)
   if best is not None and radius*SY>=best[0]-.001:break
  if best is None:raise RuntimeError(('no row site',i,c[6]))
  _,j,k=best;occ[j][k:k+w]=b'\1'*w;x=X0+k*SX;y=Y0+j*SY
  assigned[i]=(x,y);D.cells[i]=c[:2]+(x,y,x+c[4]-c[2],y+c[5]-c[3])+c[6:]
 return assigned

hist=[];assigned=pack()
for it in range(25):
 r=census(D);hist.append(dict(iteration=it,max=r['r2r_max'],bad=len(r['bad'])));print(hist[-1],flush=True)
 if not r['bad']:break
 for i in ff:desired[i]=G.ctr(D.cells[i])
 for dist,a,b in sorted(r['bad'],reverse=True):
  if a in fixed and b in fixed:continue
  xa,ya=desired.get(a,G.ctr(D.cells[a]));xb,yb=desired.get(b,G.ctr(D.cells[b]));d=abs(xa-xb)+abs(ya-yb)
  if d<=380:continue
  f=(d-380)/d
  if a in fixed:desired[b]=(xb+(xa-xb)*f,yb+(ya-yb)*f)
  elif b in fixed:desired[a]=(xa+(xb-xa)*f,ya+(yb-ya)*f)
  else:
   desired[a]=(xa+(xb-xa)*f*.5,ya+(yb-ya)*f*.5);desired[b]=(xb+(xa-xb)*f*.5,yb+(ya-yb)*f*.5)
 # Retain every other register's current legal point across projection passes.
 for i in ff:
  if i not in desired:desired[i]=G.ctr(D.cells[i])
 assigned=pack()
r=census(D);rep=dict(schema='opentallas.head_lep_register_plan.v1',source_odb='diag_place/3_place',history=hist,final={k:v for k,v in r.items() if k!='bad'},remaining=[dict(distance=d,src=D.cells[a][6],dst=D.cells[b][6],fixed_a=a in fixed,fixed_b=b in fixed) for d,a,b in r['bad']],registers=[dict(name=D.cells[i][6],master=D.cells[i][1],xy=list(assigned[i]),original_xy=list(original[i][2:4]),group=list(group[i]) if i in group else None) for i in ff])
(R/'geom/register_plan_v4.json').write_text(json.dumps(rep,indent=1)+'\n')
print('final',rep['final'],flush=True)
if r['bad']:sys.exit(1)
