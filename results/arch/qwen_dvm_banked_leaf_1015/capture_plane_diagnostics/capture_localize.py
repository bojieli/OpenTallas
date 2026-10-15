import odb,re,json
D=odb.dbDatabase.create();odb.read_db(D,'/work/qroot_preCTS_check.odb');b=D.getChip().getBlock();u=b.getDbUnitsPerMicron()
r=next(r for r in b.getRegions() if r.getName()=='dvm_fill_restore_S');g=r.getGroups()[0]
# Extend the actual restoration fence to include the physical capture plane.
for box in list(r.getBoundaries()):odb.dbBox_destroy(box)
odb.dbBox_create(r,int(2.16*u),int(5.4*u),int(58.32*u),int(24.84*u))
cap=[]
for i in b.getInsts():
 n=i.getName().replace('\\','')
 if re.search(r'(?:^|\.)wd\[\d+\]',n) and re.search('DFF|SDFF',i.getMaster().getName()):cap.append(i)
if len(cap)!=1024:raise RuntimeError(f'capture_count={len(cap)}')
for i in cap:
 old=i.getGroup()
 if old and old!=g:raise RuntimeError('capture belongs to other bank')
 g.addInst(i)
# Seed only out-of-region members; DPL still must prove full legality.
row=b.getRows()[0];sw=row.getSite().getWidth();sh=row.getSite().getHeight()
for i in g.getInsts():
 q=i.getBBox();m=i.getMaster();x,y=q.xMin(),q.yMin()
 xx=max(int(2.16*u),min(x,int(58.32*u)-m.getWidth()));yy=max(int(5.4*u),min(y,int(24.84*u)-m.getHeight()))
 xx=round(xx/sw)*sw;yy=round(yy/sh)*sh
 if xx!=x or yy!=y:i.setLocation(xx,yy);i.setPlacementStatus('PLACED')
a=sum(i.getMaster().getWidth()*i.getMaster().getHeight()/u**2 for i in g.getInsts())
print('CAPTURE_RESTORE_LOCAL_MODEL',json.dumps(dict(actual_capture_FF=1024,restore_cells=len(list(g.getInsts()))-1024,area_um2=a,region_um=[2.16,5.4,58.32,24.84],util=a/(56.16*19.44),added_FF=0,added_edges=0,II=1,payload_bytes_per_cycle=128,qualified=False)))
odb.write_db(D,'/work/capture_localize_before_DPL.odb')
