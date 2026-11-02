"""Apply disabled all-FF model to a FRESH normal floorplan. No CAD dispatch here.
Usage: openroad -python apply_allff_before_gpl.py FRESH_FP.odb targets.json OUTPUT.odb
Fails closed on changed FF identities, masters, regenerated rows/TAPs/halos or driver-bay conflicts.
"""
import sys,os,json,bisect
from pathlib import Path
import odb
source,targets_path,output=(Path(os.environ[k])for k in("ODB","TARGETS","OUT"));cfg=json.load(open(targets_path));assert cfg['enabled']is False
db=odb.dbDatabase.create();odb.read_db(db,str(source));block=db.getChip().getBlock();u=block.getDbUnitsPerMicron();assert u==1000
norm=lambda n:n.replace('\\','')
targets={p['name']:p for p in cfg['targets']};assert len(targets)==31847
inst={}
for i in block.getInsts():
 n=norm(i.getName())
 if n in targets:
  assert n not in inst,('duplicate',n);inst[n]=i
assert set(inst)==set(targets),('missing FF identities',list(set(targets)-set(inst))[:10])
actualFF=[i for i in block.getInsts()if i.getMaster().getName().startswith(('DFFHQN','DFFASRHQN'))]
assert len(actualFF)==31847,('changed FF cohort',len(actualFF))
rows={}
for r in block.getRows():
 b=r.getBBox();rows.setdefault(b.yMin(),[]).append((b.xMin(),b.xMax(),str(r.getOrient()),r.getSite().getWidth()))
occupied={y:[]for y in rows}
# Capture the actual new constraint inventory before any target failure or mutation.
def rect(b):return[b.xMin(),b.yMin(),b.xMax(),b.yMax()]
constraints=dict(dbu_per_um=u,rows=[dict(name=r.getName(),bbox_dbu=rect(r.getBBox()),origin=list(r.getOrigin()),orient=str(r.getOrient()),site_width=r.getSite().getWidth(),site_count=r.getSiteCount())for r in block.getRows()],fixed=[],macros=[],controls=[],PG_rects=[])
for q in block.getInsts():
 m=q.getMaster();st=str(q.getPlacementStatus())
 if norm(q.getName())not in targets and(st in('FIRM','LOCKED','COVER')or m.isBlock()):constraints['fixed'].append(dict(name=q.getName(),master=m.getName(),bbox_dbu=rect(q.getBBox()),orient=str(q.getOrient()),status=st))
 if m.isBlock():constraints['macros'].append(dict(name=q.getName(),master=m.getName(),bbox_dbu=rect(q.getBBox()),orient=str(q.getOrient()),PG=[dict(pin=t.getMTerm().getName(),net=t.getNet().getName()if t.getNet()else None)for t in q.getITerms()if str(t.getMTerm().getSigType())in('POWER','GROUND')]))
for bt in block.getBTerms():
 if bt.getName()in('ck','rst'):
  constraints['controls'].append(dict(name=bt.getName(),boxes=[dict(layer=b.getTechLayer().getName(),bbox_dbu=rect(b))for bp in bt.getBPins()for b in bp.getBoxes()if b.getTechLayer()]))
for n in block.getNets():
 if str(n.getSigType())not in('POWER','GROUND'):continue
 for wire in n.getSWires():
  for b in wire.getWires():
   if not b.isVia()and b.getTechLayer()and b.getTechLayer().getName()in('M5','M6'):constraints['PG_rects'].append(dict(net=n.getName(),layer=b.getTechLayer().getName(),bbox_dbu=rect(b)))
Path(str(output)+'.pre_constraints.json').write_text(json.dumps(constraints))
def reserve(box):
 x0,y0,x1,y1=box
 for y in occupied:
  if y<y1 and y+270>y0:occupied[y].append((x0,x1))
# Fixed objects except the FFs being assigned. New TAPs and fixed macros are native current FP objects.
for i in block.getInsts():
 if norm(i.getName())in targets:continue
 m=i.getMaster();status=str(i.getPlacementStatus())
 if status not in('FIRM','LOCKED','COVER')and not m.isBlock():continue
 b=i.getBBox();h=4320 if m.isBlock()else 0
 reserve((b.xMin()-h,b.yMin()-h,b.xMax()+h,b.yMax()+h))
bay=(321840,328320,326160,332640);reserve(bay)
# Inspect every footprint before mutating any instance.
planned=[];restored=[]
for name,p in sorted(targets.items(),key=lambda q:not q[1]['fixed_face']):
 i=inst[name];x,y=[round(z*u)for z in p['origin_um']];w,h=[round(z*u)for z in p['size_um']];candidate=[r for r in rows.get(y,[])if r[0]<=x and x+w<=r[1]and(x-r[0])%r[3]==0 and r[2]==p['row_orient']]
 assert len(candidate)==1,('new row/site/orientation conflict',name,x,y)
 assert not any(x<a1 and x+w>a0 for a0,a1 in occupied[y]),('new fixed/TAP/FF/halo/bay overlap',name)
 occupied[y].append((x,x+w))
 master=i.getMaster();expected=db.findMaster(p['master']);assert expected,('missing baseline master',p['master'])
 assert expected.getWidth()==w and expected.getHeight()==h,('master footprint',name,p['master'])
 if master.getName()!=p['master']:
  assert master.getName()=='DFFHQNx1_ASAP7_75t_R'and p['master']in('DFFHQNx2_ASAP7_75t_R','DFFHQNx3_ASAP7_75t_R'),('unexpected master change',name,master.getName(),p['master'])
  assert sorted(t.getName()for t in master.getMTerms())==sorted(t.getName()for t in expected.getMTerms()),('master port ABI',name)
  restored.append(dict(name=name,old=master.getName(),new=p['master']))
 planned.append((i,expected,x,y,p['row_orient']))
assert len(restored)==383,('expected exact baseline drive-class restores',len(restored))
for i,m,x,y,orient in planned:
 if i.getMaster().getName()!=m.getName():assert i.swapMaster(m),('swap failed',i.getName())
 i.setOrient(orient);i.setLocation(x,y);i.setPlacementStatus('FIRM');i.setDoNotTouch(True)
Path(str(output)+'.post_coords.json').write_text(json.dumps([dict(name=i.getName(),master=i.getMaster().getName(),bbox_dbu=rect(i.getBBox()),orient=str(i.getOrient()),status=str(i.getPlacementStatus()),dont_touch=i.isDoNotTouch())for i,_,_,_,_ in planned]))
companion=Path('/work/export_native_geom.py')
if companion.is_file():exec(compile(companion.read_text(),str(companion),'exec'))
odb.write_db(db,str(output))
Path(str(output)+'.anchors.json').write_text(json.dumps(dict(status='FF_MODEL_APPLIED_TO_FRESH_FP',FF_FIRM=31847,restored_baseline_drive_classes=restored,clock_driver_bay_um=[z/u for z in bay],new_rows_TAP_obstacles_checked=True,no_route_or_clock_or_EQ_claim=True),indent=2)+'\n')
print('ALLFF FIRM31847, baseline master restores383, regenerated row/TAP/halo/bay legality PASS; no physical timing or EQ claim')
