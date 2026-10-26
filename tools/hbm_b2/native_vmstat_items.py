#!/usr/bin/env python3
"""Append the aggregate VM status to the root host observation readset.

Used to advance an already generated native B1 delta without regenerating its
unchanged delay and request-comparator records. make_wiring.py emits this
connection directly for new deltas. Existing observation fields keep their
bit offsets, and the registered observer chain adds zero cycles.
"""
import argparse
import json
import re
from pathlib import Path


def append_vmstat(d):
    rm=d['remaster']['obs_C']; ob=d['rebuild']['obs_C']['obs']
    assert rm['master']=='ot_hbm_obs_leaf'
    assert rm['params'].find('.LID(0)')>=0
    item=['vm_status4','vmstat',0,18]
    if item in ob:
        assert ob[-1]==item
        return d
    assert not any(e[0]=='vm_status4' for e in ob)
    n=sum(e[1] if e[0]=='const' else e[3]-e[2]+1 for e in ob)
    assert re.search(r'\.N\('+str(n)+r'\)',rm['params'])
    assert n+19<=512
    ob.append(item)
    rm['params']=re.sub(r'\.N\(\d+\)',f'.N({n+19})',rm['params'])
    d['items'].append(dict(id='R-VMSTAT-OBS',kind='wiring',status='done',
        what=f'vm_status4.vmstat[18:0] at obs_C bits {n}..{n+18}; original {n} bits unchanged; 0 added cycles; D-HBM-B1 observer core/pins rebuild'))
    return d


def main():
    ap=argparse.ArgumentParser(description=__doc__.splitlines()[0]);ap.add_argument('delta');ap.add_argument('--out',required=True);a=ap.parse_args()
    d=append_vmstat(json.loads(Path(a.delta).read_text()));Path(a.out).write_text(json.dumps(d,indent=1)+'\n')
    print('VMSTAT_OBS connected '+d['remaster']['obs_C']['params'])

if __name__=='__main__':main()
