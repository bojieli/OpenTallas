#!/usr/bin/env python3
"""Native all-driver census, including resets, after kept-source re-synthesis."""
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

spec=importlib.util.spec_from_file_location('tl','textbook_lint.py')
m=importlib.util.module_from_spec(spec)
sys.modules['tl']=m
spec.loader.exec_module(m)
raw=Path('resynth.v').read_bytes()
g,top=m.flatten(m.parse_verilog(raw.decode()),'qkd_hr_core_order_n32')
a=m.build(g,None)
clocks,_=m.clock_nets(g,a)
rows=[]
for net,(ci,pin) in a['driver'].items():
    if net in clocks or net<=3 or (ci>=0 and a['kind'][ci] in ('buf','tie')):
        continue
    count,flops,_=m.bufinv_fanout(g,a,net,clocks)
    rows.append(dict(net=m.net_label(g,a,net),loads=count,flops=flops))
rows.sort(key=lambda d:d['loads'],reverse=True)
result=dict(top=top,sha256=hashlib.sha256(raw).hexdigest(),
            cells=len(g.cells),kinds=dict(Counter(a['kind'])),
            checked_drivers=len(rows),maximum_loads=max((r['loads'] for r in rows),default=0),
            violating_drivers=sum(r['loads']>32 for r in rows),top_drivers=rows[:20])
profile=dict(schema='opentallas.ref_tile.reset_landing.v1',top=top,enable=True,
             stages=2,clock='ck_core',reset_ports=['host_rst_n'],
             first_copies=dict(host_rst_n=12),copies=dict(host_rst_n=288))
result['reset_profile']=profile
result['reset_proof']=m.balanced_reset_proof(g,a,'host_rst_n',g.ports['host_rst_n'][1],profile)
result['pass']=(result['maximum_loads']<=32 and result['kinds'].get('macro')==6
                and result['reset_proof']['pass'])
Path('native32.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
raise SystemExit(0 if result['pass'] else 1)
