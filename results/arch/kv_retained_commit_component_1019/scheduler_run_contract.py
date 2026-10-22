#!/usr/bin/env python3
from pathlib import Path
import subprocess,os,json
os.chdir(Path(__file__).resolve().parent)
v=str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator')
r=[]
for c in range(4):
 d=Path('scheduler_run_contract_'+str(c));d.mkdir(exist_ok=True)
 with (d/'build.log').open('w') as log:
  rc=subprocess.call([v,'--binary','--timing','-Wno-fatal','--top-module','scheduler_bench_contract',f'-GC={c}','--Mdir',str(d/'obj'),'-j','8','scheduler_bench_contract.sv','private/ot_host_if_pb2_observed_rc.sv'],stdout=log,stderr=subprocess.STDOUT)
 assert rc==0,(c,'BUILDFAIL')
 with (d/'fail.log').open('w') as log:rc=subprocess.call([str(d/'obj/Vscheduler_bench_contract')],stdout=log,stderr=subprocess.STDOUT)
 caught=rc!=0 and 'RC_COMPONENT_CONTRACT' in (d/'fail.log').read_text()
 r.append(dict(case=c,exit=rc,caught=caught,fail_regex='RC_COMPONENT_CONTRACT'))
 Path('scheduler_run_contract.json').write_text(json.dumps(r,indent=2)+'\n')
 assert caught,(c,'CONTRACT_NOT_REFUSED')
