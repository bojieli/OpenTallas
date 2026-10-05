#!/usr/bin/env python3
"""Short local gate: storage exactness and source/model/structural checks ONLY."""
import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists(): raise SystemExit('immutable receipt exists; select a fresh output')
    provider=['rtl/gpu/ot_gpu_rf_service.sv','rtl/gpu/ot_gpu_scratch_service.sv','rtl/gpu/ot_gpu_full_sm_service.sv']
    test='rtl/test/full_sm_service/'
    records=[]
    with tempfile.TemporaryDirectory(prefix='full-sm-rf-short-') as tmp:
        cases=[('model_source_contract',['python3','tools/test_full_sm_rf_service.py']),
               ('storage_compile',['iverilog','-g2012','-s','tb_storage','-o',tmp+'/storage.vvp',*provider[:2],test+'sram_models.sv',test+'tb_storage.sv']),
               ('storage_exact',['vvp',tmp+'/storage.vvp']),
               ('enabled_structural_blackboxes_ONLY',['iverilog','-g2012','-s','tb_full_service_exact','-o',tmp+'/structural.vvp',*provider,test+'sram_models.sv',test+'arithmetic_blackboxes.sv',test+'tb_full_service_exact.sv']),
               ('disabled_elaboration_no_primitives',['iverilog','-g2012','-s','ot_gpu_full_sm_service','-o',tmp+'/disabled.vvp',provider[2]]),
               ('parent_recipe_shell_syntax',['bash','-n','tools/full_sm_rf_service_exact_gate.sh'])]
        for name,cmd in cases:
            try:
                r=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=30)
                records.append(dict(name=name,command=[v.replace(tmp,'$TMP') for v in cmd],exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr))
            except subprocess.TimeoutExpired:
                records.append(dict(name=name,exit_code=124,timeout=True))
                break
            if r.returncode:break
    paths=provider+[test+x for x in ('sram_models.sv','tb_storage.sv','arithmetic_blackboxes.sv','tb_full_service_exact.sv')]+['tools/uarch_model.py','tools/uarch_full_sm_service.py','tools/test_full_sm_rf_service.py','tools/check_full_sm_rf_service.py','tools/full_sm_rf_service_exact_gate.sh']
    result=dict(schema='opentallas.full-sm-service.short-check.v1',base_intake='5250fe00a',
                verdict='PASS' if len(records)==len(cases) and all(x['exit_code']==0 for x in records) else 'FAIL',checks=records,
                source_sha256={x:hashlib.sha256((ROOT/x).read_bytes()).hexdigest() for x in paths},
                full128_SIMD_arithmetic_exact_gate='NOT_RUN_PARENT_REVIEW_REQUIRED',SS_FF='NOT_RUN',
                hub_routing_layer_gate='PENDING_COMPOSED_PARENT; local GPU-only source check is not routing PASS',
                actual_matrix_source_join='PENDING_MAXWELL',build_GO=False,hardware_adoption=False,
                new_jobs_PVE2_PVE3=0,remote_launches=0,heavy_compiles=0,live_jobs_touched=False)
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:result[k] for k in ('verdict','full128_SIMD_arithmetic_exact_gate','build_GO')}))
    if result['verdict']!='PASS':raise SystemExit(1)
if __name__=='__main__':main()
