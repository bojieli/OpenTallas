"""PREP only: per-bit FF targets and real widest-drive row footprints; no ODB edit."""
from pathlib import Path
import json,re,math,collections
import geom_rules as G
R=Path(__file__).resolve().parent
D=G.Design('/srv/opentallas-scratch/claude/wt/codex-kv-physical-1101/results/kv_hroot_reloc_1131_A4_actual.tsv')
def family(n):return re.sub(r'x(?:\d+|p\d+)(?=_ASAP7_)','xDRIVE',n)
growth={}
for g in json.loads(Path('/home/ubuntu/coord/tmp/codex-kv-hhp-parent-1131/ring_inventory7.json').read_text())['groups']:
 for f in g['ff']:growth[family(f['master'])]=max(growth.get(family(f['master']),0),f['max_drive_width_um'])
groups=[]
for line in (R/'landing_placement_A4.tcl').read_text().splitlines():
 m=re.match(r'\s*\{(u_cland_\S+) \{([0-9. ]+)\} (ring:[^}]+)\}',line)
 if m:groups.append(dict(prefix=m[1],old_rect=list(map(float,m[2].split())),tag=m[3],bus=m[3].split(':')[1].split('+')[0]))
lr=G.land_ring_captures(D,json.loads((R/'land_slots.json').read_text()),json.loads((R/'face_guard.json').read_text()))
pins=collections.defaultdict(dict)
for p in D.pins:
 m=re.fullmatch(r'(.*)\[(\d+)\]',p['name'])
 if m:pins[m[1]][int(m[2])]=p
names={c[-1]:i for i,c in D.cells.items()}
members={g['prefix']:[i for i,c in D.cells.items() if c[0]=='S' and ('u_bound.'+g['prefix']+'/') in c[-1]] for g in groups}
all_ring={i for x in members.values() for i in x}
native=lambda n:any(t in n for t in ('u_bin_','u_bout_','u_ist_'))
SX=.054;SY=.27;X0=4.32;Y0=4.32
occ=collections.defaultdict(list)
def reserve(x,y,w,h,label):
 a=math.floor((y-Y0+1e-6)/SY);b=math.ceil((y+h-Y0-1e-6)/SY)
 for row in range(a,b):occ[row].append((x,x+w,label))
for i,c in D.cells.items():
 if i not in all_ring and not native(c[-1]) and (c[0]=='S' or D.extra['status'].get(i) in ('FIRM','LOCKED','FIXED')):
  reserve(c[2],c[3],c[4]-c[2],c[5]-c[3],c[-1])
def free(x,y,w,h):
 a=round((y-Y0)/SY);b=a+math.ceil(h/SY-1e-8)
 return all(not(x<r-1e-7 and x+w>l+1e-7) for row in range(a,b) for l,r,_ in occ[row])
def place(i,rect,target):
 c=D.cells[i];w=max(c[4]-c[2],growth.get(family(c[1]),c[4]-c[2]));h=c[5]-c[3]
 ax,ay,bx,by=rect
 xs=range(math.ceil((ax-X0-1e-7)/SX),math.floor((bx-w-X0+1e-7)/SX)+1)
 ys=range(math.ceil((ay-Y0-1e-7)/SY),math.floor((by-h-Y0+1e-7)/SY)+1)
 # Search rows near the pin, then nearest x interval. Every selected site has its real max-drive footprint free.
 tx,ty=target;best=None
 for ry in sorted(ys,key=lambda z:abs(Y0+z*SY+h/2-ty)):
  y=Y0+ry*SY;dy=abs(y+h/2-ty)
  if best and dy>=best[0]:break
  intervals=sorted((l,r) for l,r,_ in occ[ry]);segments=[];left=ax
  for l,r in intervals+[(bx,bx)]:
   if l>left:segments.append((left,min(l,bx)))
   left=max(left,r)
   if left>=bx:break
  for l,r in segments:
   lo=math.ceil((max(ax,l)-X0-1e-7)/SX);hi=math.floor((min(bx,r)-w-X0+1e-7)/SX)
   if lo>hi:continue
   rx=max(lo,min(hi,round((tx-w/2-X0)/SX)));x=X0+rx*SX
   if not free(x,y,w,h):continue
   score=abs(x+w/2-tx)+dy
   if best is None or score<best[0]:best=(score,x,y,w,h)
 if best is None:raise RuntimeError('NO_LEGAL_FOOTPRINT '+c[-1])
 _,x,y,rw,h=best;reserve(x,y,rw,h,c[-1]);dx=x-c[2];dy=y-c[3];q=list(c);q[2]+=dx;q[4]+=dx;q[3]+=dy;q[5]+=dy;D.cells[i]=tuple(q)
 return dict(name=c[-1],master=c[1],old=list(G.ctr(c)),new=list(G.ctr(q)),reserved_width_um=rw,height_um=h,pin_target=list(target),target_distance_um=best[0])
