#!/usr/bin/env python3
"""Run prepared immutable gate sources; invoke only within an ot-run admission."""
import json,pathlib,subprocess,os,shutil,concurrent.futures,hashlib
out=pathlib.Path.cwd();manifest=json.loads((out/'provenance.json').read_text());src=out/'src'
vlt=os.path.expanduser('~/.local/opentallas-tools/verilator-5.050/bin/verilator')
cases=[('positive',False,None),('raw_split_diagnostic',True,None),('cache_row_mutant',False,'actual CEXT2 arithmetic mismatch'),('parent_word_order_mutant',False,'actual CEXT2 arithmetic mismatch')]
def run(case):
 name,allsp,expected=case;case_src=src
 if expected:
  case_src=out/('src_'+name);shutil.copytree(src,case_src,dirs_exist_ok=True)
  f=case_src/('rtl/physical/ot_qwen_xcache_indexed.sv' if name=='cache_row_mutant' else 'rtl/physical/ot_qwen_tile_tp8_cached.sv')
  text=f.read_text()
  before,after=('parameter integer MUT_ROW=0','parameter integer MUT_ROW=1') if name=='cache_row_mutant' else ('.x_response(x_response)','.x_response({x_response[95:0],x_response[127:96]})')
  if text.count(before)!=1:raise RuntimeError('mutation source not unique')
  f.write_text(text.replace(before,after))
  (out/(name+'_provenance.json')).write_text(json.dumps({'mutation':name,'before':before,'after':after,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()},indent=2)+'\n')
 cmd=[vlt,'--binary','--timing','-j','4','-Wno-fatal','-Wno-lint','--top-module','tb_qwen_xcache_parent','--Mdir',str(out/('obj_'+name)),f'-GALL_SPLITS={int(allsp)}','-DXCACHE_TP8']+list(manifest['sources'])
 with (out/(name+'_build.log')).open('w') as log:subprocess.run(cmd,cwd=case_src,stdout=log,stderr=subprocess.STDOUT,check=True)
 r=subprocess.run([str(out/('obj_'+name)/'Vtb_qwen_xcache_parent')],cwd=case_src,capture_output=True,text=True)
 (out/(name+'.log')).write_text(r.stdout+r.stderr)
 if expected is None:
  if r.returncode or 'PASS actual cached parent' not in r.stdout:raise RuntimeError(r.stdout+r.stderr)
  return r.stdout
 if r.returncode==0 or expected not in r.stdout+r.stderr:raise RuntimeError('mutant escaped/mismatched: '+name+' '+r.stdout+r.stderr)
 return 'PASS rejected '+name
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 for result in pool.map(run,cases):print(result,flush=True)
print('PASS realcachedparent all four gates',flush=True)
