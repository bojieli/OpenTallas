import resource,json,time
resource.setrlimit(resource.RLIMIT_AS,(12*1024**3,12*1024**3))
resource.setrlimit(resource.RLIMIT_CPU,(30,30))
import odb
t=time.time()
db=odb.dbDatabase.create()
odb.read_db(db,'/work/results/asap7/opentallas_ot_v41_attn_eng_ctl_phys_asap7/base/4_1_cts.odb')
block=db.getChip().getBlock();scale=block.getDbUnitsPerMicron()
names=['_1780513_','_1701638_','_1028526_','_1077589_',
       'place348018','wire408299','place348017','place348016','place348015','place347952','place347951','place347944','place347941',
       'place306880','place306879','place306878','wire386705','place306877','place306876','place306875','wire381059','wire381058',
       '_1554657_','_1554721_']
result=[]
for name in names:
 inst=block.findInst(name)
 if inst is None: raise ValueError(name)
 box=inst.getBBox();loc=inst.getLocation();terms=[]
 for pin in inst.getITerms():
  net=pin.getNet()
  terms.append({'pin':pin.getMTerm().getName(),'direction':str(pin.getIoType()),'net':net.getName() if net else None,
    'connected_ITerms':len(net.getITerms()) if net else 0,
    'sinks':sum(str(p.getIoType())=='INPUT' for p in net.getITerms()) if net else 0,
    'BTerms':[p.getName() for p in net.getBTerms()] if net else []})
 result.append({'instance':name,'master':inst.getMaster().getName(),'x_um':loc[0]/scale,'y_um':loc[1]/scale,
  'bbox_um':[box.xMin()/scale,box.yMin()/scale,box.xMax()/scale,box.yMax()/scale],'terms':terms})
print('W11_QUERY_JSON='+json.dumps({'read_only':True,'elapsed_seconds':time.time()-t,'dbu_per_um':scale,'instances':result}))
