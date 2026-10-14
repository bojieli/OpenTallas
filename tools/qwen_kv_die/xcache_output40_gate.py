#!/usr/bin/env python3
"""Actual request-mode counterexample and default-off repair; ot-run only."""
import concurrent.futures,json,os,pathlib,subprocess,shutil,hashlib
out=pathlib.Path.cwd();m=json.loads((out/'provenance.json').read_text());src=out/'src'
vlt=os.path.expanduser('~/.local/opentallas-tools/verilator-5.050/bin/verilator')
cases=[('repair',0,0,None),('raw_split_repair',0,1,None),('output_tag_mutant',4,0,'actual output40 mask/identity/arithmetic edge mismatch'),('output_valid_mutant',4,0,'output40 event without allocated query'),('queue_word_mutant',4,0,'actual posted numeric word mismatch'),('queue_type_mutant',4,1,'actual posted output mask/tag mismatch')]
def run(case):
 name,mut,allsp,expected=case;case_src=src
 if name.startswith('output_'):
  case_src=out/('src_'+name);shutil.copytree(src,case_src,dirs_exist_ok=True)
  f=case_src/'rtl/physical/ot_qwen_tile_query_output_identity.sv';b=f.read_text();before='query_output_tuple<=metadata[44];'if name=='output_tag_mutant'else'valid<={valid[43:0],query_issue_v};';after='query_output_tuple<=metadata[43];'if name=='output_tag_mutant'else"valid<={valid[43:0],1'b1};"
  if b.count(before)!=1:raise RuntimeError('source mutation nonunique')
  f.write_text(b.replace(before,after));(out/(name+'_provenance.json')).write_text(json.dumps({'before':before,'after':after,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()},indent=2)+'\n')
 if name.startswith('queue_'):
  case_src=out/('src_'+name);shutil.copytree(src,case_src,dirs_exist_ok=True)
  f=case_src/'rtl/physical/ot_qwen_numeric_output_queue.sv';b=f.read_text();before='entries[tail]<={numeric_word,query_pending,query_output_tuple,query_output_toggle};';after="entries[tail]<={numeric_word ^ 512'd1,query_pending,query_output_tuple,query_output_toggle};"if name=='queue_word_mutant'else"entries[tail]<={numeric_word,1'b1,query_output_tuple,query_output_toggle};"
  if b.count(before)!=1:raise RuntimeError('queue mutation nonunique')
  f.write_text(b.replace(before,after));(out/(name+'_provenance.json')).write_text(json.dumps({'before':before,'after':after,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()},indent=2)+'\n')
 cmd=[vlt,'--binary','--timing','-j','3','-Wno-fatal','-Wno-lint','--top-module','tb_qwen_xcache_output40','--Mdir',str(out/('obj_'+name)),f'-GMUT={mut}',f'-GALL_SPLITS={allsp}','-DXCACHE_TP8']+list(m['sources'])
 with (out/(name+'_build.log')).open('w')as log:subprocess.run(cmd,cwd=case_src,stdout=log,stderr=subprocess.STDOUT,check=True)
 r=subprocess.run([str(out/('obj_'+name)/'Vtb_qwen_xcache_output40')],cwd=case_src,capture_output=True,text=True);(out/(name+'.log')).write_text(r.stdout+r.stderr)
 if expected:
  if r.returncode==0 or expected not in r.stdout+r.stderr:raise RuntimeError(name+' escaped or mismatched: '+r.stdout+r.stderr)
  return 'PASS reproduced/refused '+name
 if r.returncode or 'PASS production acceptedIB and request ports'not in r.stdout:raise RuntimeError(r.stdout+r.stderr)
 return r.stdout
with concurrent.futures.ThreadPoolExecutor(max_workers=6)as p:
 for r in p.map(run,cases):print(r,flush=True)
print('PASS actual tagged all-numeric output40 six gates',flush=True)
