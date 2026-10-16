#!/usr/bin/env python3
"""Actual exceptional HOST QM debt proof. Run under ot-run admission."""
import argparse,json,subprocess,pathlib,os

def main():
 p=argparse.ArgumentParser();p.add_argument('--sources',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args()
 a.out.mkdir(parents=True,exist_ok=True);a.out=a.out.resolve();ss=json.loads(a.sources.read_text());cases=[]
 for m in [0,1]:
  obj=a.out/f'obj_qm{m}'
  with (a.out/f'build{m}.log').open('w') as f:
   subprocess.run([os.environ.get('VERILATOR','verilator'),'--binary','--timing','-Wno-fatal','-j','2','--top-module','tb_host_qm_debt','-GMUT='+str(m),'--Mdir',str(obj),*ss,'rtl/test/qwen_static_kv/tb_host_qm_debt.sv'],stdout=f,stderr=subprocess.STDOUT,check=True)
  r=subprocess.run([str(obj/'Vtb_host_qm_debt')],capture_output=True,text=True);(a.out/f'run{m}.log').write_text(r.stdout+r.stderr)
  passed=(r.returncode==0 and 'PASS actual_QM' in r.stdout) if m==0 else (r.returncode!=0 and 'PARTIAL_DESCRIPTOR_FALSE_QUIET' in r.stdout)
  cases.append({'mutant':m,'returncode':r.returncode,'expected_result':passed})
 receipt={'status':'PASS' if all(c['expected_result'] for c in cases) else 'FAIL','cases':cases};(a.out/'receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt));return 0 if receipt['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
