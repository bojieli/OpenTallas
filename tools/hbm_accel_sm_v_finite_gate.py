#!/usr/bin/env python3
"""One source-sized seeded SM gate with finite request and barrier admission."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
os.environ.setdefault('HDC_V41_ARITH','chunk8')
import rtl_gpu_sm_exact as S
import hbm_accel_sm_v_gate as G
from uarch_model_hbm_sm_v import source_cost

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--floorplan',type=Path,required=True)
    p.add_argument('--existing-shape-gate',type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise ValueError('fresh output preserves prior failures')
    a.out.mkdir(parents=True)
    gate=json.loads(a.existing_shape_gate.read_text())
    if gate['status']!='pass':
        raise ValueError('actual existing source-sized successor evidence required')
    sources=[s for s in G.SRC if s!='rtl/test/tb_hbm_accel_sm_v.sv']
    sources+=['rtl/test/tb_hbm_accel_sm_v_finite.sv']
    for name,digest in gate['source_sha256'].items():
        if name in sources and hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('existing shape evidence source differs: '+name)
    drains={c['successor']['rtl']['drain_last_line_to_last_result']-
            c['original']['rtl']['drain_last_line_to_last_result'] for c in gate['results']}
    if drains!={12}:raise ValueError('actual source drain delta differs')
    model=source_cost(json.loads(a.floorplan.read_text()),measured_added_drain_cycles=12,
                      measured_added_done_cycles=gate['delta_done_set'])
    (a.out/'model.json').write_text(json.dumps(model,indent=2)+'\n')
    parameters=dict(SUB=4,LBS=2,LSB=16,NC=8,XDEPTH=128,RMAX=4096,LEV=4)
    results=[]
    # Compile minimum controller+real SM leaf configuration twice for reference
    # comparison, sequentially. No TP96 executor, checkpoint or inference.
    for enable in (0,1):
        build=a.out/f'build{enable}';build.mkdir()
        exe=S.compile_tb(sources,'tb_hbm_accel_sm_v_finite',
                         dict(parameters,ENABLE=enable),build)
        key=('v',)+tuple(sorted(parameters.items()))
        result=S.smv_case('finite_bf16', 'v41_bf16',3,1004,8,
            rng=np.random.default_rng(20261005),gs=True,rmax=4096,
            workdir=str(a.out),exe_cache={key:exe})
        results.append(result)
    ok=all(r['exact'] and r['rtl']['accepted_requests']==r['weight_lines'] and
           r['rtl']['returned_requests']==r['weight_lines'] and
           r['rtl']['consumed']==r['weight_lines'] and
           r['rtl']['stalled_requests']>0 and r['rtl']['released']==1 for r in results)
    record=dict(status='PASS_FINITE_SEEDED_SM_ONLY' if ok else 'FAIL',
        results=results,source_hashes={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest()
                                      for n in sources},
        model=model,real_checkpoint_gate=False,physical_signoff=False)
    (a.out/'record.json').write_text(json.dumps(record,indent=2)+'\n')
    print(record['status'],flush=True)
    return 0 if ok else 1
if __name__=='__main__':raise SystemExit(main())
