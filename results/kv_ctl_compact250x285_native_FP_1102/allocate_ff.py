"""Construct existing CTL FF sites from actual new FP rows/taps; no EDA or RTL changes."""
import sys,json,csv,math,bisect,collections,heapq,gzip,re
from pathlib import Path
O=Path(__file__).resolve().parent;R=O.parents[1];C=Path('/srv/opentallas-scratch/claude/codex-kv-ctl-compact250-0430/collector');P=O.parent/'kv_ctl_compact250x285_PREP_1102';sys.path.insert(0,str(R/'tools/autopilot'));import geom_rules as G
D=G.Design(str(C/'geom.tsv'),[str(O.parent/'kv_ctl_place_1102/memory_tt.lib')],True)
raw=list(csv.DictReader(open(C/'instances.csv')));old=list(csv.DictReader(open('/srv/opentallas-scratch/claude/codex-kv-ctl-rowfix-r2-0250/collector/placed.csv')));wanted={x['name']:x for x in old if x['kind']=='ff'};ffs={x['name']:x for x in raw if x['kind']=='ff'};assert set(ffs)==set(wanted) and len(ffs)==18768
ids={c[6]:i for i,c in D.cells.items()};rows=json.load(open(C/'rows.json'));assert rows['dbu']==1000;byy=collections.defaultdict(list)
for row in rows['rows']:byy[row['bbox'][1]].append(row)
ys=sorted(byy);occ=collections.defaultdict(list);poses={};W,H=250560,285120;CX,CY=125280,142560;ENV=130000;SW=54;RH=270
for c in raw:
 if c['kind']=='tap' or (c['kind'] not in ['ff','macro'] and c['status'] in ['FIRM','LOCKED','FIXED']):
  x,y,w,h=[round(float(c[k])*1000) for k in ['x','y','w','h']]
  for yy in range(y,y+h,RH):occ[yy].append((x,x+w,c['name']))
macros=[c for c in raw if c['kind']=='macro'];block=collections.defaultdict(list)
for yy in ys:
 for m in macros:
  x,y,w,h=[round(float(m[k])*1000) for k in ['x','y','w','h']]
  if yy<y+h+4320 and yy+RH>y-4320:block[yy].append((x-4320,x+w+4320,'MACRO'))
 if yy<CY+4520 and yy+RH>CY-4520:block[yy].append((CX-4520,CX+4520,'CLOCK_BAY'))
 occ[yy].sort()
pins={p['name']:p for p in D.pins};anchors=collections.defaultdict(list)
def first_caps(p):
 n=D.pin_net.get(p['k']);todo=[n] if n is not None else [];seen=set();out=set()
 while todo:
  n=todo.pop()
  if n in seen:continue
  seen.add(n)
  if p['io']=='OUTPUT':
   dr=D.nets[n][1]
   if not dr or dr[0]!='i':continue
   cid=dr[1];kind=D.kind(cid)
   if kind=='S':out.add(D.cells[cid][6])
   elif kind=='B':todo.extend(nn for nn,ck in D.cell_in.get(cid,[]) if not ck)
  else:
   for s in D.nets[n][2]:
    if s[0]!='i' or s[2]:continue
    kind=D.kind(s[1])
    if kind=='S':out.add(D.cells[s[1]][6])
    elif kind=='B':todo.extend(D.drives.get(s[1],[]))
 return out
for p in D.pins:
 if p['name'] in ['rst_n','por_n'] or p['sig'] in ['POWER','GROUND','CLOCK'] or G.CLOCK_PIN_RE.search(p['name']) or re.search(G.STRAP_RE_DEFAULT,p['name']):continue
 for n in first_caps(p):anchors[n].append(p)
