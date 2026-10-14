#!/usr/bin/env python3
"""Source-specific real native tile admission positives and observed mutants."""
import pathlib,json,os,subprocess,shutil,hashlib,concurrent.futures
out=pathlib.Path.cwd();m=json.loads((out/'provenance.json').read_text());src=out/'src';vlt=os.path.expanduser('~/.local/opentallas-tools/verilator-5.050/bin/verilator')
cases=[('positive',0,None),('query_level_mutant',1,'actual query ledger duplicate or stale event'),('query_version_mutant',2,'actual query ledger duplicate or stale event'),('partial_field_mutant',3,'partial real field accepted as whole-field acceptance')]
def run(case):
 name,mut,expected=case;s=src
 if mut==3:
  s=out/('src_'+name);shutil.copytree(src,s,dirs_exist_ok=True);f=s/'rtl/physical/ot_qwen_xdelivery_lifetime.sv';b=f.read_text();before='(accepted & participants)==participants';after='accepted[767]'
  if b.count(before)!=1:raise RuntimeError('nonunique mutation')
  f.write_text(b.replace(before,after));(out/(name+'_provenance.json')).write_text(json.dumps({'before':before,'after':after,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()},indent=2)+'\n')
 cmd=[vlt,'--binary','--timing','-j','3','-Wno-fatal','-Wno-lint','--top-module','tb_qwen_actual_query_ledger','--Mdir',str(out/('obj_'+name)),'-DXCACHE_TP8',f'-GMUT={mut}']+list(m['sources'])
 with(out/(name+'_build.log')).open('w')as log:subprocess.run(cmd,cwd=s,stdout=log,stderr=subprocess.STDOUT,check=True)
 r=subprocess.run([str(out/('obj_'+name)/'Vtb_qwen_actual_query_ledger')],cwd=s,capture_output=True,text=True);(out/(name+'.log')).write_text(r.stdout+r.stderr)
 if expected:
  if not r.returncode or expected not in r.stdout+r.stderr:raise RuntimeError(name+' escaped or wrong failure '+r.stdout+r.stderr)
  return 'PASS rejected '+name
 if r.returncode or 'PASS actualb646+f9 selected-tile query ledger'not in r.stdout:raise RuntimeError(r.stdout+r.stderr)
 return r.stdout
with concurrent.futures.ThreadPoolExecutor(max_workers=4)as p:
 for r in p.map(run,cases):print(r,flush=True)
print('PASS actual query ledger four gates',flush=True)
