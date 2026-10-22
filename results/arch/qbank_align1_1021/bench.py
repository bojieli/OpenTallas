#!/usr/bin/env python3
"""Normal closure replay of the existing minimum source-bound qbank scoreboard."""
import pathlib, subprocess, sys
mode, output = sys.argv[1:]
assert mode in ('positive', 'alignment_mutant')
root=pathlib.Path(__file__).resolve().parents[3]
out=pathlib.Path(output).resolve();out.mkdir(parents=True,exist_ok=True)
vl=pathlib.Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
assert vl.is_file(), 'required Verilator5.050 missing'
assert '5.050' in subprocess.check_output([str(vl),'--version'],text=True)
obj=out/'obj';align=1 if mode=='positive' else 0
cmd=[str(vl),'--binary','--timing','-j','4','-Wno-fatal','-Wno-lint','--top-module','tb_qbank',f'-GALIGN={align}','--Mdir',str(obj),str(root/'rtl/qwen_split/qfd_native59_qbank.sv'),str(root/'physical/asap7_memory_macros/ot_sram_1r1w_32x512_m1/ot_sram_1r1w_32x512_m1.v'),str(root/'results/rtl/tokfunc3_qw_1021/qbank_alignment_current/tb_qbank.sv')]
with (out/'build.log').open('w') as f: subprocess.run(cmd,check=True,stdout=f,stderr=subprocess.STDOUT)
for gap in ([1,2] if mode=='positive' else [1]):
 p=subprocess.run([str(obj/'Vtb_qbank'),f'+GAP={gap}'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 (out/f'gap{gap}.log').write_text(p.stdout);print(p.stdout,end='',flush=True)
 if mode=='alignment_mutant':
  assert p.returncode!=0 and 'QB_FAIL' in p.stdout and 'QB_MISMATCH' in p.stdout, 'mutant did not reproduce named alignment error'
  raise SystemExit(1)
 assert p.returncode==0 and f'QB_PASS ALIGN=1 LOCAL32=0 GAP={gap} rows=32 checks=512' in p.stdout, 'positive scoreboard failed'
