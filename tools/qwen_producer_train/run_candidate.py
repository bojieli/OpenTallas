#!/usr/bin/env python3
import pathlib,subprocess,tempfile
D=pathlib.Path(__file__).resolve().parent;R=D.parents[1];logs=D/'candidate_checks';logs.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory() as tmp:
 for name,params in [('stride16',[]),('stride48',['-Ptb_train.STRIDE=48']),('missing',['-Ptb_train.MUT=1']),('extra',['-Ptb_train.MUT=2']),('overlap',['-Ptb_train.MUT=3']),('wide',['-Ptb_train.MUT=4'])]:
  binary=str(pathlib.Path(tmp)/name)
  subprocess.run(['iverilog','-g2012','-s','tb_train',*params,'-o',binary,str(D/'tb_train.sv'),str(R/'rtl/qwen_split/qfd_res_train_static.sv')],check=True)
  result=subprocess.run(['vvp',binary],capture_output=True,text=True);(logs/(name+'.log')).write_text(result.stdout+result.stderr);assert result.returncode==0,(name,result.stdout)
 source=(R/'rtl/qwen_split/qfd_res_train_static.sv').read_text();mutant=pathlib.Path(tmp)/'mutant.sv';mutant.write_text(source.replace('FIRST=D+24*INDEX+8*BAND','FIRST=D+23*INDEX+8*BAND'))
 subprocess.run(['iverilog','-g2012','-s','tb_train','-o',str(pathlib.Path(tmp)/'mutant'),str(D/'tb_train.sv'),str(mutant)],check=True)
 result=subprocess.run(['vvp',str(pathlib.Path(tmp)/'mutant')],capture_output=True,text=True);(logs/'timing_mutant.log').write_text(result.stdout+result.stderr);assert result.returncode!=0
print('PASS six candidate cases and actual bank timing mutant')
