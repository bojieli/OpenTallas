import odb,json,gzip,math,os
from collections import Counter
D=odb.dbDatabase.create();odb.read_db(D,os.environ['ODB_INPUT']);b=D.getChip().getBlock();u=b.getDbUnitsPerMicron()
out={'scope':'IMMUTABLE PRE_CTS 3_place ODB ONLY; no final-route/native eligibility claim','band':[0,302.4,518.4,356.4],'std_cells':[],'macros':[],'pg':Counter(),'pg_unbound_examples':[]}
for i in b.getInsts():
 m=i.getMaster();q=i.getBBox();r=[v/u for v in [q.xMin(),q.yMin(),q.xMax(),q.yMax()]]
 if m.isBlock():
  rec={'name':i.getName(),'master':m.getName(),'box':r,'orient':str(i.getOrient()),'pins':[]}
  for it in i.getITerms():
   mt=it.getMTerm()
   if str(mt.getSigType()) in ['POWER','GROUND']:continue
   a=it.getAvgXY()
   if len(a)==3 and a[0]:
    x,y=a[1]/u,a[2]/u;ds=[abs(x-r[0]),abs(x-r[2]),abs(y-r[1]),abs(y-r[3])];face=['W','E','S','N'][min(range(4),key=lambda z:ds[z])]
    rec['pins'].append({'pin':mt.getName(),'io':str(mt.getIoType()),'x':x,'y':y,'nearest_face':face,'face_distance':min(ds),'net':it.getNet().getName() if it.getNet() else None})
  out['macros'].append(rec)
 else:
  area=(r[2]-r[0])*(r[3]-r[1]);inside=max(0,min(r[2],518.4)-max(r[0],0))*max(0,min(r[3],356.4)-max(r[1],302.4))
  out['std_cells'].append({'name':i.getName(),'master':m.getName(),'box':r,'area':area,'area_outside_band':max(0,area-inside),'status':str(i.getPlacementStatus())})
 for it in i.getITerms():
  role=str(it.getMTerm().getSigType())
  if role not in ['POWER','GROUND']:continue
  out['pg']['terms']+=1;n=it.getNet();ok=bool(n) and str(n.getSigType())==role
  out['pg']['bound' if ok else 'unbound']+=1
  if not ok and len(out['pg_unbound_examples'])<20:out['pg_unbound_examples'].append([i.getName(),it.getMTerm().getName(),role,n.getName() if n else None])
gaps=[]
for z,a in enumerate(out['macros']):
 for c in out['macros'][z+1:]:
  x,y=a['box'],c['box'];ox=min(x[2],y[2])-max(x[0],y[0]);oy=min(x[3],y[3])-max(x[1],y[1]);gap=None
  if ox>0 and (x[3]<=y[1] or y[3]<=x[1]):gap=max(y[1]-x[3],x[1]-y[3]);direction='vertical'
  if oy>0 and (x[2]<=y[0] or y[2]<=x[0]):gap=max(y[0]-x[2],x[0]-y[2]);direction='horizontal'
  if gap is not None and gap<20:gaps.append({'a':a['name'],'b':c['name'],'gap_um':gap,'direction':direction})
out['macro_gaps_under20']=gaps
bins=[[0.0]*12 for _ in range(15)]
for c in out['std_cells']:
 x0,y0,x1,y1=c['box']
 for iy in range(max(0,int(y0/43.2)),min(14,int(y1/43.2))+1):
  for ix in range(max(0,int(x0/43.2)),min(11,int(x1/43.2))+1):bins[iy][ix]+=max(0,min(x1,(ix+1)*43.2)-max(x0,ix*43.2))*max(0,min(y1,(iy+1)*43.2)-max(y0,iy*43.2))/(43.2**2)
out['bin_43p2_std_density']=bins
ss=out['std_cells'];out['summary']={'std_count':len(ss),'std_area':sum(c['area'] for c in ss),'std_bbox':[min(c['box'][0] for c in ss),min(c['box'][1] for c in ss),max(c['box'][2] for c in ss),max(c['box'][3] for c in ss)],'std_outside_band_area':sum(c['area_outside_band'] for c in ss),'std_outside_band_count':sum(c['area_outside_band']>1e-8 for c in ss),'std_max43p2_bin_density':max(max(row) for row in bins),'status':dict(Counter(c['status'] for c in ss)),'macro_count':len(out['macros']),'under20_gap_count':len(gaps),'pg':dict(out['pg'])}
with gzip.open(os.environ['OUT_JSON'],'wt') as f:json.dump(out,f)
print(json.dumps(out['summary']))
