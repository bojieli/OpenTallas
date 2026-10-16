#!/usr/bin/env python3
"""Run through ot-run,48GB/16threads; source/fixtures must already be snapshotted."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--mut',type=int,choices=[0,24],required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();R=Path.cwd();O=a.out.resolve();O.mkdir(parents=True,exist_ok=True)
manifest=json.loads((R/'source_manifest.json').read_text());assert all(hashlib.sha256((R/s).read_bytes()).hexdigest()==h for s,h in manifest['source_sha256'].items())
fixtures=R/'fixtures';assert all(hashlib.sha256((fixtures/s).read_bytes()).hexdigest()==h for s,h in manifest['fixture_sha256'].items())
top='tb_s81_engram_mix4_localized';obj=O/'obj';tool=Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
cmd=[str(tool),'--binary','--timing','-O2','-Wno-fatal','--top-module',top,'--output-split','20000','--output-split-cfuncs','2000','-Mdir',str(obj),'-j','16',f'-GMUT={a.mut}',*[str(R/s)for s in manifest['source_sha256']],'-CFLAGS','-O1']
receipt={**manifest,'mutant':a.mut,'command':cmd,'status':'COMPILING','scope':'Actual full4x5120 all-FP-RTL component at declared external VM boundary; native VM/physical parent remain OPEN'}
(O/'receipt.json').write_text(json.dumps(receipt,indent=1)+'\n')
with(O/'build.log').open('w')as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
receipt['build_returncode']=r.returncode
if r.returncode:receipt['status']='BUILD_FAILED_NOT_MUTANT_REJECTION'
else:
 with(O/'run.log').open('w')as f:r=subprocess.run([str(obj/('V'+top)),'+dir='+str(fixtures)],stdout=f,stderr=subprocess.STDOUT)
 log=(O/'run.log').read_text();receipt['run_returncode']=r.returncode
 if a.mut==0:
  expected='PASS native Engram MIX4 full4x5120 in-place20480words done tag53 writes640 reads4161 write_span639..798 cycles=810'
  receipt['status']='ACTUAL_FULL_SHAPE_COMPONENT_PASS'if r.returncode==0 and expected in log else'NUMERICAL_OR_CALENDAR_FAIL'
 else:receipt['status']='ACTUAL_STOPPED_NEW_INGRESS_CLOCK_REJECTED'if r.returncode!=0 and ('timeout' in log or ('endpoint fault cyc=28 cluster_faults=0000 ep=0 top=1' in log)) else'MUTANT_NOT_REJECTED_OR_UNCLASSIFIED'
 print(log,flush=True)
(O/'receipt.json').write_text(json.dumps(receipt,indent=1)+'\n');print(receipt['status'],flush=True)
raise SystemExit(0 if receipt['status'] in ('ACTUAL_FULL_SHAPE_COMPONENT_PASS','ACTUAL_STOPPED_NEW_INGRESS_CLOCK_REJECTED')else 1)
