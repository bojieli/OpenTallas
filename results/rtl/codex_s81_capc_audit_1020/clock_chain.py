"""Read-only native clock-pad topology for a bounded physical compensation model."""
import odb,sys,json
from pathlib import Path
db=odb.dbDatabase.create();odb.read_db(db,sys.argv[1]);b=db.getChip().getBlock();out={}
for inst in ['u_p.u_core.g_hard.u_rt','u_p.u_core.g_ld3.u_ld3']:
    n=b.findInst(inst).findITerm('clk').getNet();chain=[];seen=set()
    while n and n.getId() not in seen:
        seen.add(n.getId());ds=[x for x in n.getITerms() if str(x.getIoType())=='OUTPUT']
        if len(ds)!=1:break
        d=ds[0];i=d.getInst();inputs=[x for x in i.getITerms() if str(x.getIoType())=='INPUT'];loads=[x for x in n.getITerms() if str(x.getIoType())=='INPUT']
        chain.append({'inst':i.getName(),'master':i.getMaster().getName(),'location_dbu':list(i.getLocation()),'out_net':n.getName(),'input_count':len(inputs),'out_loads':len(loads)})
        if len(inputs)!=1:break
        n=inputs[0].getNet()
    out[inst]=chain
Path(sys.argv[2]).write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
