# DIE-QC-66/CLK: QC plan_qc52 count-aligned +1 cycle value event on the crossings that fail the low side of the count-align
# window on the v3 die clock (results/qc_die66_clk_1103/ca_v3/judge_v3_delta.json, 30 ports, ca_judge66.py on the v3 proof).
# Cycles only: DEPTH, tree ports, geometry unchanged (orthogonal to the DIE-QC-66/PLAN CB-row event). Format kept.
import json,sys
plan,delta=sys.argv[1],json.load(open(sys.argv[2]))
s=open(plan).read(); d=json.loads(s); assert json.dumps(d)+"\n"==s
ln=d["clock"]["landing_network"]; c=ln["count_aligned_cycles"]
miss=[p for p in delta if p not in c]; assert not miss,miss[:5]
assert all(v in (1,-1) for v in delta.values())
for p,v in delta.items(): c[p]=int(c[p])+v
open(plan,"w").write(json.dumps(d)+"\n"); print("ca delta",len(delta),"+1",sum(v>0 for v in delta.values()),"-1",sum(v<0 for v in delta.values()))
