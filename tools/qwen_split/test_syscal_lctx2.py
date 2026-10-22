#!/usr/bin/env python3
"""Minimum real calendar/reset component comparison; no deployment image claim."""
import hashlib,json,subprocess,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[2]
CAL=R/'rtl/qwen_sys/d2d_static_20261015'

def simulate(name,top,files,parameters=(),expect=0):
 with tempfile.TemporaryDirectory(prefix='lctx2-') as td:
  exe=Path(td)/'sim.vvp'
  subprocess.run(['iverilog','-g2012','-s',top,*parameters,'-o',str(exe),*map(str,files)],check=True)
  p=subprocess.run(['vvp',str(exe)],capture_output=True,text=True)
  if p.returncode!=expect:raise RuntimeError(f'{name} unexpected return {p.returncode}: {p.stdout} {p.stderr}')
  return dict(case=name,returncode=p.returncode,output=p.stdout.strip())

def main():
 wrapper=CAL/'qfd_syscal_lctx2.sv';reset=R/'rtl/qwen_split/qfd_sysface_reset_same3.sv'
 bench=R/'tools/qwen_split/tb_syscal_lctx2.sv'
 common=[bench,CAL/'ot_qwen_d2d_static.sv',CAL/'ot_qwen_d2d_cal_sysface32.sv']
 results=[simulate(f'NE{n}','tb_syscal_lctx2',common+[wrapper],[f'-Ptb_syscal_lctx2.NE={n}']) for n in (16,32,64)]
 results.append(simulate('same3_reset','tb_sysface_reset_same3',[R/'tools/qwen_split/tb_sysface_reset_same3.sv',reset]))
 with tempfile.TemporaryDirectory(prefix='lctx2-mutant-') as td:
  for name,text in [('segment_base_mutant',wrapper.read_text().replace(".seg_k({(4+G){start_seg}})",".seg_k({(4+G){1'b0}})")),('pointer_mutant',wrapper.read_text().replace('#(.NE(NE))','#(.NE(NE),.MUT(4))'))]:
   p=Path(td)/(name+'.sv');p.write_text(text)
   results.append(simulate(name,'tb_syscal_lctx2',common+[p],expect=1))
 print(json.dumps(dict(scope='same-edge component comparison and causal mutants only; no compiler deployment programme or physical claim',source_sha256={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [wrapper,reset,CAL/'ot_qwen_d2d_cal_sysface32.sv']},results=results),indent=2))
if __name__=='__main__':main()
