#!/usr/bin/env python3
"""Fresh immutable22-root source binding; no old-source receipts reused."""
import pathlib,json,subprocess,os,hashlib,concurrent.futures
out=pathlib.Path.cwd();m=json.loads((out/'provenance.json').read_text());vlt=os.path.expanduser('~/.local/opentallas-tools/verilator-5.050/bin/verilator');records=[]
cases=[('native','tb_qwen_numeric_merged_lifetime',0,0,None),('full_stalls','tb_qwen_numeric_merged_lifetime',1,1,None),('boundary','tb_qwen_numeric_merged_boundary',0,0,None),('bypass','tb_qwen_numeric_merged_boundary',0,1,'boundary actual new query mismatched old active ledger')]
def run(case):
 name,top,arg0,arg1,expected=case;obj=out/('obj_'+name);flags=[f'-GBOUNDARY_BYPASS={arg1}']if 'boundary'in top else[f'-GALL_SPLITS={arg0}',f'-GFULL_STALLS={arg1}'];files=[f for f in m['sources']if '/tb_qwen_numeric_merged_'not in f or f.endswith(top+'.sv')]
 cmd=[vlt,'--binary','--timing','-j','2','-Wno-fatal','-Wno-lint','--top-module',top,'--Mdir',str(obj)]+flags+['-DXCACHE_TP8']+files
 with(out/(name+'_build.log')).open('w')as log:subprocess.run(cmd,cwd=out/'src',stdout=log,stderr=subprocess.STDOUT,check=True)
 binary=obj/('V'+top);r=subprocess.run([str(binary)],cwd=out/'src',capture_output=True,text=True);text=r.stdout+r.stderr;(out/(name+'.log')).write_text(text);records.append({'case':name,'top':top,'exit':r.returncode,'command':cmd,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'expected_observed':expected})
 if expected:
  if not r.returncode or expected not in text:raise RuntimeError(name+' escaped '+text)
 elif r.returncode or ('PASS boundary actual2accept112words112queryretire'if 'boundary'in top else'PASS production acceptedIB and request ports')not in text:raise RuntimeError(text)
 return text
with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:
 for log in pool.map(run,cases):print(log,flush=True)
(out/'receipt.json').write_text(json.dumps({'cases':records,'parent_commit':m['parent_commit'],'root_count':22,'physical_claim':False},indent=2)+'\n');print('PASS fresh merged arithmetic/full stalls/reset/local boundary/bypass',flush=True)
