import odb,sys,json
D=odb.dbDatabase.create();odb.read_db(D,sys.argv[1]);b=D.getChip().getBlock()
norm=lambda s:s.replace('\\','')
reg={i.getId():i for i in b.getInsts() if 'DFF' in i.getMaster().getName()}
out=next(i for i in reg.values() if norm(i.getName())=='u_bound.u_bout_dr_o/q[516]$_DFF_P_')
def roots(net,seen=None):
 seen=set() if seen is None else seen
 if net is None or net.getId() in seen:return set()
 seen.add(net.getId());r=set()
 for t in net.getITerms():
  if t.getIoType()!='OUTPUT' or t.getSigType() in ('POWER','GROUND'):continue
  i=t.getInst()
  if i.getId() in reg:r.add(i.getName());continue
  for t2 in i.getITerms():
   if t2.getIoType()=='INPUT' and t2.getSigType() not in ('POWER','GROUND','CLOCK'):r.update(roots(t2.getNet(),seen))
 return r
r=roots(out.findITerm('D').getNet());print('DR516_ACTUAL_DRIVERS',json.dumps(sorted(r)));assert len(r)==1
