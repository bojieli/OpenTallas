import odb,json,re,os
from pathlib import Path
D=odb.dbDatabase.create();odb.read_db(D,os.environ['CUT_ODB']);b=D.getChip().getBlock();dbu=D.getTech().getDbUnitsPerMicron()
def rect(z):return(z.xMin(),z.yMin(),z.xMax(),z.yMax())
def overlap(a,c):return max(0,min(a[2],c[2])-max(a[0],c[0]))*max(0,min(a[3],c[3])-max(a[1],c[1]))/dbu**2
rows=[rect(r.getBBox()) for r in b.getRows()];taps=[rect(i.getBBox()) for i in b.getInsts() if i.getMaster().getName().startswith('TAPCELL')];macros=[i for i in b.getInsts() if i.getMaster().isBlock()];assert len(macros)==64
sx=list(b.getRows())[0].getSite().getWidth();matrix=[]
for g in b.getGroups():
 boxes=[rect(x) for x in g.getRegion().getBoundaries()];assert len(boxes)==1
 cells=list(g.getInsts());assert cells and all(not i.getMaster().isBlock() for i in cells)
 box=boxes[0];usable=sum(overlap(x,box) for x in rows)-sum(overlap(x,box) for x in taps)
 area=sum(i.getMaster().getWidth()*i.getMaster().getHeight() for i in cells)/dbu**2
 padded=sum((i.getMaster().getWidth()+4*sx)*i.getMaster().getHeight() for i in cells)/dbu**2
 assert padded<usable*.95*.60,(g.getName(),padded,usable)
 matrix.append(dict(region=g.getName(),members=len(cells),area_um2=area,padded_area_um2=padded,usable_nonmacro_rows_after_taps_um2=usable,guard5_capacity_um2=usable*.95,occupancy_after_guard5=padded/(usable*.95),rectangle_dbu=box))
assert len(matrix)==64
std=[i for i in b.getInsts() if not i.getMaster().isBlock() and not i.getMaster().getName().startswith('TAPCELL')]
record=dict(source='d0488d023 C22 actual receiver-retained PDN',macro_count=64,macro_locations=[dict(name=i.getName(),location=list(i.getLocation()),orientation=str(i.getOrient()),status=str(i.getPlacementStatus())) for i in macros],groups=matrix,all_movable_members=len(std),all_movable_area_um2=sum(i.getMaster().getWidth()*i.getMaster().getHeight() for i in std)/dbu**2,unconstrained_members=sum(i.getGroup() is None for i in std),target_density=.60,PG_specialshape_counts={n.getName():sum(1 for sw in n.getSWires() for z in sw.getWires()) for n in b.getNets() if n.getName() in ('VDD','VSS')},note='Native row/macro/tap/padding/guard5 inventory; PG retains routing budget, not duplicate row subtraction. No ODB/group/pin/clock modification.' )
Path(os.environ['CUT_CAPACITY']).write_text(json.dumps(record,indent=2)+'\n');print('C22_CURRENT_CAPACITY_PASS groups64 macros64 worst',max(x['occupancy_after_guard5'] for x in matrix),flush=True)
