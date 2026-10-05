#!/usr/bin/env python3
"""Fail-closed matched checkpoint comparison for the V4.1 ME preload path."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/rtl/hdc_v41x_fullshape_woa_shared_rl3_full1024.json'
WIDE=ROOT/'results/rtl/hdc_v41x_fullshape_woa_preloaded_rl3_full1024.json'
OUT=ROOT/'results/rtl/hdc_v41x_fullshape_woa_preload_matched.json'

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    a,b=(json.loads(p.read_text()) for p in (BASE,WIDE))
    if not (a['status']==b['status']=='pass' and
            a['exact_rows']==b['exact_rows']==2048 and
            a['rows_per_group']==b['rows_per_group']==1024 and
            a['source_sha256']==b['source_sha256'] and
            a['fixture_sha256']==b['fixture_sha256'] and
            a['bank_read_cycles']==b['bank_read_cycles']==131108 and
            a['read_latency_cycles']==b['read_latency_cycles']==3 and
            a['external_shared_store']==b['external_shared_store']==True and
            a['preloaded_activation'] is False and b['preloaded_activation'] is True and
            b['vm_bank_rotation_quarters']==2 and
            b['preload_issue_cycles']==b['preload_write_cycles']==128):
        raise ValueError('arms are not same-source, exact, and contract matched')
    for f,h in a['source_sha256'].items():
        if sha(ROOT/f)!=h: raise ValueError(f'stale source pin: {f}')
    delta=a['simulation_cycles']-b['simulation_cycles']
    rec=dict(schema='opentallas.rtl.v41x_fullshape_woa_preload_matched.v1',status='pass',
             claim_scope='TP4 rank0 layer0 wo_a two K4096 groups, 2048 exact FP32 rows; standalone shared ME bench, no VM controller, cluster or chip-rate claim',
             cycles_g4=a['simulation_cycles'],cycles_wide=b['simulation_cycles'],
             cycles_saved=delta,relative_cycle_reduction=round(delta/a['simulation_cycles'],8),
             exact_rows=2048,weight_bank_reads=a['bank_read_cycles'],
             wide_preload_issue_cycles=b['preload_issue_cycles'],
             wide_preload_write_cycles=b['preload_write_cycles'],
             vm_bank_rotation_quarters=2,
             arm_sha256={str(p.relative_to(ROOT)):sha(p) for p in (BASE,WIDE)},
             source_sha256={str(Path(__file__).relative_to(ROOT)):sha(Path(__file__))})
    OUT.write_text(json.dumps(rec,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:rec[k] for k in ('status','cycles_g4','cycles_wide','cycles_saved','relative_cycle_reduction')}))

if __name__=='__main__': main()
