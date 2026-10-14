#!/usr/bin/env python3
"""Source-specific real native tile admission positives and observed mutants."""
import pathlib,json,os,subprocess,shutil,hashlib,concurrent.futures
out=pathlib.Path.cwd();m=json.loads((out/'provenance.json').read_text());src=out/'src';vlt=os.path.expanduser('~/.local/opentallas-tools/verilator-5.050/bin/verilator')
cases=[('positive',None,None),('pending_mutant','&&!pending','unacknowledged offer accepted'),('duplicate_mutant','&&!duplicate','held GO duplicate accepted'),('bypass_mutant','offer_go&&core_ready&&!pending&&!duplicate&&!transport_fence','unacknowledged offer accepted')]
def run(case):
 name,remove,expected=case;s=src
 if remove:
  s=out/('src_'+name);shutil.copytree(src,s,dirs_exist_ok=True);f=s/'rtl/physical/ot_qwen_context_admission.sv';b=f.read_text()
  if b.count(remove)!=1:raise RuntimeError('nonunique mutation')
  f.write_text(b.replace(remove,'offer_go&&core_ready'if name=='bypass_mutant'else''));(out/(name+'_provenance.json')).write_text(json.dumps({'remove':remove,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()},indent=2)+'\n')
 cmd=[vlt,'--binary','--timing','-j','3','-Wno-fatal','-Wno-lint','--top-module','tb_qwen_actual_admission','--Mdir',str(out/('obj_'+name)),'-DXCACHE_TP8']+list(m['sources'])
 with(out/(name+'_build.log')).open('w')as log:subprocess.run(cmd,cwd=s,stdout=log,stderr=subprocess.STDOUT,check=True)
 r=subprocess.run([str(out/('obj_'+name)/'Vtb_qwen_actual_admission')],cwd=s,capture_output=True,text=True);(out/(name+'.log')).write_text(r.stdout+r.stderr)
 if expected:
  if not r.returncode or expected not in r.stdout+r.stderr:raise RuntimeError(name+' escaped or wrong failure '+r.stdout+r.stderr)
  return 'PASS rejected '+name
 if r.returncode or 'PASS actual709 admission'not in r.stdout:raise RuntimeError(r.stdout+r.stderr)
 return r.stdout
with concurrent.futures.ThreadPoolExecutor(max_workers=4)as p:
 for r in p.map(run,cases):print(r,flush=True)
print('PASS actual production admission four gates',flush=True)
