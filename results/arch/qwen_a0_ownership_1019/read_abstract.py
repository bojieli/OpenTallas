import odb,json,hashlib
p='/srv/opentallas-scratch/claude/qwen-a0-reset-r3-1019/native/candidate.odb';db=odb.dbDatabase.create();odb.read_db(db,p);b=db.getChip().getBlock();u=b.getDbUnitsPerMicron();out={}
def box(x):return {'layer':x.getTechLayer().getName(),'rect_um':[x.xMin()/u,x.yMin()/u,x.xMax()/u,x.yMax()/u]}
for i in b.getInsts():
 m=i.getMaster()
 if str(m.getType())!='BLOCK' or m.getName() in out:continue
 pins={}
 for t in m.getMTerms():
  shapes=[box(x) for pin in t.getMPins() for x in pin.getGeometry()]
  pins[t.getName()]={'direction':str(t.getIoType()),'signal_type':str(t.getSigType()),'shapes':shapes}
 out[m.getName()]={'size_um':[m.getWidth()/u,m.getHeight()/u],'pins':pins,'obs':[box(x) for x in m.getObstructions()],'inherited_instance_orientation':str(i.getOrient())}
json.dump({'odb_sha256':hashlib.sha256(open(p,'rb').read()).hexdigest(),'masters':out,'PG_via_access_qualified':False},open('/work/native_abstracts.json','w'),indent=2)
print('A0_ABSTRACT_READ_PASS',len(out),'masters')