out=[]
for g in groups:
 pp=pins[g['bus']];assert pp,g
 a=g['old_rect'];E=min(p['x'] for p in pp.values())>1800
 if E:rect=[a[0]+12.96,a[1],a[2]+12.96,a[3]]
 else:rect=[a[0],4.32,a[2],4.32+a[3]-a[1]]
 # The one wide SLG band uses an active subwindow inside its unchanged reserved rectangle.
 if g['bus']=='i_slg_Q_N_o_ctl':
  rect=[max(rect[0],928.8),rect[1],min(rect[2],961.2),rect[3]]
 oldwidth=g['old_rect'][2]-g['old_rect'][0];g['reserved_rect']=([a[0]+12.96,a[1],a[2]+12.96,a[3]] if E else [a[0],4.32,a[2],4.32+a[3]-a[1]])
 g['active_ff_rect']=rect
 start=next((p for p in D.pins if p['name'] in ('cland_fstart_in_'+g['bus'],'cland_fstart_in_'+g['bus']+'[0]')),None)
 near=min(pp,key=lambda k:abs(pp[k]['x']-(start or pp[k])['x'])+abs(pp[k]['y']-(start or pp[k])['y'])) if start else min(pp)
 ff=members[g['prefix']];wch=1+max([-1]+[int(m[1]) for i in ff if (m:=re.search(r'dch\[\d+\]\.u_dsel/y\[(\d+)\]',D.cells[i][-1].replace('\\','')))])
 def key(i):
  n=D.cells[i][-1].replace('\\','');m=re.search(r's_d\[(\d+)\]\[(\d+)\]',n)
  if m and int(m[2]) in pp:return int(m[2]),int(m[1])
  m=re.search(r'dch\[(\d+)\]\.u_dsel/y\[(\d+)\]',n)
  if m and int(m[1])*wch+int(m[2]) in pp:return int(m[1])*wch+int(m[2]),999
  return near,998
 for i in sorted(ff,key=key):
  k,_=key(i);p=pp[k];target=(rect[2]-.6,p['y']) if E else (p['x'],rect[1]+.135)
  out.append(place(i,rect,target))
print('placed model',len(out),'rings',len(groups))
fclks=set(re.findall(r'\.fclk\((fclk_in_\w+)\)',(R/'native_bound.sv').read_text()))
clock_pins=set(lr['clock_exports'])
for name in fclks:
 actual=[p['name'] for p in D.pins if p['name']==name or p['name']==name+'[0]'];assert len(actual)==1,(name,actual);clock_pins.update(actual)
metrics=G.pin_reg_metrics(D,re.compile(r'^strap_'),clock_pins=clock_pins,land=lr['caps'])
bad=[];rr=G.r2r_metrics(D,capture_pairs=bad)
print(metrics);print(rr)
result=dict(status='PREP physical-footprint model only; no ODB mutation. Native endpoint re-solve, exact reset/clock graph+startup join still held.',groups=groups,moves=out,pin_metrics=metrics,raw_r2r=rr,raw_bad_pairs=bad)
(R/'ring_footprint_proposal.json').write_text(json.dumps(result,indent=2))

src=Path('/srv/opentallas-scratch/claude/wt/codex-kv-physical-1101/results/kv_hroot_reloc_1131_A4_actual.tsv')
with (R/'model_ring.tsv').open('w') as f:
 for line in src.open():
  if line.startswith('C\t'):
   a=line.rstrip().split('\t');c=D.cells[int(a[1])];a[4:8]=[f'{v:.6f}' for v in c[2:6]];line='\t'.join(a)+'\n'
  f.write(line)
(R/'source_clock_pin_classification.json').write_text(json.dumps(dict(native_fclk_calls=sorted(fclks),actual_clock_pins=sorted(clock_pins)),indent=2))
