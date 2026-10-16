import odb,glob,json
p=glob.glob('/audit/results/asap7/*/base/4_cts.odb')[0];db=odb.dbDatabase.create();odb.read_db(db,p);b=db.getChip().getBlock();u=b.getDbUnitsPerMicron()
def r(bb):return [v/u for v in [bb.xMin(),bb.yMin(),bb.xMax(),bb.yMax()]]
n=b.findNet('_04208_');out={'odb':p,'dbu':u,'net_name':'_04208_','iterms':[],'blocks':[]}
if n:
 for t in n.getITerms():
  i=t.getInst();out['iterms'].append({'inst':i.getName(),'master':i.getMaster().getName(),'pin':t.getMTerm().getName(),'box':r(i.getBBox()),'orient':str(i.getOrient()),'status':str(i.getPlacementStatus())})
 for t in n.getBTerms():out.setdefault('bterms',[]).append(t.getName())
for i in b.getInsts():
 if i.getMaster().isBlock():out['blocks'].append({'inst':i.getName(),'box':r(i.getBBox())})
for it in out['iterms']:
 box=it['box'];near=lambda q: q[2]>box[0]-1 and q[0]<box[2]+1 and q[3]>box[1]-1 and q[1]<box[3]+1
 it['nearby_insts']=[{'name':i.getName(),'master':i.getMaster().getName(),'box':r(i.getBBox()),'status':str(i.getPlacementStatus())} for i in b.getInsts() if near(r(i.getBBox()))]
 it['nearby_obstructions']=[{'layer':o.getBBox().getTechLayer().getName(),'box':r(o.getBBox())} for o in b.getObstructions() if near(r(o.getBBox()))]
 it['placement_blockages']=[{'box':r(o.getBBox())} for o in b.getBlockages() if near(r(o.getBBox()))]
print(json.dumps(out,indent=2))
