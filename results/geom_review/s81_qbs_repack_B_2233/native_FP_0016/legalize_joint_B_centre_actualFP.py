from pathlib import Path
import json,pickle,sys,math,collections
import numpy as np
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as G
from exact_cones import physical_port_map
P=Path('/home/ubuntu/coord/tmp/codex-hist-anchor-2100');C=json.load(open(P/'repack_B_centre_actualFP_complete.json'));D=G.Design(P/'geom.tsv');adj=pickle.load(open(P/'exact_allff_adjacency.pickle','rb'));ports=physical_port_map(C);J=json.load(open(P/'joint_repack_B_targets.json'));target={a['cid']:np.array(a['center_um'])for a in J['targets']};original=dict(D.cells);fixed={x['cid']for x in C['fixed']};rows=C['rows'];core=C['core_um'];sx=.054;sy=.270;xs=min(r['origin'][0]for r in rows);ys=min(r['origin'][1]for r in rows);nx=math.ceil((core[2]-xs)/sx)+2;ny=math.ceil((core[3]-ys)/sy)+2;free=np.zeros((ny,nx),bool);rr=collections.defaultdict(list)
for r in rows:
 i=round((r['origin'][0]-xs)/sx);j=round((r['origin'][1]-ys)/sy);free[j,i:i+r['count']]=True;rr[j].append((i,i+r['count'],r['name'],r['orient']))
def block(box):
 x0,y0,x1,y1=box;i0=max(0,math.floor((x0-xs)/sx+1e-6));i1=min(nx,math.ceil((x1-xs)/sx-1e-6));j0=max(0,math.floor((y0-ys)/sy+1e-6));j1=min(ny,math.ceil((y1-ys)/sy-1e-6));free[j0:j1,i0:i1]=False
for x in C['fixed']:
 b=x['bbox_um'];m=4.32 if x['cid']in D.cells and D.kind(x['cid'])=='M'else 0;block([b[0]-m,b[1]-m,b[2]+m,b[3]+m])
block(C['proposal']['clock_entry']['driver_bay_um']);block([core[0],core[1],core[0]+8.64,core[3]]);block([core[0],core[3]-8.64,core[2],core[3]])
anchor={};selected=[];positions=dict(target)
for cid,xy in target.items():
 c=D.cells[cid];i=round((c[2]-xs)/sx);j=round((c[3]-ys)/sy);n=round((c[4]-c[2])/sx)
 if cid in fixed:
  positions[cid]=np.array(G.ctr(c));anchor[cid]=dict(cid=cid,name=c[6],origin_um=list(c[2:4]),size_um=[c[4]-c[2],sy],orient=None,row=None,preserve_original=True);continue
 if max(abs(xy-np.array(G.ctr(c))))<1e-6 and free[j,i:i+n].all():
  free[j,i:i+n]=False;positions[cid]=np.array(G.ctr(c));anchor[cid]=dict(cid=cid,name=c[6],origin_um=list(c[2:4]),size_um=[c[4]-c[2],sy],orient=None,row=None,preserve_original=True)
 else:selected.append(cid)
def bounds(cid):
 pp=[positions[n]for n in adj[cid][0]if n!=cid]
 for mk in adj[cid][1]:pp.extend(np.array([x,y])for x,y,_ in ports[mk])
 if not pp:return np.array([-1e4,-1e4]),np.array([1e4,1e4])
 q=np.array(pp);uv=np.column_stack((q[:,0]+q[:,1],q[:,0]-q[:,1]));return uv.max(axis=0)-404.946,uv.min(axis=0)+404.946
# Tight polygon first, then larger cells. All yet-unassigned neighbors use the proven402um continuous targets.
selected.sort(key=lambda c:(float(np.prod(np.maximum(bounds(c)[1]-bounds(c)[0],0))),-(D.cells[c][4]-D.cells[c][2])))
oldphases={}
for r in json.load(open(P/'complete.json'))['rows']:
 j=round((r['origin'][1]-ys)/sy)
 if j in oldphases:assert oldphases[j]==r['orient']
 oldphases[j]=r['orient']
