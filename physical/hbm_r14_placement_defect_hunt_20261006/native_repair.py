"""Align actual leaf pin centres to the retained native grid on a copy."""
import hashlib,json,collections
from pathlib import Path
import odb
D=odb.dbDatabase.create();odb.read_db(D,'/work/real_leaf_overlay.odb');b=D.getChip().getBlock()
g={}
for name,axis in [('M4','Y'),('M5','X')]:
 layer=D.getTech().findLayer(name);grid=b.findTrackGrid(layer)
 q=list(grid.getGridY() if axis=='Y' else grid.getGridX())
 assert q[1]-q[0]==48,(name,q[:4])
 g[name]=(q[0]%48,48)
changes=[]
for i in b.getInsts():
 m=i.getMaster()
 if m.getName() not in ('ot_hbm_accel_bd_col','ot_hbm_accel_tc16'):continue
 ori=str(i.getOrient());bb=i.getBBox();x,y=bb.xMin(),bb.yMin();w,h=m.getWidth(),m.getHeight();deltas=collections.defaultdict(set)
 for mt in m.getMTerms():
  if mt.getSigType() in ('POWER','GROUND'):continue
  for mp in mt.getMPins():
   for r in mp.getGeometry():
    ly=r.getTechLayer()
    if not ly or ly.getName() not in g:continue
    name=ly.getName();start,pitch=g[name]
    if name=='M4':
     c=(r.yMin()+r.yMax())//2;c=h-c if ori in ('MX','R180') else c;now=y+c;axis='Y'
    else:
     c=(r.xMin()+r.xMax())//2;c=w-c if ori in ('MY','R180') else c;now=x+c;axis='X'
    delta=(start-now)%pitch
    if delta>pitch//2:delta-=pitch
    deltas[axis].add(delta)
 assert all(len(s)==1 for s in deltas.values()),(m.getName(),ori,dict(deltas))
 dx=next(iter(deltas['X']));dy=next(iter(deltas['Y']))
 old_status=i.getPlacementStatus();i.setPlacementStatus('PLACED');i.setLocation(x+dx,y+dy);i.setPlacementStatus(old_status)
 changes.append(dict(instance=i.getName(),orientation=ori,original_LL_DBU=[x,y],shift_DBU=[dx,dy],new_LL_DBU=[x+dx,y+dy]))
odb.write_db(D,'/work/real_leaf_grid_aligned.odb')
Path('/work/repair_shifts.json').write_text(json.dumps(dict(scope='PLACEMENT_GRID_REPAIR_COPY_ONLY',original_odb_sha256=hashlib.sha256(Path('/work/real_leaf_overlay.odb').read_bytes()).hexdigest(),shifts=changes,max_abs_shift_DBU=max(abs(v) for r in changes for v in r['shift_DBU']),pin_semantics_changed=False,clock_changed=False,leaf_connectivity_claim=False),indent=1)+'\n')
print('OT_REAL_LEAF_GRID_ALIGNED',len(changes))
