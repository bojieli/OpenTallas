#!/usr/bin/env python3
"""All-port pinned mapped-original/source-copy simulation with real SRAM models."""
from pathlib import Path
import importlib.util,json,re,subprocess,sys
sp=importlib.util.spec_from_file_location('tl','textbook_lint.py');m=importlib.util.module_from_spec(sp);sys.modules['tl']=m;sp.loader.exec_module(m)
mods=m.parse_verilog(Path('original.v').read_text());g,top=m.flatten(mods,None);ports=mods[top]
top2=sys.argv[1]if len(sys.argv)>1 else'qkd_hr_core_prompt_n32';decl=['`timescale 1ns/1ps','module tb;','integer seed=251;integer n=0;','reg ck_core=0;always #5 ck_core=~ck_core;']
ca=[];cb=[];outs=[];rand=[]
for p in ports.ports:
 w='' if p not in ports.widths else '[%d:%d] '%ports.widths[p]
 if ports.dirs[p]=='input':
  if p!='ck_core':decl+=['reg '+w+p+'=0;']
  ca+=['.'+p+'('+p+')'];cb+=['.'+p+'('+p+')']
  if p not in ('ck_core','u_rank__u_control__por_n','die_id','static_setup_ready','link_up'):
   bits=1 if not w else abs(ports.widths[p][0]-ports.widths[p][1])+1
   rand += [f'for(integer k=0;k<{bits};k=k+1)'+(p+'[k]' if w else p)+'=$random(seed)&1;']
 else:
  decl+=['wire '+w+'a_'+p+',b_'+p+';'];ca+=['.'+p+'(a_'+p+')'];cb+=['.'+p+'(b_'+p+')'];outs+=[p]
decl += [top+' a('+','.join(ca)+');',top2+' b('+','.join(cb)+');','initial begin','if($value$plusargs("seed=%d",seed))begin end','die_id=3\'(seed%8);static_setup_ready=1;link_up=3;','repeat(20000)begin','@(negedge ck_core);','u_rank__u_control__por_n=(n>=12 && !(n>=1000&&n<1012));',*rand,'@(posedge ck_core);#1;','if(n>20)begin']
for p in outs:decl += ['if(a_'+p+'!==b_'+p+')$fatal(1,"PROMPT_N32 FAIL port='+p+' cycle=%0d",n);']
decl += ['end','n=n+1;end','$display("PROMPT_N32 PASS cycles=%0d seed=%0d",n,seed);$finish;end','endmodule']
Path('exact_tb.sv').write_text('\n'.join(decl)+'\n')
# Build independent candidate mutation through a macro on the one output assignment.
orig=Path(top2+'.sv').read_text();pat=r'(^\s*assign record_tx_v = )(.*?);';match=re.search(pat,orig,re.M);assert match
mut=orig[:match.start()]+f'`ifdef OT_PROMPT_N32_MUTANT\n{match.group(1)}~({match.group(2)});\n`else\n{match.group()}\n`endif'+orig[match.end():]
Path('candidate_sim.sv').write_text(mut)
base=['verilator','--binary','--timing','-j','4','-Wno-fatal','-Wno-lint','-Wno-style','--output-split','10000','--top-module','tb','exact_tb.sv','original.v','candidate_sim.sv','cell_models.v','ot_sram_1r1w_1024x256_m2_r2c2.v','ot_sram_1rw_256x64_m4_r2c2.v','ot_sram_1r1w_32x546_m1_p192_mir.v']
for mode in ['pass','mutant']:
 cmd=base+(['-DOT_PROMPT_N32_MUTANT']if mode=='mutant'else[])+['-Mdir','obj_'+mode]
 with Path('exact_'+mode+'.build.log').open('w')as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
 for seed in ([251,523,997,2001,4003,8009]if mode=='pass'else[251]):
  p=Path(f'exact_{mode}_{seed}.log')
  with p.open('w')as f:run=subprocess.run(['./obj_'+mode+'/Vtb',f'+seed={seed}'],stdout=f,stderr=subprocess.STDOUT)
  t=p.read_text();print(t[-1000:],flush=True)
  assert (run.returncode==0 and 'PROMPT_N32 PASS'in t) if mode=='pass'else(run.returncode!=0 and 'PROMPT_N32 FAIL'in t)
print('PROMPT_N32_EXACT_SUITE PASS 6 seeds 120000 cycles 1 causal mutant',flush=True)
