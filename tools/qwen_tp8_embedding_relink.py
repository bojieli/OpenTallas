#!/usr/bin/env python3
"""Relink read-only accepted-word observer against an unchanged actual model."""
import argparse,hashlib,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--obj',type=Path,required=True);p.add_argument('--bench',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
a.out.mkdir(parents=True,exist_ok=False)
inputs=[a.bench,a.obj/'Vot_qwen_tp8_embedding_core__ALL.a',a.obj/'Vot_qwen_tp8_embedding_core.h',a.obj/'Vot_qwen_tp8_embedding_core___024root.h']
objects=[a.obj/name for name in ('Vot_qwen_tp8_embedding_core__ALL.a','sim_hdc_v41x_fastfp_dpi.o','verilated.o','verilated_dpi.o','verilated_threads.o')]
inputs+=objects[1:]
pins={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in inputs}
inc='/home/ubuntu/.local/opentallas-tools/verilator-5.050/share/verilator/include'
cmd=['g++','-std=c++17','-O1','-I'+str(a.obj),'-I'+inc,'-I'+inc+'/vltstd',str(a.bench),*map(str,objects),'-pthread','-o',str(a.out/'Vtb')]
with (a.out/'link.log').open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
report={'scope':'Read-only actual FIFO-decode/NEXT accepted1024-bit witness, unchanged RTL library',
        'command':cmd,'exit':r.returncode,'source_binary_sha256':pins}
if r.returncode==0:report['binary_sha256']=hashlib.sha256((a.out/'Vtb').read_bytes()).hexdigest()
(a.out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');raise SystemExit(r.returncode)
