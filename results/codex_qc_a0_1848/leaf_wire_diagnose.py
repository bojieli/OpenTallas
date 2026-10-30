"""Read an existing A0 clock-stage TSV; expose long final-net RC hidden by a linear Manhattan model.
Usage: python leaf_wire_diagnose.py TREE.tsv OUT.json
No timing run, RTL change, or clock-frame adjustment is made.
"""
import csv,json,sys
from collections import defaultdict
T={r['inst']:r for r in csv.DictReader(open(sys.argv[1]),delimiter='\t')}
rows=[]
for n,r in T.items():
    if r['kind']!='sink' or r['master'].startswith('ot_') or r['parent'] not in T: continue
    p=T[r['parent']]
    leg=abs(float(r['x'])-float(p['x']))+abs(float(r['y'])-float(p['y']))
    wire=float(r['in_min_r'])-float(p['out_min_r'])
    fit=max(0.,-1.28+.2823*leg)
    rows.append(dict(sink=n,leaf=r['parent'],leg_um=round(leg,3),wire_ff_ps=round(wire,3),
                     model_wire_ff_ps=round(fit,3),residual_ff_ps=round(wire-fit,3)))
rows.sort(key=lambda r:r['residual_ff_ps'],reverse=True)
summary=dict(sink_count=len(rows),max_residual=rows[0],p99_residual_ps=sorted(r['residual_ff_ps'] for r in rows)[int(.99*len(rows))],worst_sinks=rows[:12])
json.dump(summary,open(sys.argv[2],'w'),indent=2)
print(json.dumps({k:v for k,v in summary.items() if k!='worst_sinks'}))
