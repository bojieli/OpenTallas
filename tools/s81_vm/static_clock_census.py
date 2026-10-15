#!/usr/bin/env python3
"""Count actual generic FF bits by distinct external clock from flattened Yosys JSON."""
import argparse,collections,hashlib,json,pathlib
p=argparse.ArgumentParser();p.add_argument('netlist');p.add_argument('module');p.add_argument('output');p.add_argument('--clocks',nargs='+',required=True);p.add_argument('--resets',nargs='+',required=True);a=p.parse_args()
f=pathlib.Path(a.netlist);m=json.loads(f.read_text())['modules'][a.module]
names={b:f'{n}[{i}]'for n in a.clocks for i,b in enumerate(m['ports'][n]['bits'])}
roots=collections.Counter()
for cell in m['cells'].values():
 if 'ff'in cell['type'].lower()and 'CLK'in cell['connections']:
  clock=cell['connections']['CLK'];assert len(clock)==1 and clock[0]in names,('nonboundaryclock',clock)
  roots[names[clock[0]]]+=len(cell['connections']['Q'])
result={'netlist_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'module':a.module,'roots':dict(sorted(roots.items())),'unique_clocks':len(roots),'FF':sum(roots.values()),'max_FF_per_root':max(roots.values()),'reset_pins':{n:len(m['ports'][n]['bits'])for n in a.resets}}
pathlib.Path(a.output).write_text(json.dumps(result,indent=2)+'\n');print(result['unique_clocks'],result['FF'],result['max_FF_per_root'])
