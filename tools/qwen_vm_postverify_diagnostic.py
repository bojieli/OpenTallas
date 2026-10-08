#!/usr/bin/env python3
"""Source-preserving four-state simulation diagnostic; not silicon fault coverage."""
import argparse,json,hashlib,subprocess
from pathlib import Path
DIR=Path('rtl/test/qwen_vm_postverify_diagnostic_20261007')
BOOK=Path('results/rtl/qwen_vm_postverify_diagnostic_20261007')
PROVIDERS=['rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv','physical/asap7_memory_macros/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v','rtl/model_ready_ds_native_vm_r2_20261003/ot_v41_vm_bank4_macro_pipe_masked_visible_r2.sv']
def run(root,out):
 root=root.resolve();out.mkdir(parents=True,exist_ok=False);out=out.resolve();src=out/'src';src.mkdir()
 pins=json.loads((root/BOOK/'source_pins.json').read_text())
 for p,h in pins.items():assert hashlib.sha256((root/p).read_bytes()).hexdigest()==h,('source changed',p)
 files=[]
 for p in [*PROVIDERS,str(DIR/'ot_qwen_checked_vm_bank_simdiag.sv'),str(DIR/'tb_qwen_vm_postverify_diagnostic.sv')]:
  q=src/Path(p).name;q.write_bytes((root/p).read_bytes());files.append(str(q))
 (out/'inventory.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in src.iterdir()},indent=2)+'\n')
 results={}
 for strict in (0,1):
  for case in range(4):
   name=f's{strict}_c{case}';exe=out/name
   with (out/f'{name}.build.log').open('w') as f:subprocess.run(['iverilog','-g2012','-s','tb_qwen_vm_postverify_diagnostic',f'-Ptb_qwen_vm_postverify_diagnostic.STRICT={strict}',f'-Ptb_qwen_vm_postverify_diagnostic.CASE={case}','-o',str(exe),*files],stdout=f,stderr=f,check=True)
   p=subprocess.run(['vvp',str(exe)],capture_output=True,text=True);(out/f'{name}.log').write_text(p.stdout+p.stderr)
   marker='PASS observed_ACK' if case==0 or (not strict and case in (1,3)) else 'PASS fail_closed'
   assert p.returncode==0 and marker in p.stdout,(name,p.returncode,p.stdout)
   results[name]=dict(exit_code=p.returncode,marker=marker)
 (out/'results.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();run(a.root,a.out)
