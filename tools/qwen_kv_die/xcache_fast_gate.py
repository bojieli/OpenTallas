#!/usr/bin/env python3
"""Run prepared immutable gate sources; invoke only within an ot-run admission."""
import json,pathlib,subprocess,os,shutil,concurrent.futures,hashlib
out=pathlib.Path.cwd();manifest=json.loads((out/'provenance.json').read_text());src=out/'src'
vlt=os.path.expanduser('~/.local/opentallas-tools/verilator-5.050/bin/verilator')
cases=[('positive',0,0,None),('row_mutant',1,0,'actual CEXT2 arithmetic mismatch'),('extra_XL_edge_mutant',2,0,'actual CEXT2 arithmetic mismatch'),('raw_split_diagnostic',0,1,None),('split_mask_mutant',0,1,'actual tile request/epoch mismatch'),('stride16_mutant',0,1,'actual tile request/epoch mismatch')]
def run(case):
 name,mut,allsp,expected=case;case_src=src
 if name in ('split_mask_mutant','stride16_mutant'):
  case_src=out/('src_'+name);shutil.copytree(src,case_src,dirs_exist_ok=True)
  f=case_src/'rtl/hdc/ot_qwen_w12_matvec.sv';text=f.read_text()
  mask_before='i_split > xab' if 'i_split > xab' in text else 'split_r > xab'
  before,after=(mask_before,mask_before.replace(' > ',' >= ')) if name=='split_mask_mutant' else ('(xcs_r << xab)','((xcs_r & 24\'h00FFFF) << xab)')
  if text.count(before)!=1:raise RuntimeError('mutation source not unique')
  f.write_text(text.replace(before,after))
  (out/(name+'_provenance.json')).write_text(json.dumps({'mutation':name,'before':before,'after':after,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()},indent=2)+'\n')
 cmd=[vlt,'--binary','--timing','-j','4','-Wno-fatal','-Wno-lint','--top-module','tb_qwen_xcache_actual_tile','--Mdir',str(out/('obj_'+name)),f'-GMUT={mut}',f'-GALL_SPLITS={allsp}','-DXCACHE_TP8']+list(manifest['sources'])
 with (out/(name+'_build.log')).open('w') as log:subprocess.run(cmd,cwd=case_src,stdout=log,stderr=subprocess.STDOUT,check=True)
 r=subprocess.run([str(out/('obj_'+name)/'Vtb_qwen_xcache_actual_tile')],cwd=case_src,capture_output=True,text=True)
 (out/(name+'.log')).write_text(r.stdout+r.stderr)
 if expected is None:
  if r.returncode or 'PASS actual CEXT2 tile' not in r.stdout:raise RuntimeError(r.stdout+r.stderr)
  return r.stdout
 if r.returncode==0 or expected not in r.stdout+r.stderr:raise RuntimeError('mutant escaped/mismatched: '+name+' '+r.stdout+r.stderr)
 return 'PASS rejected '+name
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
 for result in pool.map(run,cases):print(result,flush=True)
print('PASS fastaddress all six gates',flush=True)
