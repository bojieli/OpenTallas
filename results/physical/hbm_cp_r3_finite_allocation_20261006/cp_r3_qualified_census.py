import odb,json,hashlib
from pathlib import Path
D=odb.dbDatabase.create();odb.read_db(D,'/qualified/reallocated_context.odb');b=D.getChip().getBlock();u=b.getDbUnitsPerMicron()
B=odb.dbDatabase.create();odb.read_db(B,'/checkpoint/3_4_place_resized.odb');base={i.getName() for i in B.getChip().getBlock().getInsts()}
groups={};classes={};outside=[];ungrouped=[];fixed=0;total=0
for i in b.getInsts():
 z=i.getBBox();area=(z.xMax()-z.xMin())*(z.yMax()-z.yMin())/u**2;total+=area
 if i.isFixed():fixed+=area
 g=i.getGroup();gn=g.getName() if g else 'None'
 x=groups.setdefault(gn,dict(count=0,area_um2=0,movable_area_um2=0,fixed_area_um2=0));x['count']+=1;x['area_um2']+=area;x['fixed_area_um2' if i.isFixed() else 'movable_area_um2']+=area
 clock=any(t.getNet() and t.getNet().getSigType()=='CLOCK' for t in i.getITerms())
 cat='preCTS_existing' if i.getName() in base else ('inserted_clock_or_dummy' if clock or 'clkload' in i.getName() else 'inserted_data_repair')
 x=classes.setdefault(cat,dict(count=0,area_um2=0));x['count']+=1;x['area_um2']+=area
 if not i.isFixed() and g:
  boxes=list(g.getRegion().getBoundaries())
  if not any(q.xMin()<=z.xMin() and q.yMin()<=z.yMin() and q.xMax()>=z.xMax() and q.yMax()>=z.yMax() for q in boxes):outside.append(dict(name=i.getName(),group=gn,bbox=[z.xMin(),z.yMin(),z.xMax(),z.yMax()]))
 if not i.isFixed() and not g and any(t.getMTerm().getIoType()=='OUTPUT' for t in i.getITerms()):ungrouped.append(i.getName())
regions={g.getName():[[q.xMin(),q.yMin(),q.xMax(),q.yMax()] for q in g.getRegion().getBoundaries()] for g in b.getGroups() if g.getRegion()}
r=dict(ODB_sha256=hashlib.sha256(Path('/qualified/reallocated_context.odb').read_bytes()).hexdigest(),baseline_sha256=hashlib.sha256(Path('/checkpoint/3_4_place_resized.odb').read_bytes()).hexdigest(),DBU=u,group_stats=groups,area_classes=classes,total_cell_area_um2=total,fixed_cell_area_um2=fixed,original_region_boxes_DBU=regions,containment_violations=outside,ungrouped_movable_signal=ungrouped)
Path('/output/actual_census.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
assert not outside and not ungrouped
