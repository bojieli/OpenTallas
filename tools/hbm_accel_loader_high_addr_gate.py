#!/usr/bin/env python3
"""Single high-address component enrollment, remote only; no token/4KiB replay."""
import argparse,hashlib,json,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=['rtl/hbm_accel/loader/'+n+'.sv' for n in ['ot_hbm_accel_loader_addr','ot_hbm_accel_store_addr','ot_hbm_accel_loader_host_addr','ot_hbm_accel_loader_addr_to_service','ot_hbm_accel_dma64']]+['rtl/gpu_sys/ot_gpu_cdc_fifo.sv','rtl/link/ot_link_afifo.sv','rtl/test/hbm_accel/tb_hbm_accel_loader_high_addr.sv']
def main():
 p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--jobs',type=int,default=16);a=p.parse_args()
 if not 1<=a.jobs<=16:p.error('jobs must be1..16')
 a.work.mkdir(parents=True,exist_ok=False)
 r={'source_pin':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'scope':'ND1 ADDR37 STACK2, fullDMA64 two sectors, CRC LOAD_VERIFY+STORE; explicit stacklocal service map, no currentfulltop or clock claim','sources':{s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in SRC},'parameters':{'ADDR_W':37,'STACK_W':2,'SECTOR_W':34,'STACK_BYTES':22500000000,'ND':1},'physical_qualified':False}
 cmd=[str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'),'--binary','--timing','-O1','-j',str(a.jobs),'-Wno-fatal','-Wno-lint','-Wno-style','-Wno-WIDTH','--x-assign','0','--x-initial','0','--top-module','tb_hbm_accel_loader_high_addr','--Mdir',str(a.work/'obj')]+[str(ROOT/s) for s in SRC]
 (a.work/'command.json').write_text(json.dumps(cmd,indent=2)+'\n');t=time.monotonic()
 with (a.work/'build.log').open('w') as f:b=subprocess.run(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
 r.update(build_rc=b.returncode,build_seconds=time.monotonic()-t,verdict='FAIL_BUILD')
 if b.returncode==0:
  with (a.work/'run.log').open('w') as f:b=subprocess.run([str(a.work/'obj/Vtb_hbm_accel_loader_high_addr')],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
  lines=(a.work/'run.log').read_text();r.update(run_rc=b.returncode,terminal_lines=[s for s in lines.splitlines() if s.startswith(('HIGHADDR','PASS','%Error'))],verdict='PASS' if b.returncode==0 and 'PASS high_address_component' in lines else 'FAIL_FUNCTIONAL')
 (a.work/'record.json').write_text(json.dumps(r,indent=2)+'\n');print(r['verdict'],flush=True);return 0 if r['verdict']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
