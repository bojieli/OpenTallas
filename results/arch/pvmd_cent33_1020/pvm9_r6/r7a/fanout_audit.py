# r7a (HBM-SMATT9): native_census.py is a MAPPED-netlist (pre-layout) census; on the post-CTS netlist it
# walks the CTS tree (clk -> wire9654 repair_clock_nets buffer -> clkbuf/delaybuf) as data fanout (635) and
# flags every TAPCELL as missing Liberty. This audit applies the same <=32 dynamic-load rule to the
# post-GRT odb with the clock network (BFS from port clk through 1-in/1-out cells) and PG excluded.
import odb,os,json,collections
db=odb.dbDatabase.create();odb.read_db(db,os.environ['R7_ODB']);b=db.getChip().getBlock()
def ins_outs(inst):
  i=[t for t in inst.getITerms() if t.getNet() and str(t.getIoType())=='INPUT' and str(t.getSigType()) not in('POWER','GROUND')]
  o=[t for t in inst.getITerms() if t.getNet() and str(t.getIoType())=='OUTPUT']
  return i,o
clk=set();todo=[t.getNet() for t in b.getBTerms() if t.getName()=='clk' and t.getNet()]
while todo:
  n=todo.pop()
  if n.getId() in clk:continue
  clk.add(n.getId())
  for t in n.getITerms():
    if str(t.getIoType())!='INPUT':continue
    i,o=ins_outs(t.getInst())
    if len(i)==1 and len(o)==1:todo.append(o[0].getNet())
rows=[];over=[]
for n in b.getNets():
  if str(n.getSigType()) in('POWER','GROUND') or n.getId() in clk:continue
  loads=sum(1 for t in n.getITerms() if str(t.getIoType())=='INPUT')+sum(1 for t in n.getBTerms() if str(t.getIoType())=='OUTPUT')
  drv=[t.getInst().getName()+'/'+t.getMTerm().getName() for t in n.getITerms() if str(t.getIoType())=='OUTPUT'] or ['PORT/'+t.getName() for t in n.getBTerms() if str(t.getIoType())=='INPUT']
  rows.append((loads,n.getName(),drv[:1]))
  if loads>32:over.append((loads,n.getName(),drv[:1]))
rows.sort(reverse=True);over.sort(reverse=True)
d=dict(schema='opentallas.r7a.post_grt_fanout.v1',odb=os.environ['R7_ODB'],clock_network_nets=len(clk),nets=len(rows),limit=32,max_loads=rows[0][0] if rows else 0,over32=len(over),top=rows[:15],over=over[:200],status='PASS' if not over else 'FAIL')
open(os.environ['R7_OUT'],'w').write(json.dumps(d,indent=1)+'\n')
print('R7_FANOUT',{k:d[k] for k in('status','max_loads','over32','clock_network_nets','nets')},rows[:5])
