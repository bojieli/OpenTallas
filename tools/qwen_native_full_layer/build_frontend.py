#!/usr/bin/env python3
"""Compile only control/transport; bind a separately pinned REAL kernel model."""
import argparse,hashlib,json,subprocess,time
from pathlib import Path
TOP='ot_qwen_tp8_native_services_frontend'
NAMES=('ot_qfd_su_kv_native_posted','ot_qfd_native_q_reader','ot_qfd_native_kv_commit_fence','ot_qfd_native_kv_row_provider','ot_qfd_native_qkv_provider','ot_qwen_tp8_native_attention_frontend','ot_qwen_tp8_attn_vm_commit',TOP)
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path.cwd());p.add_argument('--out',type=Path,required=True);p.add_argument('--jobs',type=int,default=4);p.add_argument('--sector-only',action='store_true');p.add_argument('--native59',action='store_true');a=p.parse_args()
 if a.sector_only and a.native59:raise ValueError('distinct provider profiles')
 names=NAMES[:-1]+('ot_qwen_tp8_native_services_frontend_native59',) if a.native59 else NAMES
 files=[a.root/'rtl/qwen_sys/redesign_qwen'/f'{n}.sv' for n in names]+[a.root/'rtl/qwen_sys/kv_die_20261009/ot_qkvd_kv_seq_merged.sv']
 top=TOP
 if a.native59:top='ot_qwen_tp8_native_services_frontend_native59'
 if a.sector_only:
  top='ot_qwen_tp8_kv_sector_adapter'
  files=[a.root/'rtl/qwen_sys/redesign_qwen/ot_qwen_tp8_kv_sector_adapter.sv',a.root/'rtl/qwen_sys/host_20261013/qkd_host_ingest_map.sv']
 a.out.mkdir(parents=True,exist_ok=False)
 pins={str(f.relative_to(a.root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
 cmd=['/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator','--cc','--build','--top-module',top,'--Mdir',str(a.out/'obj'),'-j',str(a.jobs),'-Wno-fatal','-Wno-TIMESCALEMOD','-Wno-WIDTH','-CFLAGS','-O1']+list(map(str,files))
 if a.native59:cmd.insert(1,'-GENABLE_NATIVE=1')
 t=time.monotonic()
 with (a.out/'build.log').open('w') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
 (a.out/'receipt.json').write_text(json.dumps({'scope':'CONTROL_TRANSPORT_LIBRARY_ONLY_REAL_EXTERNAL_KERNEL_REQUIRED','command':cmd,'exit':r.returncode,'seconds':time.monotonic()-t,'source_sha256':pins},indent=2)+'\n')
 raise SystemExit(r.returncode)
if __name__=='__main__':main()
