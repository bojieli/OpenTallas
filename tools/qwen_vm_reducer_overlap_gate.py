#!/usr/bin/env python3
"""Actual captured parent160 replay through full ROM-aperture protected adapter."""
import argparse,json,hashlib,subprocess,shutil,os
from pathlib import Path
BOOK=Path('results/rtl/qwen_vm_reducer_overlap_20261007')
BENCH=Path('rtl/test/qwen_vm_reducer_overlap_20261007/tb_qwen_vm_reducer_overlap.sv')
FIXTURE=Path('results/rtl/qwen_hbm_activation_vm_realization_20261005/minimum_adapter_case/initial_x4096.u32.hex')
CALENDAR=Path('results/rtl/qwen_vm_composed_control_20261007/calendar.json')
CALPIN='6f8a3293d34a7c58130fb825e270929529a50322c0bb5827130db9aaaa3939ac'
SRC=['rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv','rtl/hdc/ot_hdc_cg.sv','physical/asap7_memory_macros/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v']+['rtl/hbm_accel/qwen/vm_direct_readback_20261007/'+n+'.sv' for n in ['ot_qwen_vm_bank4_direct_readback','ot_qwen_checked_vm_bank_direct_readback','ot_qwen_finite_vm_adapter_direct_readback']]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(a):
 root=a.root.resolve();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);src=out/'src';src.mkdir()
 pins=json.loads((root/BOOK/'source_pins.json').read_text())
 for path,pin in pins.items():assert sha(root/path)==pin,('pinned source mismatch',path)
 calendar=a.calendar or root/CALENDAR;assert sha(calendar)==CALPIN,'calendar pin changed'
 cal=json.loads(calendar.read_text());edge=next(e for e in cal['edges'] if e['cycle']==160);frame=cal['frames'][edge['frame']]
 assert frame['writes']==[dict(family='REDUCER',seat=0,address=16160)] and len(frame['reads']['VX'])==2048
 ra=re=0
 for seat,addr in frame['reads']['VX']:ra|=addr<<(24*(208+seat));re|=1<<(208+seat)
 (out/'addresses.hex').write_text(format(ra,'x')+'\n');(out/'enables.hex').write_text(format(re,'x')+'\n');(out/'fixture.hex').write_bytes((root/FIXTURE).read_bytes())
 sources=[]
 for path in SRC+[str(BENCH)]:
  p=src/Path(path).name;p.write_bytes((root/path).read_bytes());sources.append(str(p))
 (out/'admission.json').write_text(json.dumps(dict(load=os.getloadavg(),meminfo=Path('/proc/meminfo').read_text(),disk_free_bytes=shutil.disk_usage(out).free,known_prior_build_peak_KiB=126720,known_prior_run_peak_KiB=55296,source_inventory={p.name:dict(sha256=sha(p),bytes=p.stat().st_size) for p in src.iterdir()}),indent=2)+'\n')
 with (out/'build.log').open('w') as f:subprocess.run(['iverilog','-g2012','-s','tb_qwen_vm_reducer_overlap','-o',str(out/'sim'),*sources],stdout=f,stderr=f,check=True)
 terminal={}
 for case in range(4):
  command=['vvp',str(out/'sim'),'+FIXTURE='+str(out/'fixture.hex'),'+ADDRESSES='+str(out/'addresses.hex'),'+ENABLES='+str(out/'enables.hex'),f'+NEGATIVE={case}']
  p=subprocess.run(command,capture_output=True,text=True);(out/f'case{case}.log').write_text(p.stdout+p.stderr)
  expected=['PASS full_aperture_parent160','FOREIGN_REDUCER_ACK_REJECTED','UNPAID_NATIVE_ADVANCE','UNPAID_NATIVE_ADVANCE'][case]
  assert expected in p.stdout and ((p.returncode==0)==(case==0)),(case,p.returncode,p.stdout)
  terminal[case]=dict(exit_code=p.returncode,marker=expected)
 (out/'terminal.json').write_text(json.dumps(terminal,indent=2)+'\n');print(json.dumps(terminal))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',required=True,type=Path);p.add_argument('--out',required=True,type=Path);p.add_argument('--calendar',type=Path);run(p.parse_args())
