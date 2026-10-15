#!/usr/bin/env python3
"""Actual elaborated register census per physical clock-entry bit.

No ABC/CTS/area claim. Unoptimized live registers give a conservative sink
count for each real native KIND. Unknown clock cells fail, never disappear.
"""
import json
import argparse
import hashlib
from pathlib import Path
import re
import subprocess
import sys

root=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser();parser.add_argument('out');parser.add_argument('--mlat',type=int,default=3);parser.add_argument('--alat',type=int,default=3);parser.add_argument('--leaf',type=int,default=0);parser.add_argument('--kind',type=int,choices=[0,1,2]);opts=parser.parse_args();out=Path(opts.out).resolve();out.mkdir(parents=True,exist_ok=True)
files=re.findall(r'(?:rtl|physical)/[^\s\\]+\.(?:sv|v)',(root/'tools/hbm_static/su_arith_run.sh').read_text())
files=[f for f in files if '/data_store/'not in f and '/peers/'not in f and not f.startswith('physical/') and '/tb_'not in f]
records=[]
for kind in ([opts.kind] if opts.kind is not None else range(3)):
    job=out/f'kind{kind}';job.mkdir(exist_ok=True)
    commands='read_verilog -sv '+' '.join(files)+'\n'
    commands+=f'hierarchy -check -top ot_hbm_su_static_lane -chparam KIND {kind} -chparam LN 7 -chparam MLAT {opts.mlat} -chparam ALAT {opts.alat} -chparam LEAF {opts.leaf}\n'
    commands+='proc\nflatten\nmemory_map\nopt_clean\n'
    commands+=f'write_json {job}/netlist.json\n'
    (job/'census.ys').write_text(commands)
    with (job/'yosys.log').open('w')as log:
        subprocess.run(['yosys','-s',str(job/'census.ys')],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
    net=json.loads((job/'netlist.json').read_text())['modules']['ot_hbm_su_static_lane']
    names={bit:f'{port}[{i}]'for port,d in net['ports'].items()if port in ('clk_stage','clk_insert')for i,bit in enumerate(d['bits'])}
    sinks={n:0 for n in names.values()};unknown=[]
    for cellname,c in net['cells'].items():
        if c['type']in ('$dff','$adff','$sdff','$dffe','$adffe','$sdffe'):
            cl=c['connections']['CLK'];q=c['connections']['Q']
            if len(cl)!=1 or cl[0]not in names:unknown.append([cellname,c['type'],cl])
            else:sinks[names[cl[0]]]+=len(q)
        elif 'dff'in c['type'].lower()or 'latch'in c['type'].lower():unknown.append([cellname,c['type']])
    record=dict(kind=kind,clock_sink_upper_bound=sinks,unknown=unknown,
                max_sink=max(sinks.values()),all_under_15000=not unknown and max(sinks.values())<=15000)
    records.append(record)
    (job/'census.json').write_text(json.dumps(record,indent=2)+'\n')
report=dict(parameters=dict(LN=7,MLAT=opts.mlat,ALAT=opts.alat,LEAF=opts.leaf,FETCH_EXTRA_EDGES=2),qualified=False,method='Yosys proc/flatten/memory_map opt_clean register bits; no ABC/CTS',records=records,
            source_sha256={f:hashlib.sha256((root/f).read_bytes()).hexdigest()for f in files})
(out/'clock_census.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
if not all(r['all_under_15000']for r in records):sys.exit(1)
