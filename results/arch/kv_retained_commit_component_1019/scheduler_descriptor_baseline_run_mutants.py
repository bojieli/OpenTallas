#!/usr/bin/env python3
"""Causal fault mutations; immutable individual build/run logs, nonzero plus expected witness required."""
from pathlib import Path
import subprocess,os,re,json
os.chdir(Path(__file__).resolve().parent)
s=Path('private/ot_host_if_pb2_observed_rc.sv').read_text()
v=str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator')
assert 'Verilator 5.050' in subprocess.check_output([v,'--version'],text=True)
variants=[
 ('word0',4,'SCHED_WORD0_FAULT',r'wire word0_cut_ok = .*?;', 'wire word0_cut_ok = 1\'b1;'),
 ('deadline',5,'SCHED_DEADLINE',r'wire deadline_bad = .*?;', 'wire deadline_bad = 1\'b0;'),
 ('rawdone',1,'SCHED_RAWDONE_CLEANUP',r'wire\s+step_done = (.*?);',r'wire step_done = !bad_q && (\1);'),
 ('identity',7,'SCHED_IDENTITY_REFUSAL',r'wire identity_bad = .*?;', 'wire identity_bad = 1\'b0;'),
 ('counters',4,'SCHED_FAULT_COUNTERS',r'ENABLE_RETAINED_COMMIT && offered_success_q && m_bresp == 0\)\) c_tokens', 'ENABLE_RETAINED_COMMIT && eh_kind != EV_ERROR)) c_tokens'),
 ('warm',2,'SCHED_RETAIN_WARM',r'wire loss_now = .*?;', 'wire loss_now = 1\'b0;'),
]
requested=os.environ.get('ONLY_MUTANTS','').split(',') if os.environ.get('ONLY_MUTANTS') else []
receipt=json.loads(Path('scheduler_descriptor_baseline_run_mutants.json').read_text()) if requested and Path('scheduler_descriptor_baseline_run_mutants.json').exists() else []
for name,case,witness,pat,repl in variants:
 if requested and name not in requested:continue
 mutant,n=re.subn(pat,repl,s,count=1,flags=re.S);assert n==1,name
 d=Path('scheduler_descriptor_baseline_run_mutant_'+name);d.mkdir(exist_ok=True)
 f=d/'source.sv';f.write_text(mutant)
 with (d/'build.log').open('w') as log:
  rc=subprocess.call([v,'--binary','--timing','-Wno-fatal','--top-module','scheduler_descriptor_baseline','--Mdir',str(d/'obj'),'-j','8','scheduler_descriptor_baseline.sv',str(f)],stdout=log,stderr=subprocess.STDOUT)
 assert rc==0,(name,'BUILDFAIL')
 with (d/'fail.log').open('w') as log:rc=subprocess.call([str(d/'obj/Vscheduler_descriptor_baseline'),f'+CASE={case}'],stdout=log,stderr=subprocess.STDOUT)
 text=(d/'fail.log').read_text();caught=rc!=0 and witness in text
 receipt.append(dict(name=name,case=case,exit=rc,fail_regex=witness,caught=caught))
 Path('scheduler_descriptor_baseline_run_mutants.json').write_text(json.dumps(receipt,indent=2)+'\n')
 assert caught,(name,'MUTANT_NOT_CAUGHT',rc)
