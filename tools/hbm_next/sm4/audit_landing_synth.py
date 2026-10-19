#!/usr/bin/env python3
"""Audit generic synthesized landing hierarchy; run synthesis on the fleet."""
import argparse
import gzip
from collections import Counter
import json
from pathlib import Path

def audit(data):
    modules=data['modules']
    rows={}
    for name,m in modules.items():
        if int(m.get('attributes',{}).get('blackbox','0'),2):
            continue
        clocks=set()
        for port in ['ck','ck_r','ck_w']:
            clocks.update(m.get('ports',{}).get(port,{}).get('bits',[]))
        loads=Counter()
        for c in m['cells'].values():
            for p,bits in c['connections'].items():
                if c.get('port_directions',{}).get(p)=='input':
                    loads.update(x for x in bits if isinstance(x,int) and x not in clocks)
        rows[name]={'max_data_loads':max(loads.values(),default=0),
                    'cells':dict(Counter(c['type'] for c in m['cells'].values())),
                    'memories':len(m.get('memories',{}))}
    inventory=Counter()
    def walk(name):
        for c in modules[name].get('cells',{}).values():
            typ=c['type'];inventory[typ]+=1
            if typ in modules and not int(modules[typ].get('attributes',{}).get('blackbox','0'),2):
                walk(typ)
    walk('hnx_pl_land_sram')
    assert inventory['ot_sram_1r1w2c_16x546_m1']==4,inventory
    assert inventory['hnx_land_valid_one']==65,inventory
    assert all(x['max_data_loads']<=32 for x in rows.values()),rows
    assert all(x['memories']==0 for x in rows.values()),rows
    return {'pass':True,'modules':rows,'native_macro_count':4,'kept_valid_copies':65,
            'note':'Generic synth/techmap evidence; parent technology-mapped physical gate remains required'}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('json');ap.add_argument('--out');a=ap.parse_args()
    payload=gzip.open(a.json,'rt').read() if a.json.endswith('.gz') else Path(a.json).read_text()
    result=audit(json.loads(payload))
    output=json.dumps(result,indent=2)+'\n'
    if a.out:Path(a.out).write_text(output)
    else:print(output,end='')
