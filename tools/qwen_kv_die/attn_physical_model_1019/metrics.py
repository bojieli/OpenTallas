import json,pathlib,collections,math,hashlib
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Rectangle
r=pathlib.Path('.');d=json.loads((r/'placed_geometry.json').read_text());c=json.loads((r/'census.json').read_text());cells=d['cells'];ports=d['ports'];rows=d['rows']
def xyport(n):
 z=ports[n]['boxes'][0];return ((z[0]+z[2])/2,(z[1]+z[3])/2)
def xycell(n,p):return cells[n]['pins'][p]
def dist(a,b):return abs(a[0]-b[0])+abs(a[1]-b[1])
facepins=collections.defaultdict(list)
for n in ports:
 x,y=xyport(n);face='W' if x<.1 else 'E' if x>215.9 else 'S' if y<.1 else 'N';facepins[face].append(y if face in 'EW' else x)
spacing={f:min(b-a for a,b in zip(sorted(v),sorted(v)[1:])) for f,v in facepins.items()}
area=sum((z['bbox'][2]-z['bbox'][0])*(z['bbox'][3]-z['bbox'][1]) for z in cells.values());rowarea=sum((z[2]-z[0])*(z[3]-z[1]) for z in rows)
netrows=[];edges=collections.defaultdict(list);indeg=collections.Counter();ff={n for n,z in cells.items() if 'DFF' in z['master']}
for n,net in d['nets'].items():
 drivers=[(ci,p,xycell(ci,p)) for ci,p,di in net['cells'] if di=='OUTPUT']+[(None,p,xyport(p)) for p in net['ports'] if ports[p]['direction']=='INPUT'];loads=[(ci,p,xycell(ci,p)) for ci,p,di in net['cells'] if di=='INPUT']+[(None,p,xyport(p)) for p in net['ports'] if ports[p]['direction']=='OUTPUT']
 if not drivers:continue
 assert len(drivers)==1,(n,drivers)
 ci,p,xy=drivers[0]
 for li,lp,lxy in loads:
  if lp.upper() in ('CLK','CK'):continue
  v=dist(xy,lxy);netrows.append({'net':n,'driver':[ci,p],'load':[li,lp],'manhattan_um':v,'role':'reset' if lp.upper() in ('RESETN','RN','RESET','R','SN','SETN') else 'data_control'})
  if ci in ff or ci is None:src='ROOT:'+str(ci)+':'+p
  else:src=ci
  if li in ff or li is None:dst='END:'+str(li)+':'+lp
  else:dst=li
  edges[src].append((dst,v,n));indeg[dst]+=1;indeg[src]+=0
q=collections.deque(z for z,v in indeg.items() if v==0);best={z:(0,[]) for z in q};processed=0
while q:
 z=q.popleft();processed+=1
 for dst,v,n in edges[z]:
  cand=best[z][0]+v
  if dst not in best or cand>best[dst][0]:best[dst]=(cand,best[z][1]+[n])
  indeg[dst]-=1
  if indeg[dst]==0:q.append(dst)
worst=max(best.items(),key=lambda z:z[1][0]);ffpoints=[((cells[n]['bbox'][0]+cells[n]['bbox'][2])/2,(cells[n]['bbox'][1]+cells[n]['bbox'][3])/2) for n in ff];centroid=[sum(z[i] for z in ffpoints)/len(ffpoints) for i in (0,1)]
result={'source_sha256':c['source_sha256'],'cells':len(cells),'FF':len(ff),'hard_macros':sum(z['block'] for z in cells.values()),'cell_area_um2':area,'row_capacity_um2':rowarea,'row_utilization':area/rowarea,'outline_um':[216,216],'active_band_um':[2.16,86.4,213.84,129.6],'face_counts':{f:len(v) for f,v in facepins.items()},'minimum_face_pin_center_spacing_um':spacing,'ck_xy':xyport('ck'),'FF_centroid':centroid,'clock_to_FF_centroid_Manhattan_um':dist(xyport('ck'),centroid),'max_single_net_manhattan':max(netrows,key=lambda z:z['manhattan_um']),'max_reset_net_manhattan':max((z for z in netrows if z['role']=='reset'),key=lambda z:z['manhattan_um'],default=None),'nets_over405':[z for z in netrows if z['manhattan_um']>405],'max_stage_sum_manhattan_um':worst[1][0],'max_stage_nets':worst[1][1],'unresolved_comb_nodes':sum(v>0 for v in indeg.values()),'placement_status':dict(collections.Counter(z['status'] for z in cells.values())),'qualified_timing':False,'qualified_route':False}
(r/'metrics.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
fig,ax=plt.subplots(figsize=(10,10));ax.add_patch(Rectangle((0,0),216,216,fill=False,color='black'));patches=[Rectangle((z['bbox'][0],z['bbox'][1]),z['bbox'][2]-z['bbox'][0],z['bbox'][3]-z['bbox'][1]) for z in cells.values()];ax.add_collection(PatchCollection(patches,facecolor='#2878b5',alpha=.7,linewidth=0));ps=[xyport(n) for n in ports];ax.scatter([z[0] for z in ps],[z[1] for z in ps],s=2,c='#888888');cx,cy=xyport('ck');ax.scatter([cx],[cy],c='red',s=70,zorder=5,label='ck');ax.scatter([centroid[0]],[centroid[1]],c='orange',s=70,zorder=5,label='FF centroid');ax.set(xlim=(-6,222),ylim=(-6,222),aspect='equal',xlabel='um',ylabel='um',title='ATTN source6326 / actual R2 native cells\nPlacement-only; 216 square, central43.2um band; no CTS/route');ax.legend();fig.savefig(r/'placement.png',dpi=160)
