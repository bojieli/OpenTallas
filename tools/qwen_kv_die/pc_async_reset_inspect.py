#!/usr/bin/env python3
"""Read-only actual source graph census for private PC async reset conditioners."""
from collections import Counter
import importlib.util
import json
from pathlib import Path
import re
import sys

sp=importlib.util.spec_from_file_location('tl','textbook_lint.py')
m=importlib.util.module_from_spec(sp);sys.modules['tl']=m;sp.loader.exec_module(m)

def terminals(g,a,start):
    stack=[(start,0)];seen=set();out=[];exports=[]
    while stack:
        net,inv=stack.pop()
        if (net,inv) in seen:continue
        seen.add((net,inv))
        exports += [(p,inv) for p in a['out_ports'].get(net,[])]
        for ci,pin,unused in a['loads'].get(net,[]):
            if a['kind'][ci]=='buf':
                neg=bool(re.match('^(INV|CKINV)',g.cells[ci][0]))
                stack += [(x,inv^neg) for pn,bits in g.cells[ci][2].items() if a['pin_dir'][ci][pn]=='out' for x in bits]
            else:out.append((ci,pin,net,inv))
    return out,exports

report={}
for case in ['qkd_kvs_pc','qkd_kvs_pc_h']:
    g,top=m.flatten(m.parse_verilog((Path(case)/'resynth.v').read_text()),case+'_n32')
    a=m.build(g,None);row={}
    for reset,clock in [('rst_n','ck'),('hrst_n','hck')]:
        ends,exports=terminals(g,a,g.ports[reset][1])
        cells=[]
        for ci,pin,net,inv in ends:
            typ,name,pins=g.cells[ci]
            output=next((x for pn,bits in pins.items() if a['pin_dir'][ci][pn]=='out' for x in bits),None)
            consumers,exp=terminals(g,a,output) if output is not None else ([],[])
            cells.append(dict(type=typ,name=name,root_pin=pin,root_polarity=inv,
                pins={p:[g.net_name[x] for x in bs] for p,bs in pins.items()},
                output_consumers=[dict(type=g.cells[c][0],name=g.cells[c][1],pin=p,polarity=i) for c,p,n,i in consumers],output_exports=exp))
        row[reset]=dict(clock=clock,root_terminal_loads=len(ends),root_exports=exports,cells=cells)
    report[case]=row
Path('inspection.json').write_text(json.dumps(report,indent=2)+'\n')
for case,row in report.items():
    for reset,v in row.items():
        print(case,reset,'root',v['root_terminal_loads'],'types',Counter((c['type'],c['root_pin'],c['root_polarity']) for c in v['cells']))
        for c in v['cells']:print(c['name'],c['pins'],'Qloads',len(c['output_consumers']),'types',Counter((d['type'],d['pin'],d['polarity']) for d in c['output_consumers']))
