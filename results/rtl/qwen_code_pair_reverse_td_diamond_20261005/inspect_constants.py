import odb,json
from collections import Counter
db=odb.dbDatabase.create()
odb.read_db(db,"/work/route/results/asap7/kant_code_banklocal_reverse_ac019_r1/base/4_cts.odb")
b=db.getChip().getBlock()
for name in ("one_","zero_","VDD","VSS"):
 n=b.findNet(name)
 if n is None:continue
 terms=list(n.getITerms())
 print(json.dumps(dict(net=name,sigtype=str(n.getSigType()),special=n.isSpecial(),iterms=len(terms),bterms=[t.getName() for t in n.getBTerms()],masters=dict(Counter(t.getInst().getMaster().getName() for t in terms)),pins=dict(Counter(t.getMTerm().getName() for t in terms)),sample=[dict(inst=t.getInst().getName(),master=t.getInst().getMaster().getName(),pin=t.getMTerm().getName(),io=str(t.getMTerm().getIoType()),sigtype=str(t.getMTerm().getSigType())) for t in terms[:20]])))
