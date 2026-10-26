#!/usr/bin/env python3
"""Apply the physically owned compact VM typed ABI to v16 source edges.

Requires the new quadrant ABI first. Does not enable the unqualified HC engine.
"""
import copy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SP=ROOT/'tools/hbm_die_v15/v16_specs'
TAG='native-compact-0253'

def remap(endpoint):
    v=list(endpoint)
    if len(v)!=4 or v[0] not in ('hb_vms_NW','hb_vms_NE') or v[1] not in ('rq','rr'):return v
    size=136 if v[1]=='rq' else 2056
    lo,hi=v[2:]
    if lo<4*size and hi>3*size:raise ValueError(f'Live edge references retired group3: {v}')
    if lo>=4*size:v[2]-=size;v[3]-=size
    return v

def main():
    abi=json.loads((ROOT/'results/arch/hbm_vm_static_1014/quadrant_abi.json').read_text())
    expected={'SW':(3,5,2),'SE':(0,4,2),'NW':(3,5,3),'NE':(0,5,3)}
    for q,shape in expected.items():
        p=abi['quadrants'][q]['params'];assert tuple(p[k] for k in ('NC','RG','WG'))==shape,(q,p)
    # Existing source specs contain typed LG/quant/HBM paths beyond the retired port.
    for path in sorted(SP.glob('*.json')):
        d=json.loads(path.read_text())
        if d.get('vm_abi_mapping')==TAG or path.stem=='vm_compact_0253':continue
        changed=False
        for edge in d.get('edges',[]):
            for key in ('src','dst'):
                old=edge[key];edge[key]=remap(old);changed|=old!=edge[key]
        if changed:
            d['vm_abi_mapping']=TAG;path.write_text(json.dumps(d,indent=1)+'\n')
    # The v15 baseline is immutable. Replace only its moved typed edges by name.
    base=json.loads((ROOT/'results/arch/hbm_die_v15/source_contract/contract.json').read_text())
    s=dict(region='vm_compact_0253',author='Codex typed ABI integration',instances=[],edges=[],clocks=[],straps=[],gaps=[],drop_v15_edges=[],vm_abi_mapping=TAG,
           notes=['NW/NE readgroups0,1,2,4,5 ->0,1,2,3,4. No ties or missing producers added. Calendar packed offsets remain actualW187 source. Updated wrapper/bank physical views are UNQUALIFIED until source-bound gates.'])
    for edge in base['known_actual_edges']:
        a,b=remap(edge['source']),remap(edge['sink'])
        if (a,b)==(edge['source'],edge['sink']):continue
        s['drop_v15_edges'].append(edge['name'])
        s['edges'].append(dict(src=a,dst=b,bits=edge['bits'],clock='stream',basis='Exact live endpoint group mapping after deleting unused group3; baseline '+edge['name']))
    (SP/'vm_compact_0253.json').write_text(json.dumps(s,indent=1)+'\n')
    print('COMPACT_VM_EDGES updated; run complete_host_targets_2330.py and strict v16 binding next')
if __name__=='__main__':main()
