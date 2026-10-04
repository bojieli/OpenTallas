#!/usr/bin/env python3
"""Connected command/SM token17 gate, no model inference or arbitrary caps."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

from tools.gpu_sys import run_system as S


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--enable-ds-cluster17',action='store_true',required=True)
    ap.add_argument('--work',type=Path,required=True)
    a=ap.parse_args();a.work.mkdir(parents=True,exist_ok=False)
    root=S.ROOT
    extra=['rtl/gpu_sys/ds_hbm17/ot_ds_hbm_cmdproc17.sv',
           'rtl/gpu_sys/ds_hbm17/ot_ds_hbm_simt_sm17.sv',
           'rtl/gpu_sys/ds_hbm17/ot_ds_hbm_cluster17.sv',
           'rtl/test/gpu_sys/tb_ds_hbm_cluster17.sv']
    src=S.SYS_SRC+S.DEP_SRC+extra
    hashes={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in src}
    obj=a.work/'obj'
    cmd=[str(S.VERILATOR),'--binary','--timing','-O2','-j','4',
         '-Wno-fatal','-Wno-lint','-Wno-style','-Wno-WIDTH',
         '--x-assign','0','--x-initial','0','--top-module','tb_ds_hbm_cluster17',
         '--Mdir',str(obj)]+[str(root/p) for p in src]
    start=time.monotonic()
    with (a.work/'build.log').open('w') as f:
        built=subprocess.run(cmd,cwd=root,stdout=f,stderr=subprocess.STDOUT)
    runtime=None;ok=False
    if built.returncode==0:
        with (a.work/'run.log').open('w') as f:
            runtime=subprocess.run([str(obj/'Vtb_ds_hbm_cluster17'),'+gpu_sys_mem_prefix='],cwd=a.work,stdout=f,stderr=subprocess.STDOUT)
        ok=runtime.returncode==0 and 'PASS_CONNECTED_COMMAND_SM_TOKEN17' in (a.work/'run.log').read_text()
    record=dict(schema='opentallas.ds_hbm.connected_token17.v1',
        verdict='PASS_WIDTH_ONLY' if ok else 'FAIL_WIDTH_ONLY',
        compile_rc=built.returncode,runtime_rc=None if runtime is None else runtime.returncode,
        full_token_qualified=False,scope='actual command processor/SM17 RESULT roundtrip only',
        source_sha256=hashes,elapsed_seconds=time.monotonic()-start,
        clock_ps=dict(sm=833,mem=1000,link=900,host=4000))
    (a.work/'result.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record),flush=True)
    return 0 if ok else 1


if __name__=='__main__':raise SystemExit(main())
