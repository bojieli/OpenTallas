from pathlib import Path
import odb,json,hashlib
from collections import Counter
r=Path('/work');f=r/'run/results/asap7/hc_ot_nhb_zh__151_2x151_2/base/2_floorplan.odb';db=odb.read_db(odb.dbDatabase.create(),str(f));b=db.getChip().getBlock();u=b.getDbUnitsPerMicron();bb=lambda q:[q.xMin()/u,q.yMin()/u,q.xMax()/u,q.yMax()/u]
d={'status':'NATIVE_FP_READ_ONLY','ODB':str(f),'outline':bb(b.getDieArea()),'rows':[{'name':row.getName(),'box':bb(row.getBBox()),'orient':str(row.getOrient()),'site':row.getSite().getName()} for row in b.getRows()],'pins':[],'PG':{},'masters':dict(Counter(i.getMaster().getName() for i in b.getInsts())),'placed_status':dict(Counter(str(i.getPlacementStatus()) for i in b.getInsts())),'macros':[{'name':i.getName(),'master':i.getMaster().getName(),'box':bb(i.getBBox())} for i in b.getInsts() if i.getMaster().isBlock()]}
for p in b.getBTerms():
 for q in p.getBPins():
  for box in q.getBoxes():d['pins'].append({'name':p.getName(),'dir':str(p.getIoType()),'signal_type':str(p.getSigType()),'layer':box.getTechLayer().getName(),'box':bb(box)})
for name in ['VDD','VSS']:
 n=b.findNet(name);boxes=[]
 if n:
  for sw in n.getSWires():
   for s in sw.getWires():
    if s.isVia():continue
    boxes.append({'layer':s.getTechLayer().getName(),'box':bb(s)})
 d['PG'][name]={'net_exists':bool(n),'metal_rects':boxes,'iterm_count':len(n.getITerms()) if n else 0}
signal=[p for p in d['pins'] if p['signal_type'] not in ('POWER','GROUND')]
assert len({p['name'] for p in signal})==338 and len(signal)==338
W,H=d['outline'][2:];assert abs(W-151.2)<1e-6 and abs(H-151.2)<1e-6
assert all(0<=p['box'][0]<p['box'][2]<=W and 0<=p['box'][1]<p['box'][3]<=H for p in signal)
south=[p for p in signal if p['box'][1]==0]
assert len(south)==268
xs=[(p['box'][0]+p['box'][2])/2 for p in south];assert min(xs)<3 and max(xs)>148
assert d['rows'] and all(v['net_exists'] and v['metal_rects'] for v in d['PG'].values())
d['checks']={'signal_bits':338,'signal_rects':338,'all_signal_shapes_contained':True,'south_pin_count':len(south),'south_center_span':[min(xs),max(xs)],'rows':len(d['rows']),'PG_both_nets_metal_present':True,'PG_connectivity_final_signoff':'NOT_ASSERTED','PLACEMENT':'NOT_RUN','STA':'NOT_RUN'}
Path('/case/FP_NATIVE_GEOMETRY.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d['checks']))
