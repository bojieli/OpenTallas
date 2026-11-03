import json
from pathlib import Path
from collections import Counter
cs={x[-1]:x for s in open('candidate.tsv') if (x:=s.rstrip().split('\t'))[0]=='C'}
nodes=json.load(open('core_infra_plan.json'))['cells'];parents={x['name']:x['parent'] for x in nodes};leafs={x['name'] for x in nodes if x['name'] not in set(parents.values())}
with open('points.tsv','w') as f:
 for n,x in cs.items():
  typ='S' if x[2]=='S' else 'L' if n in leafs else None
  if typ:f.write(f"{typ}\t{n}\t{(float(x[4])+float(x[6]))/2}\t{(float(x[5])+float(x[7]))/2}\n")
print('actual FF',sum(x[2]=='S' for x in cs.values()),'existing leaves',len(leafs),'allnodes',len(nodes),flush=True)
