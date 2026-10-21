#!/usr/bin/env python3
"""Prove actual old/new window functions on all32 input bits; causal mutant."""
import re,pathlib,subprocess,json,hashlib
root=pathlib.Path(__file__).resolve().parents[3];out=root/'results/arch/codex_k_pvfin_1021/win_proof';out.mkdir(parents=True,exist_ok=True)
a=root/'results/arch/codex_k_pvfin_1021/win_original.txt';b=root/'rtl/qwen_sys/split_20261014/qkd_pv_fin_s32.sv';old=a.read_text();new=re.search(r'function automatic win\(.*?endfunction',b.read_text(),re.S).group()
def rename(s,n):return re.sub(r'\bwin\b',n,s)
res={}
for mut in (0,1):
 f=new if mut==0 else new.replace('&&low_ge','&&!low_ge',1)
 assert f!=new or mut==0
 s='module m(input[15:0]x,lo,output same);\n'+rename(old,'gold')+'\n'+rename(f,'dut')+'\nassign same=(gold(x,lo)==dut(x,lo));\nendmodule\n'
 p=out/f'm{mut}.v';p.write_text(s)
 r=subprocess.run(['yosys','-p',f'read_verilog -sv {p}; prep -top m; flatten; opt; sat -verify -prove same 1 -show x -show lo'],capture_output=True,text=True)
 (out/f'm{mut}.log').write_text(r.stdout+r.stderr)
 assert (r.returncode==0)==(mut==0),(mut,r.returncode)
 res[str(mut)]={'rc':r.returncode,'miter_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
res.update(qualified=False,scope='exact combinational function only; all16-bit x/lo including unsigned overflow',source_sha256=hashlib.sha256(b.read_bytes()).hexdigest(),original_function_sha256=hashlib.sha256(a.read_bytes()).hexdigest())
(out/'summary.json').write_text(json.dumps(res,indent=2)+'\n');print('WIN32_PROOF_PASS_AND_MUTANT_CAUGHT')
