import collections
from openroad import Design, Tech
t=Tech(); d=Design(t); d.readDb("/n/grt/grt.odb"); b=d.getBlock(); D=1000
for cn in ["ck_r438_1","ck_r438_2","ck_r438_3","ck_r438_4","ck_r438_5","ck_r8143_0","ck_b6805","ck_r6840_0"]:
    i=b.findInst(cn)
    if not i: print(cn,"missing"); continue
    x,y=i.getLocation()
    for it in i.getITerms():
        if it.getMTerm().getName()=="Y" and it.getNet():
            n=it.getNet(); ld=collections.Counter(j.getInst().getMaster().getName() for j in n.getITerms() if not j.isOutputSignal())
            print(cn,i.getMaster().getName(),(x/D,y/D),i.getPlacementStatus(),"->",n.getName(),dict(ld),[bt.getName() for bt in n.getBTerms()][:3])
# FF-loaded clock nets: distribution
c=collections.Counter()
for n in b.getNets():
    if n.getSigType()!="CLOCK": continue
    k=sum(1 for j in n.getITerms() if j.getMTerm().getName()=="CLK")
    if k: c[k]+=1
print("ff per clock net histogram",sorted(c.items()))
r=b.findNet("root"); print("root loads",collections.Counter(j.getInst().getMaster().getName() for j in r.getITerms()))
