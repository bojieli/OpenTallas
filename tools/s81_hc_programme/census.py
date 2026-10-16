#!/usr/bin/env python3
"""Actual optimized generic sequential state; no timing/physical qualification."""
import argparse,collections,hashlib,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();root=Path(__file__).resolve().parents[2];a.out.mkdir(parents=True,exist_ok=True)
files=subprocess.check_output(['python3',str(root/'tools/s81_hc_current/lint.py'),'--files'],text=True).splitlines()
files=[f for f in files if not f.startswith('physical/')]
top='ot_s81_hc_cseq_static'
y='read_verilog -sv -DSYNTHESIS '+' '.join(str(root/f)for f in files)+'\n'
y+=f'chparam -set COMMAND_POST_AGES 1 {top}\nhierarchy -check -top {top}\nproc\nflatten\nopt\nmemory_map\nopt\nwrite_json {a.out.resolve()}/generic.json\nstat\n'
(a.out/'census.ys').write_text(y)
with (a.out/'census.log').open('w')as f:r=subprocess.run(['yosys','-s',str(a.out/'census.ys')],stdout=f,stderr=subprocess.STDOUT)
if r.returncode:raise SystemExit(r.returncode)
m=json.loads((a.out/'generic.json').read_text())['modules'][top];roots={};types=collections.Counter()
for name,c in m['cells'].items():
 t=c['type'];types[t]+=1
 if t.startswith(('$dff','$adff','$sdff')):
  key=tuple(c['connections']['CLK']);roots[key]=roots.get(key,0)+len(c['connections']['Q'])
ports={tuple(v['bits']):n for n,v in m['ports'].items()}
rec=dict(top=top,params={'COMMAND_POST_AGES':1},generic_sequential_bits_per_clock={ports.get(k,str(k)):v for k,v in roots.items()},cell_types=dict(types),source_sha256={f:hashlib.sha256((root/f).read_bytes()).hexdigest()for f in files},scope='Optimized generic source state only; no mapped area/clock/native/physical proof')
(a.out/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec['generic_sequential_bits_per_clock']))
