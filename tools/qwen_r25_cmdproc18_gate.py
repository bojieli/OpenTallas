#!/usr/bin/env python3
"""Reproduce minimum NSM16 TOKEN18 gates and a mandatory truncation mutant.

Compile outputs go to task-local scratch; immutable result directory must be new.
"""
import argparse,hashlib,json,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
R=Path('rtl/hbm_accel/qwen/r25')
MEM=Path('physical/asap7_memory_macros/ot_sram_2rw_512x64_m4_r2c2/ot_sram_2rw_512x64_m4_r2c2.v')

def run(args,output):
 p=subprocess.run(args,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 output.write_text(p.stdout)
 return p

def main():
 a=argparse.ArgumentParser();a.add_argument('--output',required=True,type=Path);args=a.parse_args()
 args.output.mkdir(parents=True,exist_ok=False)
 out=args.output.resolve()
 commands=[]
 with tempfile.TemporaryDirectory(prefix='qwen18-') as tmp:
  tmp=Path(tmp)
  for name,sram in [('regs',False),('sram',True)]:
   cmd=['iverilog','-g2012','-s','tb_qwen_r25_cmdproc18','-o',str(tmp/(name+'.vvp'))]
   if sram:cmd+=['-DSRAM']
   cmd+=[str(R/('ot_qwen_r25_cmdproc18_m.sv' if sram else 'ot_qwen_r25_cmdproc18.sv')),str(R/'tb_qwen_r25_cmdproc18.sv')]
   if sram:cmd+=[str(MEM)]
   commands.append(cmd);assert run(cmd,out/(name+'_compile.log')).returncode==0
   p=run(['vvp',str(tmp/(name+'.vvp'))],out/(name+'.log'))
   assert p.returncode==0 and 'exhaustive_tokens=151936' in p.stdout
  cmd=['iverilog','-g2012','-s','tb_qwen_r25_cmdproc18_split','-o',str(tmp/'split.vvp')]+[str(R/x) for x in ['tb_qwen_r25_cmdproc18_split.sv','hfd_cmdproc_n_qwen18.sv','hfd_cmdproc_s_qwen18.sv','ot_qwen_r25_cmdproc18_m.sv']]+['physical/hbm_accel_die_views/common/ot_hfd_oreg1.sv',str(MEM),'rtl/common/ot_fwd_link_stage.sv']
  commands.append(cmd);assert run(cmd,out/'split_compile.log').returncode==0
  p=run(['vvp',str(tmp/'split.vvp')],out/'split.log');assert p.returncode==0 and 'SPLIT_PASS' in p.stdout
  mutant=(ROOT/R/'ot_qwen_r25_cmdproc18.sv').read_text().replace('launch_token <= db_token;', 'launch_token <= db_token[16:0];')
  (tmp/'mutant.sv').write_text(mutant)
  cmd=['iverilog','-g2012','-s','tb_qwen_r25_cmdproc18','-o',str(tmp/'mutant.vvp'),str(tmp/'mutant.sv'),str(R/'tb_qwen_r25_cmdproc18.sv')]
  commands.append(cmd);assert run(cmd,out/'mutant_compile.log').returncode==0
  p=run(['vvp',str(tmp/'mutant.vvp')],out/'token17_mutant.log')
  assert p.returncode!=0 and 'LAUNCH_TRUNCATION token=131072 got=0' in p.stdout
  p=run(['python3','tools/qwen_r25_cmdproc_program.py'],out/'program.log');assert p.returncode==0
  p=run(['python3','tools/uarch_model_qwen_cmdproc18.py'],out/'model.json');assert p.returncode==0
 files=list((ROOT/R).glob('*.sv'))+[ROOT/MEM,ROOT/'tools/qwen_r25_cmdproc_program.py',ROOT/'tools/uarch_model_qwen_cmdproc18.py']
 (out/'manifest.json').write_text(json.dumps(dict(status='PASS_COMPONENT_ONLY',base='961688ad8',commands=commands,source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},actual_rtl=True,physical_qualification=False,full_qwen_graph=False),indent=2)+'\n')
 print('QWEN_CMDPROC18_GATE_PASS '+str(out))
if __name__=='__main__':main()
