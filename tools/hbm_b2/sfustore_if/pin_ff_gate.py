#!/usr/bin/env python3
"""Require one distinct kept sequential endpoint for each of 782 live macro pins."""
import argparse, hashlib, json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('mapped_json');p.add_argument('--out',required=True);a=p.parse_args()
raw=Path(a.mapped_json).read_bytes();m=json.loads(raw)['modules']['ot_hbm_su_sfustore_hw_bank_if']
ff={k:v for k,v in m['cells'].items() if 'DFF' in v['type'].upper()}
q={};d={}
for k,v in ff.items():
    for bit in v['connections']['Q']:q.setdefault(bit,[]).append(k)
    for bit in v['connections']['D']:d.setdefault(bit,[]).append(k)
macros=[v for v in m['cells'].values() if v['type']=='ot_sram_1r1w_128x256_m1_r2c2'];assert len(macros)==1
seen=set();counts={}
for port in ['wd_in','w_mask_in','r_addr_in','w_addr_in','r_ce_in','w_ce_in','rd_out']:
    bits=macros[0]['connections'][port];bits=bits[:6] if 'addr' in port else bits
    for bit in bits:
        fs=(d if port=='rd_out' else q).get(bit,[])
        assert len(fs)==1,(port,bit,fs)
        assert fs[0] not in seen,('merged/shared interface FF',port,fs)
        seen.add(fs[0])
    counts[port]=len(bits)
assert len(seen)==782
r=dict(status='PASS',scope='one full-width bank generic mapped hard-macro netlist; actual library master geometry pending',
       live_pins=counts,unique_sequential_endpoints=len(seen),mapped_json_sha256=hashlib.sha256(raw).hexdigest())
Path(a.out).write_text(json.dumps(r,indent=1)+'\n');print(json.dumps(r))
