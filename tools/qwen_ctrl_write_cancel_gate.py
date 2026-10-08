#!/usr/bin/env python3
"""Minimum native cancellation gate; no physical or global-epoch qualification."""
import argparse, pathlib, subprocess, hashlib, json, tempfile

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source-root',type=pathlib.Path,default=pathlib.Path(__file__).resolve().parents[1]);ap.add_argument('--out',type=pathlib.Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 rtl=a.source_root/'rtl/physical/ot_qwen_ctrl_write_cancel.sv';bench=a.source_root/'rtl/test/tb_qwen_ctrl_write_cancel.sv';off=a.source_root/'rtl/test/tb_qwen_ctrl_write_cancel_disabled.sv';cases=[]
 with tempfile.TemporaryDirectory(prefix='qwen-cancel-gate-') as t:
  def run(name,module,src,pc=None,negative=False):
   cmd=['iverilog','-g2012','-s',module,'-o',t+'/sim']
   if pc is not None:cmd+=[f'-P{module}.PC={pc}']
   c=subprocess.run(cmd+[str(rtl),str(src)],capture_output=True,text=True);(a.out/(name+'.compile.log')).write_text(c.stdout+c.stderr)
   if c.returncode:raise RuntimeError(c.stderr)
   r=subprocess.run(['vvp',t+'/sim'],capture_output=True,text=True);log=r.stdout+r.stderr;(a.out/(name+'.log')).write_text(log)
   passed=(r.returncode!=0 and 'wrong typed cancellation escaped' in log) if negative else r.returncode==0 and 'PASS' in log
   cases.append(dict(case=name,negative=negative,returncode=r.returncode,qualified=passed))
  for pc in (0,31):run(f'pc{pc}','tb_qwen_ctrl_write_cancel',bench,pc)
  run('disabled','tb_qwen_ctrl_write_cancel_disabled',off)
  s=bench.read_text();i=s.index('  for(t=0;t<34;');s=s[:i]+s[i:].replace('for(t=0;t<34;t=t+1)','for(t=1;t<2;t=t+1)',1).replace('inject(t);block_expected=1;','force dut.agree=1;inject(t);block_expected=0;',1)
  s=s.replace('ctrl_fault=1;edge_step();cancel_take=1;','ctrl_fault=1;edge_step();cancel_take=1;cancel_expected=257;');mut=pathlib.Path(t)/'mutant.sv';mut.write_text(s);run('cancel_tag_bypass_negative','tb_qwen_ctrl_write_cancel',mut,negative=True)
 receipt=dict(pass_all=all(c['qualified'] for c in cases),cases=cases,source_sha256={str(f.relative_to(a.source_root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in (rtl,bench,off)},scope='Native typed cancellation, true completion, delayed ingress and68 single-state-upset cases; mapped independence, CDC, external refresh and global fence remain unqualified')
 (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt));return 0 if receipt['pass_all'] else 1
if __name__=='__main__':raise SystemExit(main())
