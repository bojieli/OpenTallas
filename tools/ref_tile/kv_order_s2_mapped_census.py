#!/usr/bin/env python3
"""Mapped register fanout census; run on fleet beside textbook_lint.py."""
import hashlib,json,sys
from pathlib import Path
import textbook_lint as T
p=Path(sys.argv[1]);dump=json.loads(Path(sys.argv[2]).read_text()) if len(sys.argv)>2 else None
g,top=T.flatten(T.parse_verilog(p.read_text()),None);a=T.build(g,dump);clk=T.clock_nets(g,a);rows=[]
for net,(ci,pin) in a['driver'].items():
 if net in clk or ci<0 or a['kind'][ci]!='ff':continue
 n,ff,ex=T.bufinv_fanout(g,a,net,clk)
 rows.append(dict(cell=g.cells[ci][1],master=g.cells[ci][0],pin=pin,net=T.net_label(g,a,net),loads=n,flop_loads=ff,example=ex))
rows.sort(key=lambda x:x['loads'],reverse=True)
out=dict(scope='actual mapped netlist; not timing or safe closure',sha256=hashlib.sha256(p.read_bytes()).hexdigest(),top=top,cells=len(g.cells),registers=sum(k=='ff' for k in a['kind']),macros=[dict(name=n,master=t) for (t,n,_),k in zip(g.cells,a['kind']) if k=='macro'],register_output_count=len(rows),over32_count=sum(x['loads']>32 for x in rows),max_register_loads=max(x['loads'] for x in rows),over32=[x for x in rows if x['loads']>32],top100=rows[:100])
Path('mapped_census.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k not in ('top100','over32')},indent=2));print('TOP20',json.dumps(rows[:20]))
