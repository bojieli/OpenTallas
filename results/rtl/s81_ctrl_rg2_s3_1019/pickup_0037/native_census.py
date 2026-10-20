import json,hashlib
from pathlib import Path
import textbook_lint as t
for name in ['ctrl']:
 p=Path(name+'.v'); g,top=t.flatten(t.parse_verilog(p.read_text()),None);dump={'macros':[]}
 for typ,nm,pins in g.cells:
  if typ=='ot_sram_1r1w2c_16x340_p192':
   known={'wclk','rclk','r_ce_in','r_addr_in','rd_out','w_ce_in','w_addr_in','wd_in','w_mask_in'}
   if set(pins)-known:raise ValueError('unknown SRAM pin')
   dump['macros'].append({'name':nm,'master':typ,'pins':[[pn,0,0,'OUTPUT' if pn=='rd_out' else 'INPUT'] for pn in pins]})
 a=t.build(g,dump);clk,_=t.clock_nets(g,a)
 rows=[]; maxloads=0
 for x,d in a['driver'].items():
  if x in clk or x<=3:continue
  ci=d[0]
  if ci>=0 and a['kind'][ci] in ('buf','tie'):continue
  n,ff,ex=t.bufinv_fanout(g,a,x,clk)
  maxloads=max(maxloads,n)
  if n>32:rows.append({'net':t.net_label(g,a,x),'loads':n,'flop_loads':ff,'driver':g.cells[ci][1] if ci>=0 else 'PORT','kind':a['kind'][ci] if ci>=0 else 'port'})
 rows.sort(key=lambda r:-r['loads'])
 result={'top':top,'flops':a['kind'].count('ff'),'macros':a['kind'].count('macro'),'max_nonclock_loads':maxloads,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'nonclock_roots_over32':len(rows),'over32':rows,'macro_cells_explicit_directions':len(dump['macros']),'constant_output_pins':[name for name,(direction,bit) in g.ports.items() if direction=='output' and bit<=3],'scope':'mapped native standard-cell roots, BUF/INV collapsed; explicit production SRAM pin directions; no physical reach claim'}
 Path(name+'_census.json').write_text(json.dumps(result,indent=1));print(name,len(rows),rows[:8],flush=True)
