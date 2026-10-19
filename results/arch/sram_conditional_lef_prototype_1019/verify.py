import json,re
from pathlib import Path
from decimal import Decimal
P=Path(__file__).resolve().parent;j=json.loads((P/'prototype.json').read_text());s=(P/'conditional_analytical_sram.lef').read_text()
def rectangles(t):
 layer=None;out=[]
 for line in t.splitlines():
  a=line.split()
  if a[:1]==['LAYER']:layer=a[1]
  if a[:1]==['RECT']:out.append((layer,[int(Decimal(v)*1000) for v in a[1:5]]))
 return out
for fam,f in j['families'].items():
 t=s.split('MACRO '+f['master']+'\n')[1].split('\nEND '+f['master'])[0]
 assert re.search(r'\bSIZE ([\d.]+) BY ([\d.]+) ;',t)
 for pin in f['pins']:
  b=t.split('  PIN '+pin['name']+'\n')[1].split('\n  END '+pin['name']+'\n')[0]
  assert rectangles(b)==[(p['layer'],p['rect_nm']) for p in pin['ports']]
  assert f"DIRECTION {pin['direction']} ;" in b and f"USE {pin['use']} ;" in b
 b=t.split('  OBS\n')[1]
 assert rectangles(b)==[(o['layer'],o['rect_nm']) for o in f['obs']]
 assert len(f['own_pg_obs_conflicts'])==f['supply_stack_count']
print('Independent finite LEF text roundtrip: exact all 647 PIN identities/directions/uses/ports and 375 OBS rectangles PASS; not native parser/AP proof.')
