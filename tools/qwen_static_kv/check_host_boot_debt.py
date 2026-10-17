#!/usr/bin/env python3
"""Actual cold-boot debt proof. Heavy compilation must use ot-run admission."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SOURCES=['rtl/qwen_sys/split_20261014/'+p+'.sv' for p in ['qkd_hbm_boot_static_completion_debt','qkd_hbm_boot_static','qkd_hbm_boot_pc','qkd_static_completion_ownerdemux']]+['rtl/test/qwen_static_kv/tb_host_boot_debt.sv']
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=True);cases=[]
 for m in [0,2]:
  obj=a.out/f'obj{m}'
  with (a.out/f'build{m}.log').open('w') as f:
   subprocess.run([os.environ.get('VERILATOR','verilator'),'--binary','--timing','-Wno-fatal','-j','2','--top-module','tb_host_boot_debt','-GMUT='+str(m),'--Mdir',str(obj),*[str(ROOT/p) for p in SOURCES]],stdout=f,stderr=subprocess.STDOUT,check=True)
  r=subprocess.run([str(obj/'Vtb_host_boot_debt')],capture_output=True,text=True);(a.out/f'run{m}.log').write_text(r.stdout+r.stderr)
  ok=(r.returncode==0 and 'PASS actualboot' in r.stdout) if m==0 else (r.returncode!=0 and 'BOOT_FALSE_QUIET' in r.stdout)
  cases.append({'mutant':m,'returncode':r.returncode,'expected':ok})
 result={'status':'PASS' if all(c['expected'] for c in cases) else 'FAIL','scope':'component only; controller declared boundary','cases':cases,'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES}};(a.out/'receipt.json').write_text(json.dumps(result,indent=2));print(json.dumps(result));return 0 if result['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
