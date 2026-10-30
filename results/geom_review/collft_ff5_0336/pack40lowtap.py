from pathlib import Path
import sys,json,re,math
from collections import defaultdict,Counter
import numpy as np
b=Path('/srv/opentallas-scratch2/claude/codex-collft-ff5-0336');w=Path('/srv/opentallas-scratch2/claude/wt/codex-qc-kits-0336');sys.path.insert(0,str(b));import geom_rules as G
p=b/'planned_geom_nf40low.tsv';D=G.Design(p);plan=json.load(open(b/'plan/plan_qc46.json'));t=plan['partition_types']['coll_ft__cla4a25d77'];bands=t['clock']['landing_contract']['bands']
# FF-only physical strips. Full tile, logical nets, IO pins and clocks remain unchanged.
rects={'crec_rx_s1_i':[4.32,4.32,118.656,30.24], 'crec_rx_s2_i':[119.616,4.32,233.968,30.24], 'crec_tx_s1_i':[234.928,963.36,349.68,989.28], 'crec_tx_s2_i':[350.64,963.36,464.816,989.28], 'fltk_i':[452.056,4.32,460.696,30.24], 'fltv_i':[465.416,4.32,474.056,30.24]}
ps=json.load(open(b/'pins.json'))
pins={(q['bus'],q['bit']):q for q in ps};pinranges={n:sorted([q for q in ps if q['bus']==n],key=lambda q:q['bit']) for n in rects}
owned_moving={q["name"].replace(chr(92),"") for q in json.load(open(b/"anchors_nf40lowtap.json"))["anchors"]}
fixed_status={line.replace('\\t','\t').split('\t')[0].replace('\\','') for line in (b/'face_placement_baseline.tsv').read_text().splitlines() if 'cland:status:' in line}
byring=defaultdict(list);protected=[]
for cid,c in D.cells.items():
 if c[0]!='S':continue
 nm=c[6].replace('\\','')
 if nm in fixed_status:protected.append((cid,c));continue
 m=re.search(r'u_cland_([^/]+)/',nm)
 if m and m[1] in rects:byring[m[1]].append((cid,c,nm))
 elif any(x in nm for x in ('u_cland_origin/','u_cland_fstart_','u_cland_rst_','u_cland_reset_','u_rrl_','u_rst_in/')):protected.append((cid,c))
