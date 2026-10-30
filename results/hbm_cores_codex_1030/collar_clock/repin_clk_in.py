#!/usr/bin/env python3
"""Unsigned D34e3 collar legacy clock alias geometry, no interface/cycle change."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ap=argparse.ArgumentParser()
ap.add_argument('base',type=Path)
ap.add_argument('out',type=Path)
a=ap.parse_args()
if a.out.exists():raise SystemExit('fresh output directory required')
shutil.copytree(a.base,a.out,copy_function=shutil.copy2,symlinks=False)
p=a.out/'die_plan.json';d=json.loads(p.read_text())
c=next(c for c in d['partition_types']['root']['hard_cores'] if c['inst']=='u_col_idx')
pins=json.loads((a.out/c['pins_file']).read_text())
name=lambda q:q.get('name',q.get('bus') if q.get('bit') is None else f"{q['bus']}[{q['bit']}]")
old={name(q):dict(q) for q in pins}
assert len(old)==len(pins)==1559
clk=old['clk'];alias=next(q for q in pins if name(q)=='clk_in')
assert clk['layer']=='M5' and abs(clk['x']-88.872)<1e-6 and abs(clk['y']-44.424)<1e-6
root_clk=next(q for q in pins if name(q)=='clk')
root_clk.update(layer='M5',x=43.224,y=43.2,w=0.048,h=0.48,face='C',track_note='Actual centre-entry M5 track0.024+900*0.048')
alias.update(layer='M5',x=44.664,y=43.2,w=0.048,h=0.48,face='C')
ce=json.loads((a.out/'clock_entries.json').read_text())['root']['u_col_idx']
assert ce['merged_clock_ports']==['clk','clk_in']
assert ce['xy_um']==[43.2,43.2]
assert set(old)=={name(q) for q in pins}
assert all(q==old[name(q)] for q in pins if name(q) not in ('clk','clk_in'))
f='cores/ot_hbm_static_cfg_collar_idx256r__88.992x88.992__codex_clk_alias1030.json'
(a.out/f).write_text(json.dumps(pins,indent=1)+'\n');c['pins_file']=f
c['note']+=' | Codex clock alias physical fix: actual clk centred at43.224,43.2 and clk_in M5 sized at44.664,43.2; sidecar and physical pins agree, 0 cycles'
p.write_text(json.dumps(d,indent=1)+'\n')
report=dict(base=str(a.base),plan_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),pins_sha256=hashlib.sha256((a.out/f).read_bytes()).hexdigest(),old_clk=old['clk'],new_clk=root_clk,old_clk_in=old['clk_in'],new_clk_in=alias,unchanged_pins=1557,pin_names_unchanged=True,clock_entries_unchanged=True,rtl_cycles_added=0,view_adopted=False)
(a.out/'codex_clock_alias_report.json').write_text(json.dumps(report,indent=1)+'\n')
print(json.dumps(report))
