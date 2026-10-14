#!/usr/bin/env python3
"""Actual request-mode counterexample and default-off repair; ot-run only."""
import concurrent.futures,json,os,pathlib,subprocess
out=pathlib.Path.cwd();m=json.loads((out/'provenance.json').read_text());src=out/'src'
vlt=os.path.expanduser('~/.local/opentallas-tools/verilator-5.050/bin/verilator')
cases=[('repair',0,0,None),('original_live_mode_failure',1,0,'actual CEXT2 arithmetic mismatch'),('live_mode_mutant',2,0,'live mode lost old pending request'),('resident_version_mutant',3,0,'resident context/version reused'),('raw_split_repair',0,1,None)]
def run(case):
 name,mut,allsp,expected=case
 cmd=[vlt,'--binary','--timing','-j','3','-Wno-fatal','-Wno-lint','--top-module','tb_qwen_xcache_mode_parent','--Mdir',str(out/('obj_'+name)),f'-GMUT={mut}',f'-GALL_SPLITS={allsp}','-DXCACHE_TP8']+list(m['sources'])
 with (out/(name+'_build.log')).open('w')as log:subprocess.run(cmd,cwd=src,stdout=log,stderr=subprocess.STDOUT,check=True)
 r=subprocess.run([str(out/('obj_'+name)/'Vtb_qwen_xcache_mode_parent')],cwd=src,capture_output=True,text=True);(out/(name+'.log')).write_text(r.stdout+r.stderr)
 if expected:
  if r.returncode==0 or expected not in r.stdout+r.stderr:raise RuntimeError(name+' escaped or mismatched: '+r.stdout+r.stderr)
  return 'PASS reproduced/refused '+name
 if r.returncode or 'PASS actual request-mode parent'not in r.stdout:raise RuntimeError(r.stdout+r.stderr)
 return r.stdout
with concurrent.futures.ThreadPoolExecutor(max_workers=5)as p:
 for r in p.map(run,cases):print(r,flush=True)
print('PASS request mode five gates',flush=True)
