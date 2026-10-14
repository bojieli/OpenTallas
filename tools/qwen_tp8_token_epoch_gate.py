#!/usr/bin/env python3
"""Build actual sole-epoch RTL plus independently observed fault mutants."""
import argparse,hashlib,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--rtl',type=Path,required=True);p.add_argument('--bench',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
a.out.mkdir(parents=True,exist_ok=False);original=a.rtl.read_text();records=[]
for mode in ('original','early_drain','warm_identity','fault_admit'):
    directory=a.out/mode;directory.mkdir();source=original
    if mode=='early_drain':source=source.replace('terminal_kv_drained && terminal_vm_drained &&','terminal_kv_drained || terminal_vm_drained ||',1)
    if mode=='warm_identity':source=source.replace('if (!por_n) begin','if (!por_n || !warm_ready) begin',1)
    if mode=='fault_admit':source=source.replace('&& !identity_fault && !busy','&& !busy',1)
    rtl=directory/a.rtl.name;rtl.write_text(source)
    cmd=['/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator','--cc','--exe','--build','-j','2','--top-module','ot_qwen_tp8_token_epoch_allocator','-GINITIAL_EPOCH=65534','-Wno-fatal','--Mdir',str(directory/'obj'),str(rtl),str(a.bench)]
    with (directory/'build.log').open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
    if r.returncode:raise SystemExit(r.returncode)
    result=subprocess.run([str(directory/'obj/Vot_qwen_tp8_token_epoch_allocator')],capture_output=True,text=True)
    (directory/'verdict.log').write_text(result.stdout+result.stderr)
    ok=result.returncode==(0 if mode=='original' else 1)
    records.append({'mode':mode,'exit':result.returncode,'expected_observed':ok,'rtl_sha256':hashlib.sha256(rtl.read_bytes()).hexdigest(),'output':result.stdout+result.stderr})
    print(mode,result.stdout+result.stderr,flush=True)
report={'scope':'actual component ownership/epoch/drain/reset protocol; caller real link reset/retraining bindings not yet composed',
        'source_sha256':hashlib.sha256(a.rtl.read_bytes()).hexdigest(),'bench_sha256':hashlib.sha256(a.bench.read_bytes()).hexdigest(),'records':records,'passed':all(r['expected_observed'] for r in records)}
(a.out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');raise SystemExit(0 if report['passed'] else 1)
