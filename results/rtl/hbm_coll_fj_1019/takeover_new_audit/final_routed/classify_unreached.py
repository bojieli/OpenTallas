import odb,os,json,collections
from pathlib import Path
p=Path(os.environ['AUDIT_ODB']);db=odb.dbDatabase.create();odb.read_db(db,str(p));b=db.getChip().getBlock()
r=json.load(open(os.environ['AUDIT_REACH_REPORT']));groups=collections.Counter();details=[]
for item in r['unreached_capture_pins']:
 n=b.findNet(item['net']);drivers=[]
 for t in n.getITerms():
  if str(t.getIoType())=='OUTPUT':
   i=t.getInst();m=i.getMaster();drivers.append({'instance':i.getName(),'master':m.getName(),'master_type':str(m.getType()),'pin':t.getMTerm().getName(),'input_nets':[(x.getMTerm().getName(),x.getNet().getName() if x.getNet() else None)for x in i.getITerms() if str(x.getIoType())=='INPUT']})
 sinkpin=item['sink'][2].rsplit('/',1)[-1]
 types=','.join(sorted(set(x['master_type'] for x in drivers)))or'NO_DRIVER'
 groups[sinkpin+' <- '+types]+=1
 details.append(dict(item,net_type=str(n.getSigType()),drivers=drivers,bterms=[x.getName() for x in n.getBTerms()]))
out=dict(schema='opentallas.unreached_pin_classes.v1',scope='literal driver master types, no assumption of constants or waived functional pins',count=len(details),classes=dict(groups),details=details)
Path(os.environ['AUDIT_OUT']).write_text(json.dumps(out,indent=2)+'\n');print(out['classes'])
