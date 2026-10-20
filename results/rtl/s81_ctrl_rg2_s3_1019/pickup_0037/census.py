import json,hashlib
from pathlib import Path
import textbook_lint as t
for name in ['ctrl','coll']:
 p=Path(name+'.v'); g,top=t.flatten(t.parse_verilog(p.read_text()),None);a=t.build(g,None);clk,_=t.clock_nets(g,a)
 rows=[]
 for x,d in a['driver'].items():
  if x in clk or x<=3:continue
  ci=d[0]
  if ci>=0 and a['kind'][ci] in ('buf','tie'):continue
  n,ff,ex=t.bufinv_fanout(g,a,x,clk)
  if n>32:rows.append({'net':t.net_label(g,a,x),'loads':n,'flop_loads':ff,'driver':g.cells[ci][1] if ci>=0 else 'PORT','kind':a['kind'][ci] if ci>=0 else 'port'})
 rows.sort(key=lambda r:-r['loads'])
 result={'top':top,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'nonclock_roots_over32':len(rows),'over32':rows,'macro_cells_direction_inferred':a['kind'].count('macro'),'scope':'mapped native standard-cell roots, BUF/INV collapsed; no physical reach or complete macro-direction claim'}
 Path(name+'_census.json').write_text(json.dumps(result,indent=1));print(name,len(rows),rows[:8],flush=True)
