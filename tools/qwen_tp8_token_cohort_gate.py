#!/usr/bin/env python3
"""Remote-only source-exact cohort gate and observed fault-removal mutants."""
import argparse,hashlib,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--rtl',type=Path,required=True);p.add_argument('--bench',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
a.out.mkdir(parents=True,exist_ok=False);original=a.rtl.read_text();records=[]
for mode in ('original','early_rank','tag_guard','drain_guard','warm_identity'):
 d=a.out/mode;d.mkdir();source=original
 if mode=='early_rank':source=source.replace('(&accepted_ranks)','(&accepted_ranks[6:0])',1)
 if mode=='tag_guard':source=source.replace('request_tag[59*r +: 59] != cohort_tag','1\'b0',1)
 if mode=='drain_guard':source=source.replace('kv_drained && vm_drained && collective_drained && host_drained','kv_drained && vm_drained && collective_drained',1)
 if mode=='warm_identity':source=source.replace('if (!por_n) begin','if (!por_n || !warm_ready) begin',1)
 rtl=d/a.rtl.name;rtl.write_text(source)
 cmd=['/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator','--cc','--exe','--build','-j','2','--top-module','ot_qwen_tp8_token_cohort','-Wno-fatal','--Mdir',str(d/'obj'),str(rtl),str(a.bench)]
 with (d/'build.log').open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
 if r.returncode:raise SystemExit(r.returncode)
 r=subprocess.run([str(d/'obj/Vot_qwen_tp8_token_cohort')],capture_output=True,text=True)
 (d/'verdict.log').write_text(r.stdout+r.stderr);ok=r.returncode==(0 if mode=='original' else 1)
 records.append({'mode':mode,'exit':r.returncode,'expected_observed':ok,'rtl_sha256':hashlib.sha256(rtl.read_bytes()).hexdigest(),'output':r.stdout+r.stderr});print(mode,r.stdout+r.stderr,flush=True)
report={'scope':'actual standalone admission barrier; genuine HOST endpoint/link bindings and full-token numerical execution pending','source_sha256':hashlib.sha256(a.rtl.read_bytes()).hexdigest(),'bench_sha256':hashlib.sha256(a.bench.read_bytes()).hexdigest(),'records':records,'passed':all(x['expected_observed'] for x in records)}
(a.out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');raise SystemExit(0 if report['passed'] else 1)
