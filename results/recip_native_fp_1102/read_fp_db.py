from pathlib import Path
import odb,json,hashlib
from collections import Counter
r=Path('/work');f=r/'run/results/asap7/hc_ot_qkh_recip_leaf__216x216/base/2_floorplan.odb';db=odb.read_db(odb.dbDatabase.create(),str(f));b=db.getChip().getBlock();u=b.getDbUnitsPerMicron();bb=lambda q:[q.xMin()/u,q.yMin()/u,q.xMax()/u,q.yMax()/u]
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
signal=[p for p in d['pins'] if p['signal_type'] not in ('POWER','GROUND')];assert len({p['name'] for p in signal})==69;assert len(signal)==70;W,H=d['outline'][2:];bad=[p for p in signal if not(0<=p['box'][0]<p['box'][2]<=W and 0<=p['box'][1]<p['box'][3]<=H)];assert not bad,bad
x=[p for p in signal if p['name']=='x[31]'];assert len(x)==2 and all(p['layer']=='M5' for p in x);assert max(p['box'][3] for p in x)<=138.24
assert d['rows'] and all(v['net_exists'] and v['metal_rects'] for v in d['PG'].values())
d['checks']={'signal_bits':69,'signal_rects':70,'all_signal_shapes_contained':True,'x31_two_shapes_retained':True,'rows':len(d['rows']),'PG_both_nets_metal_present':True,'PG_connectivity_final_signoff':'NOT_ASSERTED','PLACEMENT':'NOT_RUN','STA':'NOT_RUN'}
Path('/case/FP_NATIVE_GEOMETRY.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d['checks']))
