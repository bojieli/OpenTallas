import openroad, odb, collections, json
from openroad import Design, Tech
t=Tech(); d=Design(t); d.readDb("/n/grt/grt.odb")
b=d.getBlock()
c=collections.Counter(i.getMaster().getName() for i in b.getInsts())
print("insts",sum(c.values())); print(c.most_common(40))
print("bterms",len(b.getBTerms()), [x.getName() for x in list(b.getBTerms())[:5]])
r=b.findNet("root"); print("root net", r and [ (it.getInst().getName(),it.getMTerm().getName()) for it in r.getITerms()][:5])
# tap net example
for n in ["t_hg_EN_0__clk","ck_t_hg_EN_0__clk"]:
  x=b.findNet(n)
  if x: print(n,[(it.getInst().getName(),it.getInst().getMaster().getName(),it.getMTerm().getName()) for it in x.getITerms()][:8], [bt.getName() for bt in x.getBTerms()])
sig=collections.Counter(n.getSigType() for n in b.getNets()); print(sig)
# FF clock pins: which nets
ffc=collections.Counter()
for i in b.getInsts():
  m=i.getMaster().getName()
  if m.startswith("DFF") or "DFF" in m:
    for it in i.getITerms():
      if it.getMTerm().getName()=="CLK": ffc[it.getNet().getName() if it.getNet() else None]+=1
print("ff clk nets",len(ffc),ffc.most_common(10))