assert len(anchors)==6846 and all(len(a)==1 for a in anchors.values())
selected={x['FF'] for x in json.load(open(P/'FF_envelope_PREP.json'))['centered_public']};assert len(selected)==522 and selected<=anchors.keys()
por_candidates=sorted(first_caps(pins['por_n'])-anchors.keys());assert por_candidates;por_ff=por_candidates[0]
# Same density bins as the actual rule; track FF-only occupancy, which cannot be lowered by later combinational placement.
bw=max(250.56,285.12)/80;nx=math.ceil(250.56/bw);ny=80;areas=collections.defaultdict(float);cellbin=collections.Counter()
def bindex(x,y):return (min(nx-1,max(0,int(x/1000/bw))),min(ny-1,max(0,int(y/1000/bw))))
def barea(i,j):return (min(250.56,(i+1)*bw)-i*bw)*(min(285.12,(j+1)*bw)-j*bw)
def reserve(name,x,y,w,h,orient):
 bisect.insort(occ[y],(x,x+w,name));poses[name]=dict(name=name,master=wanted[name]['master'],ll_dbu=[x,y],size_dbu=[w,h],orient=orient);i,j=bindex(x+w/2,y+h/2);areas[i,j]+=w*h/1e6;cellbin[i,j]+=1

def free_segments(lo,hi,blocks):
 left=lo
 for a,b,_ in sorted(blocks):
  if b<=left:continue
  if a>=hi:break
  if a>left:yield left,min(a,hi)
  left=max(left,b)
 if left<hi:yield left,hi

def find(name,tx,ty,inner,pinlimits=(),radius=None,binbox=None):
 w,h=[round(float(wanted[name][k])*1000) for k in ['w','h']];assert h==RH;options=[]
 ylo,yhi=(binbox[1],binbox[3]-h) if binbox else (ys[0],ys[-1])
 if radius is not None:ylo=max(ylo,ty-radius-h/2);yhi=min(yhi,ty+radius-h/2)
 for yy in ys[bisect.bisect_left(ys,ylo):bisect.bisect_right(ys,yhi)]:
  yc=yy+h/2;lo=-10**9;hi=10**9
  for px,py,r in ([(CX,CY,ENV)] if inner else [])+list(pinlimits):
   remaining=r-abs(yc-py)
   if remaining<0:lo=1;hi=0;break
   lo=max(lo,px-remaining-w/2);hi=min(hi,px+remaining-w/2)
  if binbox:lo=max(lo,binbox[0]);hi=min(hi,binbox[2]-w)
  if lo>hi:continue
  for rr in byy[yy]:
   a0,_,b0,_=rr['bbox'];left=max(a0,lo);right=min(b0-w,hi)
   if left>right:continue
   for a,b in free_segments(left,right+w,occ[yy]+block[yy]):
    low=a0+math.ceil((a-a0)/SW)*SW;high=a0+math.floor((b-w-a0)/SW)*SW
    if low>high:continue
    xx=max(low,min(high,a0+round((tx-w/2-a0)/SW)*SW));dist=abs(xx+w/2-tx)+abs(yc-ty)
    if radius is None or dist<=radius:options.append((dist,abs(yc-ty),xx,yy,rr['orient']))
 if not options:return None
 _,_,x,y,orient=min(options);return x,y,w,h,orient

def put(name,tx,ty,inner,limits,search=(2000,5400,10000,25000,60000,200000)):
 for r in search:
  q=find(name,tx,ty,inner,limits,radius=r)
  if q:reserve(name,*q);return
 raise RuntimeError(('NO_NATIVE_SITE',name,inner,limits,tx,ty))
outer=collections.defaultdict(list)
for n,a in anchors.items():
 if n in selected:continue
 p=a[0];f='W' if p['x']<2 else ('E' if p['x']>248.56 else ('S' if p['y']<2 else 'N'));outer[f].append((n,p))
for f,items in outer.items():
 items.sort(key=lambda q:q[1]['y'] if f in ['W','E'] else q[1]['x'])
 for k,(n,p) in enumerate(items):
  d=6000+2200*(k%10);px,py=round(p['x']*1000),round(p['y']*1000);tx,ty=px,py
  if f=='W':tx+=d
  elif f=='E':tx-=d
  elif f=='S':ty+=d
  else:ty-=d
  put(n,tx,ty,False,[(px,py,30000)])
