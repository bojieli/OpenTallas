#!/usr/bin/env python3
"""Exact current static leaves: component-only positive and hardware mutant proof."""
import argparse,json,pathlib,subprocess,hashlib
p=argparse.ArgumentParser();p.add_argument('leaf',choices=['issuer','argmax','vmwrite']);p.add_argument('out');a=p.parse_args()
r=pathlib.Path(__file__).resolve().parents[2];o=pathlib.Path(a.out).resolve();o.mkdir(parents=True,exist_ok=True)
base='rtl/hbm_accel/generic/collective/p2p/'
leaf={'issuer':('ot_hgi_coll_static_issuer','MUT_DATA',[base+'ot_hgi_coll_static_issuer.sv','physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v']), 'argmax':('ot_hgi_coll_argmax_static','MUT_TIE',[base+'ot_hgi_coll_argmax_static.sv','rtl/hbm_accel/generic/collective/ot_hgi_coll_amerge.sv']), 'vmwrite':('ot_hgi_coll_static_vmwrite','MUT',[base+'ot_hgi_coll_static_vmwrite.sv'])}[a.leaf]
top='tb_'+leaf[0].removeprefix('ot_');files=leaf[2]+[base+top+'.sv'];rec={'scope':'component boundary only; no physical or whole-chip qualification','source_sha256':{f:hashlib.sha256((r/f).read_bytes()).hexdigest() for f in files},'cases':[]}
for mutation in (0,1):
 b=o/('mutant' if mutation else 'positive');b.mkdir(exist_ok=True)
 cmd=['verilator','--binary','--timing','-Wno-fatal','--top-module',top,'-j','2','--Mdir',str(b/'obj'),'-G'+leaf[1]+'='+str(mutation)]+files
 with (b/'build.log').open('w') as log:subprocess.run(cmd,cwd=r,stdout=log,stderr=subprocess.STDOUT,check=True)
 with (b/'run.log').open('w') as log:run=subprocess.run([str(b/'obj'/('V'+top))],cwd=r,stdout=log,stderr=subprocess.STDOUT)
 text=(b/'run.log').read_text(); ok=(run.returncode!=0 and ('FAIL' in text or 'Error' in text or 'fatal' in text)) if mutation else (run.returncode==0 and 'PASS' in text)
 rec['cases'].append({'mutation':mutation,'exit':run.returncode,'expected_result_observed':ok,'output':text})
 (o/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n')
 if not ok:raise SystemExit('unexpected proof outcome')
rec['status']='PASS';(o/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec,indent=2))
