from pathlib import Path
from collections import Counter
import sys,json,math
import numpy as np
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as g
P=Path(__file__).parent;D=g.Design('/home/ubuntu/coord/tmp/codex-hbm-bfqg-compact-kit-1101/corrected_guide_place/geom.tsv');CUT=107.5;LEFT,RIGHT=10,17
layers=[(n,p)for n,(direction,p)in D.extra['tech'].items()if direction.upper().startswith('V')and 2<=g._layer_idx(n)<=5];full=sum(g.TRACK_DERATE/p for n,p in layers);nb=math.ceil(D.die[2]-D.die[0]);cap=np.full(nb,full);active=[]
for cid,c in D.cells.items():
 if c[0]!='M'or not c[3]<CUT<c[5]:continue
 keep=sum(g.TRACK_DERATE/p for n,p in layers if n not in D.extra['mobs'].get(c[1],set()));a,b=int(c[2]),math.ceil(c[4]);cap[a:b]=np.minimum(cap[a:b],keep);active.append(dict(id=cid,name=c[6],box=list(c[2:6]),modeled_macro_bins=[a,b],open_vertical_layers=[n for n,p in layers if n not in D.extra['mobs'].get(c[1],set())]))
def bbox(index):
 sig,dr,sk=D.nets[index]
 if sig=='CLOCK':return None
 xs=[];ys=[];mac=[];members=[]
 for e in([dr]if dr else[])+sk:
  if e[0]=='p':
   p=D.pin_by_k[e[1]];xs.append(p['x']);ys.append(p['y']);members.append(dict(kind='port',name=p['name'],xy=[p['x'],p['y']]))
  else:
   c=D.cells[e[1]]
   if c[0]=='M':mac.append((e[1],c));continue
   x,y=g.ctr(c);xs.append(x);ys.append(y);members.append(dict(kind='cell',id=e[1],name=c[6],xy=[x,y]))
 gx=sum(xs)/len(xs)if xs else None;gy=sum(ys)/len(ys)if ys else None
 for cid,c in mac:
  if gx is None:gx,gy=g.ctr(c)
  px,py=min(max(gx,c[2]),c[4]),min(max(gy,c[3]),c[5])
  if c[2]<px<c[4]and c[3]<py<c[5]:
   dl,dr_,db,dt=px-c[2],c[4]-px,py-c[3],c[5]-py;k=min(dl,dr_,db,dt);px=c[2]if k==dl else c[4]if k==dr_ else px;py=c[3]if k==db else c[5]if k==dt else py
  xs.append(px);ys.append(py);members.append(dict(kind='macro_projected',id=cid,name=c[6],xy=[px,py]))
 if len(xs)<2:return None
 return [min(xs),min(ys),max(xs),max(ys)],members
rows=[];whole=[]
for i in range(len(D.nets)):
 b=bbox(i)
 if b is None:continue
 bb,members=b
 if not bb[1]<CUT<bb[3]:continue
 a,z=max(0,min(nb-1,int(bb[0]))),max(0,min(nb-1,int(bb[2])));total=float(cap[a:z+1].sum());over=float(cap[max(a,LEFT):min(z+1,RIGHT)].sum())if max(a,LEFT)<min(z+1,RIGHT)else 0
 row=dict(net_index=i,signal_type=D.nets[i][0],box=bb,model_bins=[a,z+1],model_span_capacity=total,hot_window_weight=over/total if total else 0,members=members)
 whole.append(row)
 if row['hot_window_weight']>0:rows.append(row)
capacity=float(cap[LEFT:RIGHT].sum());demand=sum(r['hot_window_weight']for r in rows);sensitivity=[]
for ext in[0,1,2,4,8]:
 dem=0
 for r in whole:
  a=max(0,r['model_bins'][0]-ext);z=min(nb,r['model_bins'][1]+ext);total=float(cap[a:z].sum());over=float(cap[max(a,LEFT):min(z,RIGHT)].sum())if max(a,LEFT)<min(z,RIGHT)else 0
  if total:dem+=over/total
 sensitivity.append(dict(extra_x_bin_each_side_um=ext,hot_allocated_crossings=dem,hot_ratio=dem/capacity))
# Read-only fractional-bin sensitivity at the actual macro edge, no production rule change.
frac_cap=np.full(nb,full)
for item in active:
 x0,y0,x1,y1=item['box'];keep=sum(g.TRACK_DERATE/p for n,p in layers if n in item['open_vertical_layers'])
 for ix in range(int(x0),math.ceil(x1)):
  overlap=max(0,min(ix+1,x1)-max(ix,x0));frac_cap[ix]=min(frac_cap[ix],full*(1-overlap)+keep*overlap)
end=17.28;hot=np.zeros(nb);hot[LEFT:17]=1;hot[17]=.28*full/frac_cap[17];dem=0;count=0
for r in whole:
 a,z=r['model_bins'];total=float(frac_cap[a:z].sum());over=float((frac_cap[a:z]*hot[a:z]).sum())
 if total and over:dem+=over/total;count+=1
capacity=float((frac_cap*hot).sum())
res=dict(scope='Analytical fractional-bin/actual-free-edge sensitivity only; no production rule rewrite or physical gate waiver',hot_window=[10,end],hot_capacity_tracks=capacity,weighted_demand=dem,ratio=dem/capacity,contributor_count=count,bin17_capacity=float(frac_cap[17]),note='Actual free 0.28um portion of bin17 has full M3/M5 capacity; full-net bbox endpoints remain original integer bins. Sensitivity only.')
(P/'fractional_edge_sensitivity.json').write_text(json.dumps(res,indent=1)+'\n');print(res)
