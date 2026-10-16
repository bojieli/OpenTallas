import odb,glob,json
p=glob.glob('/audit/results/asap7/*/base/5_1_grt.odb')[0]
db=odb.dbDatabase.create();odb.read_db(db,p);b=db.getChip().getBlock();u=b.getDbUnitsPerMicron()
def r(bb):return [round(v/u,5) for v in [bb.xMin(),bb.yMin(),bb.xMax(),bb.yMax()]]
def near(bb,x0=182,y0=0,x1=189,y1=8):return bb.xMax()/u>=x0 and bb.xMin()/u<=x1 and bb.yMax()/u>=y0 and bb.yMin()/u<=y1
out={'dbu':u,'net':{},'near_insts':[],'obstructions':[],'supply':[],'near_pins':[]}
n=b.findNet('tag_payload[55]')
if n:
 for t in n.getITerms():
  i=t.getInst();out['net'].setdefault('iterms',[]).append({'inst':i.getName(),'master':i.getMaster().getName(),'pin':t.getMTerm().getName(),'box':r(i.getBBox()),'orient':str(i.getOrient()),'status':str(i.getPlacementStatus())})
 for t in n.getBTerms():
  for bp in t.getBPins():
   for bx in bp.getBoxes():out['net'].setdefault('bterms',[]).append({'name':t.getName(),'layer':bx.getTechLayer().getName(),'box':r(bx)})
for i in b.getInsts():
 if near(i.getBBox()):out['near_insts'].append({'inst':i.getName(),'master':i.getMaster().getName(),'box':r(i.getBBox()),'orient':str(i.getOrient()),'status':str(i.getPlacementStatus())})
for o in b.getObstructions():
 bb=o.getBBox()
 if near(bb):out['obstructions'].append({'layer':bb.getTechLayer().getName(),'box':r(bb)})
for n in b.getNets():
 if n.getSigType() in ['POWER','GROUND']:
  for sw in n.getSWires():
   for bb in sw.getWires():
    if near(bb):out['supply'].append({'net':n.getName(),'layer':bb.getTechLayer().getName() if bb.getTechLayer() else 'VIA','box':r(bb)})
for t in b.getBTerms():
 for bp in t.getBPins():
  for bb in bp.getBoxes():
   if near(bb):out['near_pins'].append({'name':t.getName(),'layer':bb.getTechLayer().getName(),'box':r(bb)})
print(json.dumps(out,indent=2))
