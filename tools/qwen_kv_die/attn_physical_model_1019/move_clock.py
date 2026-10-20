import odb,pathlib
r=pathlib.Path('/work');db=odb.dbDatabase.create();odb.read_db(db,str(r/'3_placed.odb'));b=db.getChip().getBlock();u=b.getDbUnitsPerMicron();t=b.findBTerm('ck')
for p in list(t.getBPins()):odb.dbBPin.destroy(p)
p=odb.dbBPin.create(t);odb.dbBox.create(p,db.getTech().findLayer('M5'),round(215.916*u),round(107.988*u),round(216*u),round(108.012*u));p.setPlacementStatus('FIRM');odb.write_db(db,str(r/'3_placed_clock_center.odb'))
print('proposed only physical ck pin at east band center; no cell/net/edge change')
