from pathlib import Path
from collections import Counter
import json
import textbook_lint as t
import sys
p=Path(sys.argv[1])
g,top=t.flatten(t.parse_verilog(p.read_text()),None);a=t.build(g,None);clk,_=t.clock_nets(g,a)
alias_map={}
for n,i in g.net_id.items():
 if not n.startswith("_"):alias_map.setdefault(g.find(i),[]).append(n)
rows=[]
for x,d in a['driver'].items():
 if x in clk or x<=3 or (d[0]>=0 and a['kind'][d[0]] in ('buf','tie')):continue
 count,ff,ex=t.bufinv_fanout(g,a,x,clk)
 if count<=32:continue
 stack=[x];seen={x};sinks=[]
 while stack:
  y=stack.pop()
  for ci,pn,_ in a['loads'].get(y,()):
   if a['kind'][ci]=='buf':
    for z in t._out_nets(g,a,ci):
     if z not in seen:seen.add(z);stack.append(z)
   else:sinks.append((ci,pn))
 groups=Counter('.'.join(g.cells[ci][1].split('.')[:5]) for ci,pn in sinks)
 aliases=alias_map.get(x,[])
 inputs=[]
 def upstream(bit,depth=0,seen=None):
  if seen is None:seen=set()
  if bit in seen or depth>12:return []
  seen.add(bit);v=a['driver'].get(bit)
  if v is None:return [g.net_name[bit]]
  if v[0]<0:return [t.net_label(g,a,bit)]
  if a['kind'][v[0]]=='ff':return [t.net_label(g,a,bit)]
  out=[]
  for pi,bs in g.cells[v[0]][2].items():
   for z in bs:
    if z!=bit:out+=upstream(z,depth+1,seen)
  return list(dict.fromkeys(out))
 inputs=[]
 if d[0]>=0:
  typ,n,pins=g.cells[d[0]]
  for pn,bits in pins.items():
   for bit in bits:
    prev=a['driver'].get(bit)
    if bit!=x and prev is not None:inputs.append(t.net_label(g,a,bit))
 rows.append(dict(root=t.net_label(g,a,x),kind=a['kind'][d[0]] if d[0]>=0 else 'port',loads=count,aliases=aliases[:16],inputs=inputs,upstream=upstream(x),consumer_groups=groups.most_common(8)))
rows.sort(key=lambda r:r['loads'],reverse=True)
Path(sys.argv[2]).write_text(json.dumps(rows,indent=1)+'\n')
print('cones',len(rows),flush=True)
