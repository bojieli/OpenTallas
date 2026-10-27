import odb,json,os,collections
d=odb.dbDatabase.create();odb.read_db(d,os.environ["ODB"]);b=d.getChip().getBlock()
roots={}
all_sinks=set()
for i in b.getInsts():
 for t in i.getITerms():
  if t.getMTerm().getSigType()=="CLOCK" and t.getMTerm().getIoType()=="INPUT":all_sinks.add(i.getName()+"/"+t.getMTerm().getName())
for port in ["s0__clk[0]","s1__clk[0]"]:
 bt=b.findBTerm(port);assert bt is not None,port
 q=collections.deque([bt.getNet()]);seen=set();sinks=set()
 while q:
  n=q.popleft()
  if n is None or n.getId() in seen:continue
  seen.add(n.getId())
  for t in n.getITerms():
   mt=t.getMTerm()
   if mt.getIoType()!="INPUT":continue
   i=t.getInst()
   if mt.getSigType()=="CLOCK":sinks.add(i.getName()+"/"+mt.getName());continue
   if i.getMaster().getName().startswith(("BUF","INV","CLKBUF")):
    for o in i.getITerms():
     if o.getMTerm().getIoType()=="OUTPUT" and o.getNet() is not None:q.append(o.getNet())
 roots[port]=dict(sinks=len(sinks),nets=len(seen),sink_names=sorted(sinks))
covered=set().union(*(set(x["sink_names"]) for x in roots.values()));missing=all_sinks-covered
r=dict(roots=roots,total_clock_mterm_sinks=len(all_sinks),covered=len(covered),missing=sorted(missing),overlap=len(set(roots["s0__clk[0]"]["sink_names"])&set(roots["s1__clk[0]"]["sink_names"])))
print("PRE",len(all_sinks),{k:v["sinks"] for k,v in roots.items()})
for port in ["s0__clk[0]","s1__clk[0]"]:
 n=b.findBTerm(port).getNet()
 print("ROOT",port,n.getName(),[(t.getInst().getName(),t.getMTerm().getName(),t.getMTerm().getSigType(),t.getMTerm().getIoType()) for t in n.getITerms()][:8])
for i in b.getInsts():
 if "v_r" in i.getName():
  print("FFTERMS",[(t.getMTerm().getName(),t.getMTerm().getSigType(),t.getMTerm().getIoType(),t.getNet().getName() if t.getNet() else None) for t in i.getITerms()]);break
print({k:v for k,v in r.items() if k!="roots"});print({k:{a:z for a,z in v.items() if a!="sink_names"} for k,v in roots.items()})
open(os.environ["OUT"],"w").write(json.dumps(r,indent=1)+"\n")
