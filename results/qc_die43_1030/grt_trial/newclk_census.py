import json,sys,collections
from pathlib import Path
import odb
src,res,out=sys.argv[1],sys.argv[2],sys.argv[3]
names=None
d=odb.dbDatabase.create();odb.read_db(d,src);b=d.getChip().getBlock()
# rebuild the new-clock list from routed? too heavy; use prefix census of all start_provider SIGNAL nets with no wire
drv=collections.Counter();snk=collections.Counter();ex=[];n_nets=0;layers=collections.Counter()
for n in b.getNets():
    if str(n.getSigType())!='SIGNAL' or n.getWire() is not None or not n.getName().startswith('start_provider'): continue
    n_nets+=1
    for t in n.getITerms():
        k=(t.getInst().getMaster().getName(),t.getMTerm().getName(),str(t.getMTerm().getSigType()))
        (drv if t.isOutputSignal() else snk)[k]+=1
    for t in n.getBTerms(): snk[('BTERM',t.getIoType(),'')]+=1
    if len(ex)<5: ex.append([n.getName(),[(t.getInst().getName(),t.getMTerm().getName()) for t in n.getITerms()][:6]])
r=dict(start_provider_unwired_signal_nets=n_nets,drivers=[[list(k),v] for k,v in drv.most_common(15)],sinks=[[list(k),v] for k,v in snk.most_common(20)],examples=ex)
Path(out).write_text(json.dumps(r,indent=1));print(json.dumps(r,indent=1))
