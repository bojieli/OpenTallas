#!/usr/bin/env python3
"""Remote admitted native macro IKS component gate. Raw failures immutable."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parents[1]
SRC=['rtl/common/ot_secded.sv','rtl/common/ot_secded_cols.svh','physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v',
'physical/hbm_accel_die_views/svc/rtl/ot_hbm_index_lines_sram.sv','rtl/test/hbm_accel/tb_hbm_index_lines_sram.sv']
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--work',type=Path,required=True);a=ap.parse_args();a.work.mkdir(parents=True,exist_ok=False)
 v=str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator')
 rec={'schema':'opentallas.hbm_index_sram_gate.v1','source_commit':os.environ['PINNED_SOURCE_COMMIT'],'input_sha256':{s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in SRC},'verdict':'INCOMPLETE','cases':[],'scope':'native macro ports+capture+SECDED+remap full component; not physical closure'}
 (a.work/'record.json').write_text(json.dumps(rec,indent=2)+'\n')
 def run(mode):
  w=a.work/f'mode{mode}';w.mkdir()
  cmd=[v,'--binary','--timing','-Wno-fatal','-Wno-WIDTH','-j','4','-O2','--top-module','tb_hbm_index_lines_sram',f'-GMODE={mode}','-I'+str(ROOT/'rtl/common'),'--Mdir',str(w/'obj')]+[str(ROOT/s) for s in SRC if not s.endswith('.svh')]
  with(w/'build.log').open('w')as log:cp=subprocess.run(['/srv/opentallas-scratch/admit.sh','8','--','/usr/bin/time','-v']+cmd,stdout=log,stderr=subprocess.STDOUT)
  result={'mode':mode,'build_returncode':cp.returncode,'runs':[]}
  if not cp.returncode:
   for blocks,delay in [(342,1),(342,23)] if mode==0 else [(342,1)]:
    logpath=w/f'blocks{blocks}_delay{delay}.log'
    with logpath.open('w')as log:rp=subprocess.run([str(w/'obj/Vtb_hbm_index_lines_sram'),f'+blocks={blocks}',f'+credit_delay={delay}'],stdout=log,stderr=subprocess.STDOUT)
    raw=logpath.read_text();marker='PASS_EXPECTED_PROTECTED_FAULT' if mode>=3 else 'PASS_HBM_INDEX_LINES_SRAM'
    result['runs'].append(dict(blocks=blocks,credit_delay=delay,returncode=rp.returncode,gate_passed=rp.returncode==0 and marker in raw,raw_log=str(logpath.relative_to(a.work)),sha256=hashlib.sha256(logpath.read_bytes()).hexdigest()))
  result['gate_passed']=cp.returncode==0 and bool(result['runs']) and all(x['gate_passed'] for x in result['runs'])
  return result
 with ThreadPoolExecutor(5)as pool:
  for result in pool.map(run,range(5)):
   rec['cases'].append(result);(a.work/'record.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(result),flush=True)
 rec['verdict']='PASS' if all(x['gate_passed']for x in rec['cases'])else'FAIL';(a.work/'record.json').write_text(json.dumps(rec,indent=2)+'\n')
 return 0 if rec['verdict']=='PASS'else 1
if __name__=='__main__':raise SystemExit(main())
