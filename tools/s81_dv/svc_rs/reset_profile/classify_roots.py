#!/usr/bin/env python3
"""Read-only source aliases for actual prior native failures; no acceptance changes."""
import sys,json,gzip,collections,re
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
import textbook_lint as T
net,census,out=sys.argv[1:];g,top=T.flatten(T.parse_verilog(Path(net).read_text()),'dsdv_svc_att')
r=json.load(gzip.open(census,'rt'));targets=sorted(r['violations'],key=lambda x:x['loads'],reverse=True)[:80]
roots={g.find(g.net_id[t['net']])for t in targets if t['net']in g.net_id};aliases=collections.defaultdict(list)
for i,n in enumerate(g.net_name):
 root=g.find(i)
 if root in roots and not re.match(r'^_\d+_$',n):aliases[root].append(n)
cells={n:(ty,p)for ty,n,p in g.cells};records=[]
for t in targets:
 q=dict(t);q.pop('endpoints',None);root=g.find(g.net_id[t['net']]);q['source_aliases']=aliases[root]
 n=t['driver'].rsplit('/',1)[0]
 if n in cells:
  ty,pins=cells[n];q['master']=ty;q['input_named_aliases']={p:[g.net_name[x]for x in bs[:4]]for p,bs in pins.items()if p not in ['Q','QN','Y','RESETN','SETN','CLK']}
 records.append(q)
Path(out).write_text(json.dumps({'scope':'Immutable prior NORST map source classification only; actual fmem and reset successor effects not inferred.','top':top,'records':records},indent=2)+'\n')
for q in records[:35]:print(q['loads'],q['driver'],q['source_aliases'])
