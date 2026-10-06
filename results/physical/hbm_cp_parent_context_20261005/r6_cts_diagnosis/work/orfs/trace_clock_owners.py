import odb,json
from pathlib import Path
r=Path('/work');db=odb.dbDatabase.create();odb.read_db(db,str(r/'cts_failure.odb'));b=db.getChip().getBlock()
clock=[i for i in b.getInsts() if i.getName().startswith(('clkbuf','clkload'))]
def owners_of(net,visited=None):
 visited=set() if visited is None else visited
 if net is None or net.getName() in visited:return {}
 visited.add(net.getName());found={}
 for t in net.getITerms():
  m=t.getMTerm();i=t.getInst()
  if str(m.getIoType()) not in ('INPUT','INOUT'):continue
  if i.getMaster().getName().startswith('DFF') and m.getName() in ('CLK','CLKN','CK'):
   g=i.getGroup();found[i.getName()]=None if g is None else g.getName()
  elif i.getName().startswith('clkbuf') or i.getMaster().getName().startswith('INV'):
   for o in i.getITerms():
    if str(o.getMTerm().getIoType())=='OUTPUT':found.update(owners_of(o.getNet(),visited))
 return found
out=[]
for i in clock:
 terms=[t for t in i.getITerms() if str(t.getMTerm().getIoType())==('INPUT' if i.getName().startswith('clkload') else 'OUTPUT')]
 ff={}
 for t in terms:ff.update(owners_of(t.getNet()))
 counts={}
 for g in ff.values():counts[str(g)]=counts.get(str(g),0)+1
 out.append(dict(cell=i.getName(),master=i.getMaster().getName(),actual_FF_owner_groups=counts,actual_FF_sink_count=len(ff)))
(r/'cts_clock_owner_trace.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps([x for x in out if 'cp_association' in x['actual_FF_owner_groups']],indent=2))
