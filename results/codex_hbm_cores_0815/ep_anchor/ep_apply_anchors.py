"""Clone a placed EP database and anchor three existing data/reset flops.
Input is mounted read-only. No source, ports, connectivity or instance creation.
Check placement before writing a new database; current kit is never mutated.
"""
import hashlib,json,os
from pathlib import Path
import openroad

src=Path(os.environ['ODB_IN']);out=Path(os.environ['ODB_OUT']);model=json.loads(Path(os.environ['MODEL']).read_text())
moves=model['models'][0]['moves']
design=openroad.Design(openroad.Tech());design.readDb(str(src));block=design.getBlock();dbu=block.getDb().getTech().getDbUnitsPerMicron()
norm=lambda n:n.replace(chr(92),'')
by={}
for i in block.getInsts():by.setdefault(norm(i.getName()),[]).append(i)
before=(len(block.getInsts()),len(block.getNets()),len(block.getBTerms()))
done=[]
for name,box in moves.items():
    found=by.get(norm(name),[])
    if len(found)!=1:raise RuntimeError('anchor instance missing/ambiguous '+name)
    inst=found[0];bb=inst.getBBox();old=[bb.xMin()/dbu,bb.yMin()/dbu,bb.xMax()/dbu,bb.yMax()/dbu]
    x,y,x1,y1=box;xx,yy=int(round(x*dbu)),int(round(y*dbu))
    rows=[r for r in block.getRows() if r.getOrigin()[1]==yy and r.getBBox().xMin()<=xx and r.getBBox().xMax()>=int(round(x1*dbu))]
    if not rows:raise RuntimeError('no legal row for '+name)
    inst.setOrient(rows[0].getOrient());inst.setLocation(xx,yy);inst.setPlacementStatus('FIRM')
    actual=inst.getBBox();got=[actual.xMin()/dbu,actual.yMin()/dbu,actual.xMax()/dbu,actual.yMax()/dbu]
    if any(abs(a-b)>.001 for a,b in zip(got,box)):raise RuntimeError('placed box mismatch '+str((name,box,got)))
    done.append(dict(name=inst.getName(),old_box_um=old,new_box_um=got,row=rows[0].getName()))
assert before==(len(block.getInsts()),len(block.getNets()),len(block.getBTerms()))
design.evalTclString('check_placement -verbose')
design.writeDb(str(out))
report=dict(scope=__doc__,input_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),
            output_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),moves=done,
            instances=before[0],nets=before[1],ports=before[2],connectivity_changed=False,added_cycles=0,
            check_placement='PASS',next='Dump actual successor geometry and review before any CTS or STA')
Path(os.environ['RECEIPT']).write_text(json.dumps(report,indent=1)+'\n')
print('EP_ANCHOR_COPY_PASS moved='+str(len(done)))
