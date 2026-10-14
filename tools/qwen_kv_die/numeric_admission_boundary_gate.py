#!/usr/bin/env python3
"""Selected-tile local drain admission; never a full-field/source release."""
import pathlib,json,subprocess,os,hashlib,concurrent.futures
out=pathlib.Path.cwd();m=json.loads((out/'provenance.json').read_text());vlt=os.path.expanduser('~/.local/opentallas-tools/verilator-5.050/bin/verilator');records=[]
def run(bypass):
 name='bypass'if bypass else'positive';obj=out/('obj_'+name);cmd=[vlt,'--binary','--timing','-j','2','-Wno-fatal','-Wno-lint','--top-module','tb_qwen_numeric_admission_boundary','--Mdir',str(obj),f'-GBOUNDARY_BYPASS={bypass}','-DXCACHE_TP8']+list(m['sources'])
 with(out/(name+'_build.log')).open('w')as f:subprocess.run(cmd,cwd=out/'src',stdout=f,stderr=subprocess.STDOUT,check=True)
 binary=obj/'Vtb_qwen_numeric_admission_boundary';r=subprocess.run([str(binary)],cwd=out/'src',capture_output=True,text=True);log=r.stdout+r.stderr;(out/(name+'.log')).write_text(log)
 expected='boundary actual new query mismatched old active ledger'if bypass else'PASS boundary actual2accept112words112queryretire'
 records.append({'case':name,'exit':r.returncode,'expected_observed':expected,'command':cmd,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest()})
 if (bypass==0)!=(r.returncode==0)or expected not in log:raise RuntimeError(name+' unexpected '+log)
 return log
with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:
 for log in pool.map(run,[0,1]):print(log,flush=True)
(out/'receipt.json').write_text(json.dumps({'cases':records,'scope':'Selected-local2-operation boundary only; oldbank active/unsealed, no full768/source/node release or fabricated peer callbacks.'},indent=2)+'\n');print('PASS selected-local held-offer admission and actual bypass rejection',flush=True)
