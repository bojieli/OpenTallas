#!/usr/bin/env python3
"""Collect four COMPLETE RTL head-field ranks; never fill missing rows with reference roots.

Output roots_rN.mem plugs directly into existing head_stage.py run. Its independent
expected logits/expect.mem must come from the golden checker, never this collector.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np


def collect(dirs, output):
    output.mkdir(parents=True, exist_ok=False)
    records=[]
    for rank, directory in enumerate(dirs):
        rec=json.loads((directory/'record.json').read_text())
        if rec['bad'] or rec['mutant'] or rec['groups']!=253:
            raise ValueError(f'incomplete/failing rank {rank}')
        z=np.load(directory/f'rtl_rank{rank}.npz')
        if z['roots'].shape!=(32320,2) or z['logits'].shape!=(32320,) or not z['seen'].all():
            raise ValueError(f'missing RTL rows rank {rank}')
        groups=json.loads((directory/'groups.json').read_text())
        if any(g['rank']!=rank or g['bad'] for g in groups):
            raise ValueError('rank identity or exactness failed')
        if records and any(rec[k]!=records[0][k] for k in ('xf_sha256','source','native_xf_chained','b_root_format','static_group_cycles')):
            raise ValueError('rank sources, schedule or input differ')
        records.append(rec)
        # Preserve RTL bits verbatim, including B padding already performed in RTL.
        (output/f'roots_r{rank}.mem').write_text(''.join(f'{int(a):08x}{int(b):08x}\n' for a,b in z['roots']))
        (output/f'rtl_logits_r{rank}.mem').write_text(''.join(f'{int(x):08x}\n' for x in z['logits']))
    provenance=dict(schema='opentallas.s81.native_head_field.collect.v1',rows=129280,
                    all_roots_produced_by_rtl=True,native_xf_chained=all(r['native_xf_chained'] for r in records),
                    full_native_token_qualified=False,source=records[0]['source'],xf_sha256=records[0]['xf_sha256'],
                    b_root_format=records[0]['b_root_format'],static_group_cycles=records[0]['static_group_cycles'],
                    rank_records=[dict(path=str(d/'record.json'),sha256=hashlib.sha256((d/'record.json').read_bytes()).hexdigest()) for d in dirs])
    (output/'field.provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    return provenance


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ranks',nargs=4,type=Path,required=True,metavar=('R0','R1','R2','R3'))
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();print(json.dumps(collect(a.ranks,a.output),indent=2))
if __name__=='__main__':main()
