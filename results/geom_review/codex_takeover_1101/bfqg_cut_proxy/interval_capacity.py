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
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import maximum_flow
EXT=int(__import__('os').environ.get('EXT','0'));n=len(whole);source=n+nb;sink=source+1;rr=[];cc=[];vv=[];scale=48
for i,r in enumerate(whole):
 rr.append(source);cc.append(i);vv.append(scale)
 a,z=r['model_bins'];a=max(0,a+EXT*-1);z=min(nb,z+EXT)
 for j in range(a,z):
  if cap[j]>0:rr.append(i);cc.append(n+j);vv.append(scale)
for j in range(nb):rr.append(n+j);cc.append(sink);vv.append(round(float(cap[j])*scale))
mat=coo_matrix((vv,(rr,cc)),shape=(sink+1,sink+1),dtype=np.int64).tocsr();f=maximum_flow(mat,source,sink)
r=dict(scope='READ-ONLY single-cut interval-capacity feasibility on unchanged proxy bboxes/capacity; no routing/geometry gate waiver',bbox_extension_um=EXT,cut_y_um=CUT,nets=n,required_units=n*scale,flow_units=int(f.flow_value),all_bbox_cut_demands_assignable=int(f.flow_value)==n*scale,scale_units_per_crossing=scale,hot_capacity_tracks=float(cap[LEFT:RIGHT].sum()),hot_assigned_crossings=sum(int(f.flow[n+j,sink])for j in range(LEFT,RIGHT))/scale,note='Maxflow reallocates fractional crossings within each original endpoint xbbox. It does not create native routes or check access/other cuts/layer continuity.')
(P/('interval_capacity_feasibility_'+str(EXT)+'.json')).write_text(json.dumps(r,indent=1)+'\n');print(r)
