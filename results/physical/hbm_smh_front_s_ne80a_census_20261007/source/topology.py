import odb,json,pathlib
base=next(pathlib.Path('/work/results/asap7').glob('*/base'));db=odb.dbDatabase.create();odb.read_db(db,str(base/'6_final.odb'));rows=[]
for bt in db.getChip().getBlock().getBTerms():
 if bt.getIoType()!='OUTPUT':continue
 net=bt.getNet();drivers=[];sinks=[]
 for it in net.getITerms():
  inst=it.getInst();row={'instance':inst.getName(),'pin':it.getMTerm().getName(),'master':inst.getMaster().getName(),'location_dbu':list(inst.getLocation())}
  (drivers if it.getIoType()=='OUTPUT' else sinks).append(row)
 boxes=[]
 for pin in bt.getBPins():
  for box in pin.getBoxes():boxes.append({'layer':box.getTechLayer().getName(),'rect_dbu':[box.xMin(),box.yMin(),box.xMax(),box.yMax()]})
 rows.append({'port':bt.getName(),'net':net.getName(),'drivers':drivers,'iterm_sinks':sinks,'net_bterms':[b.getName() for b in net.getBTerms()],'terminal_boxes':boxes})
print('OUTPUT_TOPOLOGY_JSON '+json.dumps({'dbu_per_micron':db.getChip().getBlock().getDbUnitsPerMicron(),'outputs':rows}))
block=db.getChip().getBlock();pin=block.findBTerm('req_ready');net=pin.getNet();details=[]
for inst in [block.findInst('input1315')]:
 if inst is None:raise RuntimeError('Missing pinned input driver')
 for it in inst.getITerms():
  n=it.getNet();details.append({'pin':it.getMTerm().getName(),'net':n.getName(),'connections':[{'instance':t.getInst().getName(),'master':t.getInst().getMaster().getName(),'pin':t.getMTerm().getName(),'direction':t.getIoType(),'location_dbu':list(t.getInst().getLocation())} for t in n.getITerms()],'bterms':[b.getName() for b in n.getBTerms()]})
print('READY_TOPOLOGY_JSON '+json.dumps({'port':pin.getName(),'input_net':net.getName(),'buffer_connections':details}))