print('OUTER_PUBLIC_PLACED',len(poses),flush=True)
for n in sorted(selected|{por_ff}):
 p=anchors[n][0] if n in anchors else pins['por_n'];px,py=round(p['x']*1000),round(p['y']*1000);dx,dy=px-CX,py-CY;scale=min(1,122000/max(1,abs(dx)+abs(dy)));put(n,CX+dx*scale,CY+dy*scale,True,[(px,py,145000)])
print('CENTERED_SPECIAL_PLACED',len(poses),flush=True)
heap=[]
for j in range(ny):
 for i in range(nx):
  x=(i+.5)*bw*1000;y=(j+.5)*bw*1000
  if abs(x-CX)+abs(y-CY)>ENV:continue
  if any(float(m['x'])*1000-4320<x<(float(m['x'])+float(m['w']))*1000+4320 and float(m['y'])*1000-4320<y<(float(m['y'])+float(m['h']))*1000+4320 for m in macros):continue
  heapq.heappush(heap,(areas[i,j]/barea(i,j),cellbin[i,j],j,i))
for n in sorted(ffs.keys()-poses.keys()):
 while heap:
  density,count,j,i=heapq.heappop(heap);area=barea(i,j)
  if abs(density-areas[i,j]/area)>1e-9 or count!=cellbin[i,j]:continue
  bx=(i*bw*1000,j*bw*1000,min(250.56,(i+1)*bw)*1000,min(285.12,(j+1)*bw)*1000);q=find(n,(bx[0]+bx[2])/2,(bx[1]+bx[3])/2,True,binbox=bx)
  if not q:continue
  reserve(n,*q);heapq.heappush(heap,(areas[i,j]/area,cellbin[i,j],j,i));break
 else:raise RuntimeError(('INTERNAL_HEAP_EXHAUSTED',n,len(poses)))
assert len(poses)==18768
changed_master=[]
for n,p in poses.items():
 i=ids[n];c=D.cells[i];x,y=p['ll_dbu'];w,h=p['size_dbu'];D.cells[i]=tuple([c[0],p['master'],x/1000,y/1000,(x+w)/1000,(y+h)/1000]+list(c[6:]))
 if ffs[n]['master']!=p['master']:changed_master.append(n)
assert len(changed_master)==54
rr=G.r2r_metrics(D);pr=G.pin_reg_metrics(D,re.compile(G.STRAP_RE_DEFAULT));original=D.cells;D.cells={i:c for i,c in original.items() if c[0] in 'SM'};ffarea=G.area_metrics(D);D.cells=original
public_dist=[(abs(G.ctr(D.cells[ids[n]])[0]-p['x'])+abs(G.ctr(D.cells[ids[n]])[1]-p['y']),p['name']) for n,ps in anchors.items() for p in ps]
report=dict(status='NATIVE_FF_SITE_PREP_NOT_PLACE',FFs=len(poses),target_master_resizes=len(changed_master),native_rows=len(rows['rows']),native_taps=sum(x['kind']=='tap' for x in raw),public_DATA_max=max(public_dist),public_DATA_gt150=sum(x[0]>150 for x in public_dist),public_DATA_gt30=sum(x[0]>30 for x in public_dist),R2R=rr,pins=pr,FF_only_density=ffarea,reset_anchor_FF=por_ff,ordinary_combinational_placement='NOT RUN; channel model/PG coupling still OPEN')
(O/'FF_site_report.json').write_text(json.dumps(report,indent=2)+'\n');(O/'FF_sites.json.gz').write_bytes(gzip.compress(json.dumps(list(poses.values()),separators=(',',':')).encode(),mtime=0));print(json.dumps(report,indent=2))
