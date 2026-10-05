#!/usr/bin/env python3
"""Reuse completed finite SM binaries with one existing released W19 operand.

No TP96 execution, new inference, checkpoint rebuild or compile. Eight physical
columns replay the same existing AR input, not eight independent token positions.
"""
import argparse
import hashlib
import json
import pickle
from pathlib import Path
import subprocess
import sys

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root',type=Path,required=True)
    p.add_argument('--seeded-gate',type=Path,required=True)
    p.add_argument('--donor',type=Path,required=True)
    p.add_argument('--dump',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    sys.path.insert(0,str(a.source_root/'tools'))
    import numpy as np
    import rtl_gpu_sm_exact as S
    import w19_sm_real_ops as W
    import hdc_golden as G
    import hdc_golden_v41 as V
    seeded=json.loads((a.seeded_gate/'record.json').read_text())
    if seeded['status']!='PASS_FINITE_SEEDED_SM_ONLY':
        raise ValueError('completed same-source finite gate required')
    for name,digest in seeded['source_hashes'].items():
        if hashlib.sha256((a.source_root/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('native binary source changed: '+name)
    donor=json.loads((a.donor/'donor.json').read_text())
    raw=(a.donor/'gate_row0.bf16').read_bytes()
    dumped=a.dump.read_bytes()
    if (hashlib.sha256(raw).hexdigest()!=donor['raw_sha256'] or
        hashlib.sha256(dumped).hexdigest()!=donor['dump_sha256'] or
        donor['tensor']!='layers.0.ffn.gate.weight' or donor['row']!=0 or
        donor['dtype']!='BF16' or len(raw)!=10240):
        raise ValueError('actual released weight/old operand source differs')
    e=pickle.loads(dumped)[donor['entry']]
    if (e['w']!=donor['tensor'] or e['fmt']!='bf16' or
        e['fn']!='mv' or e['k']!=5120 or e['rows']!=[0,4]):
        raise ValueError('existing W19 source operation mismatch')
    if a.out.exists():raise ValueError('fresh real output preserves failures')
    a.out.mkdir(parents=True)
    V.set_arith('chunk8')
    w=(np.frombuffer(raw,dtype='<u2').astype(np.uint32)<<16).view(np.float32).reshape(1,5120)
    x=np.asarray(e['x'],dtype=np.float32)
    results=[]
    for enable in (0,1):
        executable=a.seeded_gate/f'build{enable}/sim.vvp'
        if not executable.is_file():raise ValueError('existing native binary absent')
        work=a.out/f'enable{enable}';work.mkdir()
        actual,golden,meta=W.smv_real('existing_L0_router_gate','v41_bf16',w,[x]*8,
            rmax=4096,workdir=str(work),
            sim_runner=lambda params,d:S.run_sim(executable,d,0))
        mismatch=sum(int(G.bits(v[0])!=G.bits(e['out'][0])) for v in actual)
        oracle_mismatch=sum(int(G.bits(actual[c][0])!=G.bits(golden[c][0])) for c in range(8))
        debt=(meta['accepted_requests']==meta['lines']==meta['returned_requests']==meta['consumed']
              and meta['released']==1 and meta['fault']==0 and meta['stalled_requests']>0)
        results.append(dict(enable=enable,cached_W19_mismatches=mismatch,
            scalar_oracle_mismatches=oracle_mismatch,finite_debt_closed=debt,
            rtl=meta,binary_sha256=hashlib.sha256(executable.read_bytes()).hexdigest()))
    ok=all(r['cached_W19_mismatches']==0 and r['scalar_oracle_mismatches']==0
           and r['finite_debt_closed'] for r in results)
    record=dict(status='PASS_EXISTING_REAL_OPERAND_SM_ONLY' if ok else 'FAIL',results=results,
        donor=donor,columns='same existing AR input replayed across8 physical columns',
        source_root=str(a.source_root),source_hashes=seeded['source_hashes'],
        helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        no_new_TP96_executor=True,physical_signoff=False,full_token=False)
    (a.out/'record.json').write_text(json.dumps(record,indent=2)+'\n')
    print(record['status'],flush=True)
    return 0 if ok else 1
if __name__=='__main__':raise SystemExit(main())
