# DIE-QC-57: QC plan_qc52 value event: +1 count_aligned_cycles on the crossings that fail the ring guard (<100 ps low side)
# on gen55a (physical-paths proof, START hop 400 um). DEPTH unchanged; K derived by count_align_bind at bind time.
import json,sys
plan,plus=sys.argv[1],json.load(open(sys.argv[2]))
s=open(plan).read(); d=json.loads(s); assert json.dumps(d)+"\n"==s
c=d["clock"]["landing_network"]["count_aligned_cycles"]
miss=[p for p in plus if p not in c]; assert not miss,miss[:5]
for p in plus: c[p]=int(c[p])+1
open(plan,"w").write(json.dumps(d)+"\n"); print("plus1",len(plus))
