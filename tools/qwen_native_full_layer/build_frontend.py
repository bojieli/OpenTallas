#!/usr/bin/env python3
"""Compile only control/transport; bind a separately pinned REAL kernel model."""
import argparse,hashlib,json,subprocess,time
from pathlib import Path
TOP='ot_qwen_tp8_native_services_frontend'
NAMES=('ot_qfd_su_kv_native_posted','ot_qfd_native_q_reader','ot_qfd_native_kv_commit_fence','ot_qfd_native_kv_row_provider','ot_qfd_native_qkv_provider','ot_qwen_tp8_native_attention_frontend','ot_qwen_tp8_attn_vm_commit',TOP)
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path.cwd());p.add_argument('--out',type=Path,required=True);p.add_argument('--jobs',type=int,default=4);a=p.parse_args()
 files=[a.root/'rtl/qwen_sys/redesign_qwen'/f'{n}.sv' for n in NAMES]+[a.root/'rtl/qwen_sys/kv_die_20261009/ot_qkvd_kv_seq_merged.sv']
 a.out.mkdir(parents=True,exist_ok=False)
 pins={str(f.relative_to(a.root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
 cmd=['/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator','--cc','--build','--top-module',TOP,'--Mdir',str(a.out/'obj'),'-j',str(a.jobs),'-Wno-fatal','-Wno-TIMESCALEMOD','-Wno-WIDTH','-CFLAGS','-O1']+list(map(str,files))
 t=time.monotonic()
 with (a.out/'build.log').open('w') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
 (a.out/'receipt.json').write_text(json.dumps({'scope':'CONTROL_TRANSPORT_LIBRARY_ONLY_REAL_EXTERNAL_KERNEL_REQUIRED','command':cmd,'exit':r.returncode,'seconds':time.monotonic()-t,'source_sha256':pins},indent=2)+'\n')
 raise SystemExit(r.returncode)
if __name__=='__main__':main()
