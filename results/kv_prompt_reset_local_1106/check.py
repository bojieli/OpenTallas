import odb,re
D=odb.dbDatabase.create();odb.read_db(D,"/out/qualified_reset.odb");b=D.getChip().getBlock()
copies=[];netmap={}
for i in b.getInsts():
 m=re.fullmatch(r"(.*)_qrr[0-9]+",i.getName())
 if not m:continue
 o=b.findInst(m[1]);assert o and o.getMaster()==i.getMaster(),i.getName()
 copies.append((i,o))
 for t in i.getITerms():
  if t.getMTerm().getIoType()=="OUTPUT" and t.getNet():
   orig=o.findITerm(t.getMTerm().getName()).getNet();assert orig
   netmap[t.getNet().getName()]=orig.getName()
def check():
 for i,o in copies:
  for t in i.getITerms():
   m=t.getMTerm()
   if m.getIoType()!="INPUT" or m.getSigType() in ("POWER","GROUND"):continue
   ot=o.findITerm(m.getName());n=t.getNet();on=ot.getNet()
   assert bool(n)==bool(on),(i.getName(),m.getName(),"connection-presence")
   if not n:continue
   logical=netmap.get(n.getName(),n.getName())
   assert logical==on.getName(),(i.getName(),m.getName(),logical,on.getName())
   if "DFF" in i.getMaster().getName():assert n==on,(i.getName(),m.getName(),"sequential-input-must-match-exactly")
check();print("STRUCTURAL_REPLICA_PASS",len(copies),"cells",len(netmap),"outputs; every root D/CK/async identical and every qualifier input preserved")
# Deliberately cross-wire a cloned AND sideinput; the same checker must reject it.
victim=next(i for i,o in copies if i.getMaster().getName().startswith("AND4"))
terms=[t for t in victim.getITerms() if t.getMTerm().getIoType()=="INPUT"]
a=terms[0];bad=next(t.getNet() for t in terms[1:] if t.getNet()!=a.getNet());a.disconnect();a.connect(bad)
try:check()
except AssertionError as e:print("MUTANT_CAUGHT",e)
else:raise RuntimeError("qualifier-sideinput mutant escaped")
