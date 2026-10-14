#!/usr/bin/env python3
"""Recompile unchanged generated HOST C++ with O1; no RTL/model regeneration."""
import argparse,hashlib,json,shutil,subprocess,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--jobs',type=int,default=4);a=p.parse_args()
top='Vqkd_host_token_service'
pins={str(f.relative_to(a.source)):hashlib.sha256(f.read_bytes()).hexdigest() for f in a.source.iterdir() if f.suffix in ('.cpp','.h','.mk')}
shutil.copytree(a.source,a.out,ignore=shutil.ignore_patterns('*.o','*.a','*.d','*.gch','*.pch'))
cmd=['make','-C',str(a.out),'-f',top+'.mk','-j',str(a.jobs),'VM_USER_CFLAGS=-O1','OPT_FAST=-O1','OPT_SLOW=-O1']
t=time.monotonic()
with (a.out/'recompile.log').open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
after={str(f.relative_to(a.out)):hashlib.sha256(f.read_bytes()).hexdigest() for f in a.out.iterdir() if f.suffix in ('.cpp','.h','.mk')}
if pins!=after:raise SystemExit('generated source changed during C++ rebuild')
archive=a.out/(top+'__ALL.a')
record={'scope':'SIMULATOR_COMPILER_OPTIMIZATION_ONLY_NO_ASIC_RATE_OR_RTL_CHANGE','command':cmd,'exit':r.returncode,'seconds':time.monotonic()-t,'generated_source_sha256':pins,'source_unchanged':True,'artifact_sha256':hashlib.sha256(archive.read_bytes()).hexdigest() if archive.exists() else None,'functional_behavior_gate_required':True}
(a.out/'optimized_receipt.json').write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(r.returncode)
