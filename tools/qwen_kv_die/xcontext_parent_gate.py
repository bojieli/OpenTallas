#!/usr/bin/env python3
"""Run prepared immutable gate sources; invoke only within an ot-run admission."""
import json,pathlib,subprocess,os,shutil,concurrent.futures,hashlib,sys
out=pathlib.Path.cwd();manifest=json.loads((out/'provenance.json').read_text());src=out/'src'
vlt=os.path.expanduser('~/.local/opentallas-tools/verilator-5.050/bin/verilator')
cases=[('positive',0,0,None),('lost_go_mutant',1,0,'actual tile request/epoch mismatch'),('raw_split_diagnostic',0,1,None)]
def run(case):
 name,mut,allsp,expected=case;case_src=src
 cmd=[vlt,'--binary','--timing','-j','4','-Wno-fatal','-Wno-lint','--top-module','tb_qwen_xcontext_parent','--Mdir',str(out/('obj_'+name)),f'-GMUT={mut}',f'-GALL_SPLITS={allsp}','-DXCACHE_TP8']+list(manifest['sources'])
 if '--reuse-built' not in sys.argv:
  with (out/(name+'_build.log')).open('w') as log:subprocess.run(cmd,cwd=case_src,stdout=log,stderr=subprocess.STDOUT,check=True)
 r=subprocess.run([str(out/('obj_'+name)/'Vtb_qwen_xcontext_parent')],cwd=case_src,capture_output=True,text=True)
 (out/(name+'.log')).write_text(r.stdout+r.stderr)
 if expected is None:
  if r.returncode or 'PASS actual cached parent heldGO' not in r.stdout:raise RuntimeError(r.stdout+r.stderr)
  return r.stdout
 if r.returncode==0 or expected not in r.stdout+r.stderr:raise RuntimeError('mutant escaped/mismatched: '+name+' '+r.stdout+r.stderr)
 return 'PASS rejected '+name
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 for result in pool.map(run,cases):print(result,flush=True)
print('PASS actualparent heldGO three gates',flush=True)
