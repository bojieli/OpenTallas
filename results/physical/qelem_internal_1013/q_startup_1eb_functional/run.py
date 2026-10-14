from pathlib import Path
import json,subprocess,hashlib
base=Path(__file__).resolve().parent;src=base/'src';out=base/'proof';out.mkdir(exist_ok=True)
manifest=json.loads((base/'source_manifest.json').read_text());assert all(hashlib.sha256((src/p).read_bytes()).hexdigest()==h for p,h in manifest['source_sha256'].items())
sources=list(manifest['source_sha256']);receipt={'source_manifest':manifest,'physical_admission':False,'scope':'PQ1 genuine reset/clock startup witnesses; PQ0 existing independent numerical benchmark','cases':[]}
for label,top,defs in [('startup','tb_s81_q_startup',[]),('omitted_tree_mutant','tb_s81_q_startup',['+define+S81_Q_STARTUP_OMIT_LAST']),('numerical','tb_s81_q_startup_exact',['+define+QT_CHECK','+define+QP_CHECK','+define+QX_DUT_PQ0','+define+QX_QM=5','+define+QX_QS=6','+define+QX_QH=1','+define+QX_QCG=1'])]:
 cmd=['/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator','--binary','--timing','-Wno-fatal','-Wno-lint','-Wno-style','--top-module',top,'--Mdir',str(out/label),'-j','8','-CFLAGS','-O1']+defs+[str(src/p) for p in sources]
 with (out/(label+'.build.log')).open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,cwd=src)
 receipt.setdefault('builds',{})[label]={'command':cmd,'exit':r.returncode};(out/'gate.json').write_text(json.dumps(receipt,indent=2));print('BUILD',label,r.returncode,flush=True)
 if r.returncode:raise SystemExit(r.returncode)
 for seed,sparse in ([(1,False),(2,False),(3,False),(4,False),(1,True)] if label=='numerical' else [(0,False)]):
  name=label+str(seed)+('_nan_sparse' if sparse else '');cmd=[str(out/label/('V'+top))]+([f'+seed={seed}']+(['+nan_sparse'] if sparse else []) if label=='numerical' else [])
  with (out/(name+'.log')).open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,cwd=src)
  text=(out/(name+'.log')).read_text();ok=(r.returncode!=0 and 'omitted real tree reset consumer' in text) if label=='omitted_tree_mutant' else r.returncode==0
  receipt['cases'].append({'name':name,'exit':r.returncode,'observed_expected':ok,'log_sha256':hashlib.sha256((out/(name+'.log')).read_bytes()).hexdigest()});(out/'gate.json').write_text(json.dumps(receipt,indent=2));print('CASE',name,r.returncode,ok,flush=True)
  if not ok:raise SystemExit(1)
receipt['verdict']='ACTUAL_STARTUP_PASS_OWNED_MUTANT_FAIL_PQ0_NUMERICAL_PASS';(out/'gate.json').write_text(json.dumps(receipt,indent=2));print('Q_STARTUP_PROOF_DONE',flush=True)
