import odb,json,collections,hashlib
p='/srv/opentallas-scratch/claude/qwen-a0-reset-r3-1019/native/candidate.odb'
db=odb.dbDatabase.create();odb.read_db(db,p);b=db.getChip().getBlock();u=b.getDbUnitsPerMicron();a={}; groups=collections.defaultdict(lambda:{'cells':0,'area_um2':0.0})
for i in b.getInsts():
 m=i.getMaster();a[m.getName()]=m.getWidth()*m.getHeight()/u**2
 n=i.getName();g='hard' if str(m.getType())=='BLOCK' else ('named_me' if '.u_me.' in n else ('named_other' if 'u_g.' in n else 'anonymous_mapped'))
 groups[g]['cells']+=1;groups[g]['area_um2']+=a[m.getName()]
json.dump({'source_odb_sha256':hashlib.sha256(open(p,'rb').read()).hexdigest(),'master_area_um2':a,'hierarchy_groups':groups,'placement_status':'synthesis only; anonymous mapped cells need source-cone ownership'},open('/work/native_area.json','w'),indent=2)
print('A0_AREA_READ_PASS',len(a),'masters',len(b.getInsts()),'cells')