failed=[]
for seq,cid in enumerate(selected):
 c=D.cells[cid];n=round((c[4]-c[2])/sx);oi=round((c[2]-xs)/sx);oj=round((c[3]-ys)/sy);oldori=oldphases[oj];lo,hi=bounds(cid);tx,ty=target[cid];found=None
 for rad in (2.16,8.64,34.56,138.24,648):
  xmin=max(core[0],(lo[0]+lo[1])/2,tx-rad);xmax=min(core[2],(hi[0]+hi[1])/2,tx+rad);ymin=max(core[1],(lo[0]-hi[1])/2,ty-rad);ymax=min(core[3],(hi[0]-lo[1])/2,ty+rad)
  i0=max(0,math.ceil((xmin-xs-n*sx/2)/sx-1e-6));i1=min(nx-n+1,math.floor((xmax-xs-n*sx/2)/sx+1e-6)+1);j0=max(0,math.ceil((ymin-ys-sy/2)/sy-1e-6));j1=min(ny,math.floor((ymax-ys-sy/2)/sy+1e-6)+1)
  if i1<=i0 or j1<=j0:continue
  candidates=[]
  for j in range(j0,j1):
   yy=ys+j*sy+sy/2;low=max(i0,math.ceil((lo[0]-yy-xs-n*sx/2)/sx-1e-6),math.ceil((lo[1]+yy-xs-n*sx/2)/sx-1e-6));high=min(i1,math.floor((hi[0]-yy-xs-n*sx/2)/sx+1e-6)+1,math.floor((hi[1]+yy-xs-n*sx/2)/sx+1e-6)+1)
   if high<=low:continue
   f=free[j,low:high+n-1];cs=np.r_[0,np.cumsum(f,dtype=np.int32)];good=np.where(cs[n:]-cs[:-n]==n)[0]+low
   if not len(good):continue
   ii=int(good[np.argmin(abs(xs+good*sx+n*sx/2-tx))]);xx=xs+ii*sx+n*sx/2;candidates.append((abs(xx-tx)+abs(yy-ty),j,ii))
  for _,j,i in sorted(candidates):
   row=[r for r in rr[j]if r[0]<=i and i+n<=r[1]and r[3]==oldori]
   if len(row)==1:found=(j,i,row[0]);break
  if found:break
 if found is None:failed.append(dict(cid=cid,name=c[6],uv_lo=list(lo),uv_hi=list(hi)));continue
 j,i,row=found;free[j,i:i+n]=False;x=round(xs+i*sx,6);y=round(ys+j*sy,6);positions[cid]=np.array([x+n*sx/2,y+sy/2]);anchor[cid]=dict(cid=cid,name=c[6],origin_um=[x,y],size_um=[round(n*sx,6),sy],row=row[2],orient=row[3],preserve_original=False)
 if seq%1000==0:print('allocated',seq,'of',len(selected),'failed',len(failed),flush=True)
# Full exact endpoint census uses baseline positions for any failure, so no hidden optimistic targets.
for cid in target:
 if cid not in anchor:positions[cid]=np.array(G.ctr(D.cells[cid]))
ffbad=[];macbad=[];maxff=0;maxmac=0
for cid in target:
 xy=positions[cid]
 for n in adj[cid][0]:
  dd=float(np.sum(abs(xy-positions[n])));maxff=max(maxff,dd)
  if dd>405+1e-6 and cid<n:ffbad.append([cid,n,dd])
 for mk in adj[cid][1]:
  for x,y,label in ports[mk]:
   dd=abs(xy[0]-x)+abs(xy[1]-y);maxmac=max(maxmac,dd)
   if dd>405+1e-6:macbad.append([cid,label,float(dd)])
summary=dict(scope='DISABLED REPACK B allFF legal-model candidate; old rows/taps conservative, future actual regeneration required',allFF=len(target),anchors=len(anchor),selected=len(selected),failed=len(failed),max_ff_um=maxff,ff_gt405=len(ffbad),max_macro_um=float(maxmac),macro_gt405=len(macbad))
(P/'legal_joint_B_centre_actualFP.json').write_text(json.dumps(dict(summary=summary,anchors=list(anchor.values()),failed=failed,ff_bad=ffbad,macro_bad=macbad),indent=1));print(json.dumps(summary,indent=2))
