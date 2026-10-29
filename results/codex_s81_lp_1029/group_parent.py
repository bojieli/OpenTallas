#!/usr/bin/env python3
"""Attribute retained physical cells to exact emitted parent instance prefixes; leave merged ABC logic unassigned."""
from collections import Counter,defaultdict
from functools import lru_cache
import json,re,sys
from pathlib import Path
b=Path(sys.argv[1]);m={k.lstrip('\\'):v for k,v in json.load(open(b/'mapped_stat.json'))['modules'].items()};meta=json.load(open(b/'sources.json'));macro=set(meta['macros']);groups=defaultdict(Counter)
@lru_cache(None)
def cells(n):
 if n=='$scopeinfo':return Counter()
 if n in macro or 'ASAP7' in n:return Counter({n:1})
 assert n in m,n
 r=Counter()
 for t,num in m[n]['num_cells_by_type'].items():
  for k,v in cells(t.lstrip('\\')).items():r[k]+=num*v
 return r
active=False;count=0
with (b/'parent_mapped.v').open() as f:
 for line in f:
  mm=re.match(r'module\s+(\\\S+|\w+)',line)
  if mm:active=mm.group(1).lstrip('\\')==meta['top']
  if not active:continue
  mm=re.match(r'\s+(\\\S+|[A-Za-z_$][\w$]*)\s+(\\\S+|[A-Za-z_$][\w$]*)\s*\(',line)
  if not mm:continue
  typ,inst=(x.lstrip('\\') for x in mm.groups());prefix=inst.split('.')[0]
  if not prefix.startswith('u_'):prefix='MERGED_ABC_OR_INFRA'
  count+=1
  for t,n in cells(typ).items():groups[prefix][t]+=n
rows=[]
for p,c in groups.items():
 rows.append(dict(prefix=p,std_cells=sum(n for k,n in c.items() if k not in macro),macros={k:n for k,n in c.items() if k in macro},cell_histogram=dict(c)))
rows.sort(key=lambda r:-r['std_cells']);total=sum(r['std_cells'] for r in rows);(b/'instance_costs.json').write_text(json.dumps(dict(scope='Mapped physical cells by preserved instance prefix; ABC merged gates retain generated names',top_instances_parsed=count,std_cells=total,groups=rows),indent=1)+'\n')
print(json.dumps([r for r in rows if r['prefix'].startswith('u_u_lnl') or r['prefix'] in ('u_u_land','u_u_lep')],indent=1));print('ALLGROUPS_TOTAL',total,'instances',count,'groups',len(rows))