ring_ids={a[0] for v in byring.values() for a in v}; protected_ids={a[0] for a in protected}
core=D.extra['core'];sx=.054;rh=.27;xbase,ybase=core[:2];placed={};stats={};pad=0
for n,rect in rects.items():
 ax,ay,bx,by=rect;i0=math.ceil((ax-xbase)/sx-1e-6);i1=math.floor((bx-xbase)/sx+1e-6);j0=math.ceil((ay-ybase)/rh-1e-6);j1=math.floor((by-ybase)/rh+1e-6)
 occ=np.zeros((j1-j0,i1-i0),dtype=bool)
 # Exact complete pre-anchor occupancy already includes software reservations as well as every fixed body.
 for line in (b/"pre_anchor_occupancy.tsv").read_text().splitlines()[1:]:
  rr,lo,hi=map(int,line.split(chr(9)));jj=rr-j0
  l=max(0,math.floor((lo/1000-xbase)/sx+1e-6)-i0);r=min(i1-i0,math.ceil((hi/1000-xbase)/sx-1e-6)-i0)
  if 0<=jj<occ.shape[0] and l<r:occ[jj,l:r]=True
 # Exact runtime fixed-cell census includes physical TAP cells omitted by AUTO-GEOM.
 for line in (b/'fixed_sites.tsv').read_text().splitlines():
  if line.split(chr(9))[0].replace(chr(92),"") in owned_moving:continue
  fields=line.split('\t');x0,y0,x1,y1=map(float,fields[3:7])
  l=max(0,math.floor((x0-xbase)/sx)-i0);r=min(i1-i0,math.ceil((x1-xbase)/sx)-i0)
  lo=max(0,math.floor((y0-ybase)/rh)-j0);hi=min(j1-j0,math.ceil((y1-ybase)/rh)-j0)
  if l<r and lo<hi:occ[lo:hi,l:r]=True
 for cid,c in D.cells.items():
  if cid in ring_ids:continue
  if D.extra.get('status',{}).get(cid) not in ('FIRM','LOCKED') and cid not in protected_ids:continue
  l=max(0,math.floor((c[2]-xbase)/sx)-i0-pad);r=min(i1-i0,math.ceil((c[4]-xbase)/sx)-i0+pad);lo=max(0,math.floor((c[3]-ybase)/rh)-j0);hi=min(j1-j0,math.ceil((c[5]-ybase)/rh)-j0)
  if l<r and lo<hi:occ[lo:hi,l:r]=True
 north=n.startswith('crec_tx');payload=[];ctl=[]
 for cid,c,nm in byring[n]:
  m=re.search(r'u_ring\.s_d\[\d+\]\[(\d+)\]',nm)
  if m:bit=int(m[1]);payload.append((bit,cid,c,nm));continue
  m=re.search(r'u_ring\.dch\[(\d+)\]\.u_dsel/y\[(\d+)\]',nm)
  if m:bit=64*int(m[1])+int(m[2]);payload.append((bit,cid,c,nm));continue
  ctl.append((cid,c,nm))
 reserves={cid:math.ceil((c[4]-c[2])/sx/0.4-1e-6) for cid,c,_ in byring[n]}
 valid={}
 for rw in set(reserves.values()):
  psum=np.concatenate((np.zeros((occ.shape[0],1),dtype=int),np.cumsum(occ,axis=1)),axis=1)
  valid[rw]=(psum[:,rw:]-psum[:,:-rw])==0
 def assign(cid,c,target):
  cw=round((c[4]-c[2])/sx);ch=round((c[5]-c[3])/rh);tx,ty=target;rw=reserves[cid]
  if ch!=1:raise RuntimeError('Only actual one-row FFs supported')
  free=valid[rw]
  xs=xbase+(i0+np.arange(free.shape[1]))*sx+(c[4]-c[2])/2
  ys=ybase+(j0+np.arange(free.shape[0]))*rh+(c[5]-c[3])/2
  costs=np.abs(ys[:,None]-ty)+np.abs(xs[None,:]-tx)
  costs=np.where(free,costs,np.inf);ind=int(np.argmin(costs));jj,ii=np.unravel_index(ind,costs.shape);cost=float(costs[jj,ii])
  if cost<=60.01:
   occ[jj,ii:ii+rw]=True
   for other,mask in valid.items():mask[jj,max(0,ii-other+1):min(mask.shape[1],ii+rw)]=False
   x=xbase+(i0+ii)*sx;y=ybase+(j0+jj)*rh;placed[cid]=dict(name=c[6],master=c[1],origin_um=[round(x,6),round(y,6)],target_xy=target,pin_dist_um=round(cost,4),reserved_width_um=rw*sx,ring=n);return
  raise RuntimeError(f'No <=60um free reserved footprint for {n} {c[6]}, target{target}, cellsplaced{len(placed)}')
 fstart=next((q for q in t['clock']['landing_contract']['pins'] if q['name']=='cland_fstart_in_'+n),None)
 if fstart:target=tuple(fstart['xy_um'])
 else:target=(sum(q['x'] for q in pinranges[n])/len(pinranges[n]),pinranges[n][0]['y'])
 for cid,c,nm in sorted(ctl,key=lambda a:a[2]):assign(cid,c,target)
 def constrained_first(v):
  bit=v[0];q=pins.get((n,bit))
  if q is None:return(1e9,bit)
  return(min(q['x']-ax,bx-q['x']),bit)
 for bit,cid,c,nm in sorted(payload,key=constrained_first):
  q=pins.get((n,bit))
  if q is None:raise RuntimeError(f'Unmapped payload {n}:{bit}')
  assign(cid,c,(q['x'],q['y']))
 area=sum((c[4]-c[2])*(c[5]-c[3]) for _,c,_ in byring[n]);stats[n]=dict(ffs=len(byring[n]),area_um2=area,rect_um=rect,fill=area/((bx-ax)*(by-ay)),payload=len(payload),controls=len(ctl))
for n,rect in rects.items():bands[n]['rect_um']=rect;bands[n]['note']='CODEX proposed FF-only near-face strip; payload global-bit-correlated; ring combinational logic remains movable; no RTL or cycle change'
plan['note']+='; CODEX coll_ft near-face FF-strip candidate, held on independent START/reset/clock failures'
(b/'plan/plan_collft_nf40lowtap.json').write_text(json.dumps(plan,indent=2)+'\n');(b/'anchors_nf40lowtap.json').write_text(json.dumps(dict(schema='codex.collft.ff_anchors.v1',anchors=list(placed.values()),protected=[dict(name=c[6],origin_um=[c[2],c[3]]) for _,c in protected],stats=stats),indent=2)+'\n')
lines=[]
for line in p.read_text().splitlines():
 a=line.split('\t')
 if a[0]=='C' and int(a[1]) in placed:
  v=placed[int(a[1])];c=D.cells[int(a[1])];x,y=v['origin_um'];a[4:8]=[f'{x:.6f}',f'{y:.6f}',f'{x+c[4]-c[2]:.6f}',f'{y+c[5]-c[3]:.6f}'];line='\t'.join(a)
 lines.append(line)
(b/'planned_geom_nf40lowtap.tsv').write_text('\n'.join(lines)+'\n');print(json.dumps(stats,indent=2));print('PLANNED_ANCHORS',len(placed),'PROTECTED_START_RESET',len(protected))
