import odb,re,json
D=odb.dbDatabase.create();odb.read_db(D,'/work/qroot_preCTS_check.odb');b=D.getChip().getBlock();u=b.getDbUnitsPerMicron()
r=next(r for r in b.getRegions() if r.getName()=='dvm_fill_restore_S');g=r.getGroups()[0]
for box in list(r.getBoundaries()):odb.dbBox_destroy(box)
box=[2.16,2.16,62.64,24.84];odb.dbBox_create(r,*[round(v*u) for v in box])
cap=[];resident=[]
for i in b.getInsts():
 n=i.getName().replace('\\','');seq=bool(re.search('DFF|SDFF',i.getMaster().getName()));q=i.getBBox()
 capture=seq and bool(re.search(r'^u_leaf\.(?:wv|cv|wep|cep|woff|wm|wd|wctl)(?:\[|\$)',n))
 if capture:cap.append(i)
 old=i.getGroup()
 south=(q.yMin()+q.yMax())/2<24.84*u
 if (capture or south) and (not old or old==g):resident.append(i)
 if capture and old and old!=g:raise RuntimeError('capture owned by bank')
if len(cap)!=1170:raise RuntimeError(f'capture_count={len(cap)}')
for i in resident:g.addInst(i)
a=sum(i.getMaster().getWidth()*i.getMaster().getHeight()/u**2 for i in g.getInsts());util=a/((box[2]-box[0])*(box[3]-box[1]))
print('FULL_S_PLACEMENT_MODEL',json.dumps(dict(capture_FF=len(cap),S_resident_cells=len(list(g.getInsts())),area_um2=a,region_um=box,util=util,added_FF=0,added_edges=0,fill_II=1,fill_bytes_per_cycle=128,source_logic_unchanged=True,route_qualified=False)))
if util>.65:raise RuntimeError('Reject before DPL: actual S util exceeds65%, grow/repartition')
row=b.getRows()[0];sw=row.getSite().getWidth();sh=row.getSite().getHeight()
for i in g.getInsts():
 q=i.getBBox();m=i.getMaster();x,y=q.xMin(),q.yMin();xx=max(round(box[0]*u),min(x,round(box[2]*u)-m.getWidth()));yy=max(round(box[1]*u),min(y,round(box[3]*u)-m.getHeight()));xx=round(xx/sw)*sw;yy=round(yy/sh)*sh
 if xx!=x or yy!=y:
  if i.getPlacementStatus() in ('FIRM','LOCKED','COVER'):raise RuntimeError('Cannot move fixed resident')
  i.setLocation(xx,yy);i.setPlacementStatus('PLACED')
odb.write_db(D,'/work/fullS_before_DPL.odb')
