#!/usr/bin/env python3
"""Run prepared context candidate under an ot-run admission, no physical claim."""
import concurrent.futures,json,os,pathlib,subprocess
out=pathlib.Path.cwd();m=json.loads((out/'provenance.json').read_text())
vlt=os.path.expanduser('~/.local/opentallas-tools/verilator-5.050/bin/verilator')
def run(case):
 name,mut,expected=case
 top='tb_qwen_xcontext_wrap' if name.startswith('wrap') else 'tb_qwen_xcontext_protocol'
 cmd=[vlt,'--binary','--timing','-j','1','-Wno-fatal','-Wno-lint','--top-module',top,'--Mdir',str(out/('obj_'+name)),f'-GMUT={mut}']+list(m['sources'])
 with (out/(name+'_build.log')).open('w') as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
 r=subprocess.run([str(out/('obj_'+name)/('V'+top))],capture_output=True,text=True)
 (out/(name+'.log')).write_text(r.stdout+r.stderr)
 if expected:
  if r.returncode==0 or expected not in r.stdout+r.stderr:raise RuntimeError('mutant escaped '+name+' '+r.stdout+r.stderr)
  return 'PASS rejected '+name
 if r.returncode or 'PASS ' not in r.stdout:raise RuntimeError(r.stdout+r.stderr)
 return r.stdout
cases=[('wrap_positive',0,None),('wrap_reuse_mutant',1,'live token reused after16bit wrap'),('positive',0,None),('stale_context_mutant',1,'stale context/full key'),('duplicate_fire_mutant',2,'duplicate fill accepted'),('lost_go_mutant',3,'GO lost during core pause')]
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as p:
 for result in p.map(run,cases):print(result,flush=True)
print('PASS dictionary protocol six gates',flush=True)
