import odb,json
D=odb.dbDatabase.create();odb.read_db(D,'/input/run/results/asap7/kq_qfd_qc_su_lane_w_l1_w0e61bf/base/5_2_route.odb');b=D.getChip().getBlock();u=b.getDbUnitsPerMicron()
def box(x):return [x.xMin()/u,x.yMin()/u,x.xMax()/u,x.yMax()/u]
def near(r):return r[0]<225 and r[2]>220 and r[1]<164 and r[3]>160
out={'dbu':u,'data_shapes':[],'power_shapes':[],'macro':{}}
n=next(x for x in b.getNets() if x.getName().replace(chr(92),'')=='u_u_rsq1.u_rsq.g_nr[0].g_h.d_h.genblk1.g_line.line[238]')
out['terminals']=[{'inst':t.getInst().getName(),'pin':t.getMTerm().getName(),'bbox':box(t.getInst().getBBox())} for t in n.getITerms()]
w=n.getWire();it=odb.dbWirePathItr();it.begin(w);p=odb.dbWirePath();s=odb.dbWirePathShape()
while it.getNextPath(p):
 while it.getNextShape(s):
  q=s.shape;r=box(q)
  if near(r):out['data_shapes'].append({'bbox':r,'via':q.isVia(),'layer':None if q.isVia() else q.getTechLayer().getName()})
for name in ['VDD','VSS']:
 net=b.findNet(name)
 for sw in net.getSWires():
  for q in sw.getWires():
   r=box(q)
   if near(r):out['power_shapes'].append({'net':name,'bbox':r,'via':q.isVia(),'layer':q.getTechLayer().getName() if q.getTechLayer() else None,'type':str(sw.getWireType())})
i=next(x for x in b.getInsts() if x.getName().replace(chr(92),'')=='u_u_head1.u_h.u_lane.g_native_bank[1].u_tlm')
assert str(i.getOrient())=='R0';origin=i.getLocation()
def transform(q):return [(q.xMin()+origin[0])/u,(q.yMin()+origin[1])/u,(q.xMax()+origin[0])/u,(q.yMax()+origin[1])/u]
out['macro']={'name':i.getName(),'master':i.getMaster().getName(),'bbox':box(i.getBBox()),'orient':str(i.getOrient()),'pins':[],'obstructions':[]}
for t in i.getITerms():
 for pin in t.getMTerm().getMPins():
  for q in pin.getGeometry():
   bb=transform(q)
   if near(bb):out['macro']['pins'].append({'pin':t.getMTerm().getName(),'net':t.getNet().getName() if t.getNet() else None,'layer':q.getTechLayer().getName(),'bbox':bb})
for q in i.getMaster().getObstructions():
 bb=transform(q)
 if near(bb):out['macro']['obstructions'].append({'layer':q.getTechLayer().getName(),'bbox':bb})
json.dump(out,open('/work/audit.json','w'),indent=2);print('L1_DRC_READ_ONLY_AUDIT_COMPLETE')
