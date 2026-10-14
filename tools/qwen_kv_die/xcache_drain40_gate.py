#!/usr/bin/env python3
"""Actual request-mode counterexample and default-off repair; ot-run only."""
import concurrent.futures,json,os,pathlib,subprocess,shutil,hashlib
out=pathlib.Path.cwd();m=json.loads((out/'provenance.json').read_text());src=out/'src'
vlt=os.path.expanduser('~/.local/opentallas-tools/verilator-5.050/bin/verilator')
cases=[('repair',0,0,None),('raw_split_repair',0,1,None),('drain_early_mutant',4,0,'actual arithmetic drain identity/timing mismatch'),('drain_identity_mutant',4,0,'actual arithmetic drain identity/timing mismatch')]
def run(case):
 name,mut,allsp,expected=case;case_src=src
 if name.startswith('drain_'):
  case_src=out/('src_'+name);shutil.copytree(src,case_src,dirs_exist_ok=True)
  f=case_src/'rtl/physical/ot_qwen_tile_local_drain.sv';b=f.read_text();before="remaining[selected]<=6'd48;"if name=='drain_early_mutant'else'identities[selected]<={issue_context,issue_version};';after="remaining[selected]<=6'd47;"if name=='drain_early_mutant'else"identities[selected]<={16'd0,issue_version};"
  if b.count(before)!=1:raise RuntimeError('source mutation nonunique')
  f.write_text(b.replace(before,after));(out/(name+'_provenance.json')).write_text(json.dumps({'before':before,'after':after,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()},indent=2)+'\n')
 cmd=[vlt,'--binary','--timing','-j','3','-Wno-fatal','-Wno-lint','--top-module','tb_qwen_xcache_drain40','--Mdir',str(out/('obj_'+name)),f'-GMUT={mut}',f'-GALL_SPLITS={allsp}','-DXCACHE_TP8']+list(m['sources'])
 with (out/(name+'_build.log')).open('w')as log:subprocess.run(cmd,cwd=case_src,stdout=log,stderr=subprocess.STDOUT,check=True)
 r=subprocess.run([str(out/('obj_'+name)/'Vtb_qwen_xcache_drain40')],cwd=case_src,capture_output=True,text=True);(out/(name+'.log')).write_text(r.stdout+r.stderr)
 if expected:
  if r.returncode==0 or expected not in r.stdout+r.stderr:raise RuntimeError(name+' escaped or mismatched: '+r.stdout+r.stderr)
  return 'PASS reproduced/refused '+name
 if r.returncode or 'PASS production acceptedIB and request ports'not in r.stdout:raise RuntimeError(r.stdout+r.stderr)
 return r.stdout
with concurrent.futures.ThreadPoolExecutor(max_workers=4)as p:
 for r in p.map(run,cases):print(r,flush=True)
print('PASS actual numeric drain40 four gates',flush=True)
