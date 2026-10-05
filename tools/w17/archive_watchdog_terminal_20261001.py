#!/usr/bin/env python3
"""Commit lightweight terminal receipts without modifying live source or failed evidence."""
import pathlib,json,time,subprocess,hashlib,os
repo=pathlib.Path('/home/ubuntu/w17-stall-bounded')
root=repo/'results/rtl/w17_unchangedbinary_watchdog_20261001'
base=pathlib.Path('/home/ubuntu/w17-watchdog-unchanged-20261001-r1')
def archive(source,name,files):
 target=root/name;target.mkdir(exist_ok=False);paths=[]
 for f in files:
  p=source/f
  if not p.exists():continue
  dest=target/f;dest.write_bytes(p.read_bytes());paths.append(str(dest.relative_to(repo)))
 subprocess.run(['git','-C',str(repo),'add','--',*paths],check=True)
 subprocess.run(['git','-C',str(repo),'commit','-m','Capture source-bound W17 '+name+' terminal evidence'],check=True)
 commit=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
 with open('/tmp/claude-1000/queue/W17.manifest','a') as f:f.write('\n# W17 terminal evidence '+name+' committed '+commit+'; source '+str(source)+'; historical failure and live pins unchanged.\n')
while not(base/'analysis.json').exists():time.sleep(15)
archive(base,'diagnostic_terminal',['launch.json','terminal.json','analysis.json','run.log','progress.log'])
a=json.loads((base/'analysis.json').read_text())
if a['all_ranks_advanced_beyond_pc9']:
 source=pathlib.Path('/home/ubuntu/w17-fulltoken-unchanged-20261001-r1');files=['launch.json','terminal.json','analysis.json','run.log','progress.log'];name='fulltoken_terminal'
else:
 source=pathlib.Path('/home/ubuntu/w17-he-progress-20261001-r1');files=['launch.json','analysis.json','compile.log','trace.log','probe.cpp'];name='HE_probe_terminal'
while not(source/'analysis.json').exists():time.sleep(15)
archive(source,name,files)
