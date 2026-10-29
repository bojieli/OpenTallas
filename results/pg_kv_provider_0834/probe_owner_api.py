import odb,json
for name in ('dbBox','dbMaster','dbMPin','dbMTerm','dbInst','dbLib'):
 cls=getattr(odb,name)
 print('API',name,[x for x in dir(cls) if any(k in x.lower() for k in ('destroy','remove','name','copy','swap','create','freeze'))],flush=True)
 print('DOC',name,{k:str(getattr(cls,k).__doc__) for k in ('create','destroy','copy','swapMaster','rename','setName') if hasattr(cls,k)},flush=True)
D=odb.dbDatabase.create();odb.read_lef(D,'/OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef');odb.read_lef(D,'/kv/full_abstracts/kv3_hg_part.lef');m=D.findMaster('kv3_hg_part');mt=m.findMTerm('VDD')
q=[x for x in m.getObstructions()][0]
print('BEFORE_CLASS_DESTROY',sum(1 for x in m.getObstructions()),flush=True)
odb.dbBox.destroy(q)
print('AFTER_CLASS_DESTROY',sum(1 for x in m.getObstructions()),flush=True)
mp=[x for x in mt.getMPins()][0]
print('BEFORE_MPIN_DESTROY',sum(1 for p in mt.getMPins() for x in p.getGeometry()),flush=True)
odb.dbMPin.destroy(mp)
print('AFTER_MPIN_DESTROY',sum(1 for p in mt.getMPins() for x in p.getGeometry()),flush=True)
