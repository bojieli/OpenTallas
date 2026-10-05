import odb,json,hashlib
from pathlib import Path
p=Path('/work/cts_failure.odb')
db=odb.dbDatabase.create();odb.read_db(db,str(p));block=db.getChip().getBlock();scale=block.getDbUnitsPerMicron()
def rect(box):return [getattr(box,f)()/scale for f in ('xMin','yMin','xMax','yMax')]
def group_info(i):
 g=i.getGroup()
 return None if g is None else g.getName()
def cell(i):
 master=i.getMaster();box=i.getBBox();terms=[]
 for t in i.getITerms():
  n=t.getNet();mt=t.getMTerm()
  terms.append(dict(pin=mt.getName(),io=str(mt.getIoType()),net=None if n is None else n.getName(),sig=None if n is None else str(n.getSigType())))
 return dict(name=i.getName(),master=master.getName(),bbox_um=rect(box),location_um=[v/scale for v in i.getLocation()],orientation=str(i.getOrient()),placement_status=str(i.getPlacementStatus()),fixed=i.isFixed(),group=group_info(i),area_um2=master.getWidth()*master.getHeight()/scale**2,terms=terms)
pairs=[('clkload0','clkbuf_2_2__f_clk'),('clkload16','clkbuf_leaf_20_clk'),('clkload17','clkbuf_leaf_21_clk'),('clkload18','clkbuf_leaf_22_clk'),('clkload19','clkbuf_leaf_23_clk'),('clkload4','clkbuf_leaf_26_clk'),('clkload5','clkbuf_leaf_27_clk'),('clkload6','clkbuf_leaf_28_clk'),('clkload7','clkbuf_leaf_29_clk')]
names={n for pair in pairs for n in pair}
actors={i.getName():cell(i) for i in block.getInsts() if i.getName() in names}
association_cells=[cell(i) for i in block.getInsts() if group_info(i)=='cp_association']
assert set(actors)==names
summary={};all_clock=[]
for i in block.getInsts():
 n=i.getName();kind='CTS_dummy' if n.startswith('clkload') else 'CTS_buffer' if n.startswith('clkbuf') else 'other'
 if kind!='other':all_clock.append(cell(i))
 g=group_info(i);status=str(i.getPlacementStatus());key=(kind,g,status)
 row=summary.setdefault(str(key),dict(kind=kind,group=g,status=status,count=0,area_um2=0))
 row['count']+=1;row['area_um2']+=i.getMaster().getWidth()*i.getMaster().getHeight()/scale**2
regions=[]
for r in block.getRegions():regions.append(dict(name=r.getName(),type=str(r.getRegionType()),boxes_um=[rect(b) for b in r.getBoundaries()],groups=[g.getName() for g in r.getGroups()]))
result=dict(scope='Actual retained post-CTS failure geometry; original nine R5 marker pairs',failure_odb_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),dbu_per_um=scale,pairs=[dict(load=actors[a],buffer=actors[b]) for a,b in pairs],regions=regions,association_cells=association_cells,cell_summary=list(summary.values()),CTS_cells=all_clock)
Path('/work/cts_failure_geometry.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(association_cells=association_cells,pairs=len(pairs),regions=regions,clock_summary=[v for v in summary.values() if v['kind']!='other']),indent=2))
