#!/usr/bin/env python3
"""One actual full512bit64row protected column, never a full array simulation."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
P='rtl/hbm_accel/collective_h2_ecc_20261007/'
FILES=['rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv','physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v',P+'ot_hbm_h2_ecc_column.sv',P+'tb_h2_ecc_column.sv']
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
 files=FILES+['tools/hbm_collective_h2_ecc_model.py','tools/hbm_collective_h2_ecc_gate.py','results/rtl/hbm_collective_h2_ecc_20261007/model_before_rtl.json']
 pins={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files};(a.out/'source_pins.json').write_text(json.dumps(pins,indent=2)+'\n')
 # Preserve actual source bytes for either a pass or an immutable failed run.
 snap=a.out/'source';snap.mkdir()
 for f in files:(snap/Path(f).name).write_bytes((ROOT/f).read_bytes())
 checks={}
 for name in ['baseline','corrupt_output']:
  inputs=[str(snap/Path(f).name) for f in FILES]
  if name=='corrupt_output':
   s=(snap/Path(FILES[2]).name).read_text();old='assign out_data[k*64+:64]=decoded[63:0];';assert s.count(old)==1
   m=a.out/'mutant.sv';m.write_text(s.replace(old,"assign out_data[k*64+:64]=decoded[63:0]^64'd1;"));inputs[2]=str(m)
   (a.out/'mutation.json').write_text(json.dumps({'replacement_from':old,'replacement_to':"assign out_data[k*64+:64]=decoded[63:0]^64'd1;",'sha256':hashlib.sha256(m.read_bytes()).hexdigest()},indent=2)+'\n')
  cmd=['iverilog','-g2012','-s','tb_h2_ecc_column','-o',str(a.out/(name+'.vvp'))]+inputs
  with (a.out/(name+'.build.log')).open('w') as log:b=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
  if b.returncode:checks[name]={'build_exit':b.returncode,'passed':False};break
  with (a.out/(name+'.log')).open('w') as log:r=subprocess.run(['vvp',str(a.out/(name+'.vvp'))],stdout=log,stderr=subprocess.STDOUT)
  output=(a.out/(name+'.log')).read_text()
  ok=(r.returncode==0 and 'PASS_H2_ECC_COLUMN' in output) if name=='baseline' else (r.returncode!=0 and 'DATA order mismatch' in output)
  checks[name]={'run_exit':r.returncode,'passed':ok,'output':output}
  if not ok:break
 record={'status':'PASS_COMPONENT_ONLY' if len(checks)==2 and all(x['passed'] for x in checks.values()) else 'FAIL','checks':checks,'scope':'Actual1R1W column and capture/identity check only. Full banked reduction, protected generation provider, physical timing and fullnative composition absent.'}
 (a.out/'record.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record));return record['status']=='FAIL'
if __name__=='__main__':raise SystemExit(main())
