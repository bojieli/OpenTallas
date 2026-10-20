import json,sys
from pathlib import Path
p=Path(sys.argv[1]);j=json.loads((p/'mapped.json').read_text());counts={};area=0
def walk(top,active):
 global area
 assert top not in active,('recursive module',top)
 for x in j['modules'][top].get('cells',{}).values():
  t=x['type'];mod=j['modules'].get(t,{})
  if t=='$scopeinfo':continue
  if mod.get('cells'):
   walk(t,active|{top})
  else:
   counts[t]=counts.get(t,0)+1;area+=float(mod.get('attributes',{}).get('area',0))
top=sys.argv[2] if len(sys.argv)>2 else 'ot_s81svc7_chunk_reduce'
walk(top,set())
n=json.loads((p/'census.json').read_text());r=dict(std_um2=area,flops=sum(v for k,v in counts.items() if k.startswith('DFF')),macros=sum(v for k,v in counts.items() if k.startswith('ot_sram')),native_status=n['status'],max_dynamic_loads=n['max_dynamic_loads'],arithmetic_edges=42 if top.endswith('_core') else 35,scope='already staggered8product reduction only; parent weights/mul/dequant/skew/tree not included')
(p/'summary.json').write_text(json.dumps(r,indent=2)+'\n');print(r)
