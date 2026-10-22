#!/usr/bin/env python3
"""Actual 17-source hierarchy/capture minimum, not a deployed programme proof."""
import hashlib,json,re,subprocess,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[2]
P=R/'rtl/qwen_split/qfd_sys_face_lctx3_wrapped.sv'
def main():
 sources=[R/s for s in (R/'results/arch/codex_sysface_l_2000/wrapper_sources.f').read_text().splitlines()]
 source=P.read_text();expr=re.search(r'copy_0<=([^;]+);',source)[1]
 assert expr=='prog_auth_slot'
 variants=dict(selected=source,wrong_source_mutant=source.replace('copy_0<=prog_auth_slot;','copy_0<=~prog_auth_slot;',1),extra_capture_edge_mutant=source.replace('copy_0<=prog_auth_slot;','copy_0<=prog_auth_slot__ot_q;',1))
 out=[]
 with tempfile.TemporaryDirectory(prefix='lctx-wrapper-') as td:
  for name,text in variants.items():
   p=Path(td)/(name+'.sv');p.write_text(text);exe=Path(td)/(name+'.vvp')
   ss=[p if x==P else x for x in sources]
   subprocess.run(['iverilog','-g2012','-DSYNTHESIS','-s','tb_lctx3_wrapper_capture','-I',str(R/'rtl/qwen_sys/d2d_static_20261015'),'-o',str(exe),*map(str,ss),str(R/'tools/qwen_split/tb_lctx3_wrapper_capture.sv')],check=True)
   v=subprocess.run(['vvp',str(exe)],text=True,capture_output=True)
   expect=0 if name=='selected' else 1
   if v.returncode!=expect:raise RuntimeError(f'{name}: return{v.returncode} {v.stdout}')
   out.append(dict(case=name,returncode=v.returncode,output=v.stdout.strip()))
 print(json.dumps(dict(scope='Actual full hierarchy elaborated, wrapper captures/reset only; core Q wires driven for output-capture test; no programme is installed or qualified',wrapper_sha256=hashlib.sha256(P.read_bytes()).hexdigest(),abi_port_count=93,results=out),indent=2))
if __name__=='__main__':main()
