"""Place the thin standard-cell band against exact immutable child contacts.
The resulting full graph must match the native floorplan before extraction.
"""
import odb,json,sys
from pathlib import Path
r=Path('/run');db=odb.dbDatabase.create();mode=sys.argv[-1]
odb.read_db(db,str(r/('floorplan.odb' if mode=='strip' else 'placed_cells.odb')));b=db.getChip().getBlock();u=b.getDbUnitsPerMicron()
if mode=='strip':
 records=[]
 for i in list(b.getInsts()):
  if not i.getMaster().isBlock():continue
  rec={'name':i.getName(),'master':i.getMaster().getName(),'orient':i.getOrient(),'xy':list(i.getLocation()),'pins':[]}
  for t in i.getITerms():
   if t.getNet() is None:continue
   ok,x,y=t.getAvgXY();assert ok
   n=t.getNet();name='__child_contact__'+i.getName()+'__'+t.getMTerm().getName()
   bt=odb.dbBTerm_create(n,name);bt.setIoType('OUTPUT' if t.getIoType()=='INPUT' else 'INPUT')
   bp=odb.dbBPin_create(bt);bp.setPlacementStatus('FIRM')
   odb.dbBox_create(bp,db.getTech().findLayer('M5'),x-12,y-42,x+12,y+42)
   rec['pins'].append({'pin':t.getMTerm().getName(),'net':n.getName(),'virtual_port':name,'xy_dbu':[x,y]})
  records.append(rec);odb.dbInst.destroy(i)
 (r/'child_contacts.json').write_text(json.dumps(records,indent=2));odb.write_db(db,str(r/'placement_input.odb'));print('fixed exact child contacts',sum(len(x['pins']) for x in records))
else:
 for rec in json.loads((r/'child_contacts.json').read_text()):
  i=odb.dbInst_create(b,db.findMaster(rec['master']),rec['name']);i.setOrient(rec['orient']);i.setLocation(*rec['xy']);i.setPlacementStatus('FIRM')
  for p in rec['pins']:
   i.findITerm(p['pin']).connect(b.findNet(p['net']));odb.dbBTerm.destroy(b.findBTerm(p['virtual_port']))
 odb.write_db(db,str(r/'placed.odb'));print('restored exact children')
