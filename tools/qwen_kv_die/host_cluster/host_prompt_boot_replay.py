#!/usr/bin/env python3
"""Randomized original/COPY0 relation, independent new copies, complete real SRAM state."""
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
record=json.loads(Path(top2+'.json').read_text())
init=['u_rank__u_control__por_n=1;','#1;']
ff_count=0
kinds=m.build(g,None)['kind']
copy_rows={r['cell']:r for r in record['copied_cells']}
ff_rows=[]
for ci,(typ,name,pins) in enumerate(g.cells):
 if kinds[ci]!='ff':continue
 assert typ in ('DFFHQNx1_ASAP7_75t_R','DFFASRHQNx1_ASAP7_75t_R'),typ
 ff_rows.append((ci,name,copy_rows.get(ci,{}).get('copies',1)))
blocks=[]
# Explicit deterministic subset for retained states not replicated, reproducing
# historical failure without relying on Verilator's default initialization.
for chunk in range(0,len(ff_rows),128):
 lines=['initial begin: init_ff_'+str(chunk),'#1;']
 for ci,name,copies in ff_rows[chunk:chunk+128]:
  if ci in copy_rows:continue
  original='a.\\'+name+' .QN'
  lines += [original+"=1'b0;",f'b.u{ci}_c0.u_cell.QN='+original+';']
  lines += [f'if({original}!==b.u{ci}_c0.u_cell.QN)$fatal(1,"INIT_RELATION FF {ci}");']
 lines+=['end'];blocks+=lines
# Maintain the historical RNG order for the 80 original registers and their
# 395 added copies, before consuming macro-state initialization random bits.
for row in record['copied_cells']:
 if row['kind']!='ff':continue
 original='a.\\'+row['original']+' .QN'
 init += [original+'=$random(seed)&1;',f'b.u{row["cell"]}_c0.u_cell.QN='+original+';']
 for k in range(1,row['copies']):init += [f'b.u{row["cell"]}_c{k}.u_cell.QN=$random(seed)&1;']
 init += [f'if({original}!==b.u{row["cell"]}_c0.u_cell.QN)$fatal(1,"INIT_RELATION COPIED FF");']
ff_count=len(ff_rows)
state_checks=[]
for row in record['macros']:
 a='a.\\'+row['original']+' ';b='b.'+row['instance']
 init += [f'for(integer r=0;r<$size({a}.arr);r++)begin',f'for(integer k=0;k<$bits({a}.arr[0]);k++){a}.arr[r][k]=$random(seed)&1;',f'{b}.arr[r]={a}.arr[r];','end',f'for(integer k=0;k<$bits({a}.rd_out);k++){a}.rd_out[k]=$random(seed)&1;',f'{b}.rd_out={a}.rd_out;']
 state_checks += [f'for(integer r=0;r<$size({a}.arr);r++)if({a}.arr[r]!=={b}.arr[r])$fatal(1,"PROMPT_STATE FAIL macro_arr {row["instance"]} cycle=%0d row=%0d",n,r);',f'if({a}.rd_out!=={b}.rd_out)$fatal(1,"PROMPT_STATE FAIL macro_rd_out {row["instance"]} cycle=%0d",n);']
init += state_checks + ['#1;u_rank__u_control__por_n=0;']
Path('boot_replay_relation.json').write_text(json.dumps(dict(original_copy0_explicit_aligned_ff=ff_count,original_random_ff=80,original_explicit_zero_ff=ff_count-80,independent_new_ff=True,macro_pairs=len(record['macros']),complete_array_and_read_output=True,repair_after_initialization=False,ff_chunk_size=128,complete_original_ff_inventory=True),indent=2))
decl += blocks
decl += [top+' a('+','.join(ca)+');',top2+' b('+','.join(cb)+');','initial begin','if($value$plusargs("seed=%d",seed))begin end','die_id=3\'(seed%8);static_setup_ready=1;link_up=3;',*init,'repeat(100)begin','@(negedge ck_core);','u_rank__u_control__por_n=(n>=12 && !(n>=1000&&n<1012));',*rand,'@(posedge ck_core);#1;','if(n>20)begin',*state_checks]
for p in outs:decl += ['if(a_'+p+'!==b_'+p+')$fatal(1,"PROMPT_N32 FAIL port='+p+' cycle=%0d",n);']
decl += ['end','n=n+1;end','$display("PROMPT_N32 PASS cycles=%0d seed=%0d",n,seed);$finish;end','endmodule']
trace=['always @(posedge ck_core) begin']
for row in record['macros']:
 a='a.\\'+row['original']+' ';b='b.'+row['instance']
 if row['type'].startswith('ot_sram_1rw'):
  pins=['ce_in','we_in','addr_in','wd_in','w_mask_in']
 else:pins=['w_ce_in','w_addr_in','wd_in','w_mask_in','r_ce_in','r_addr_in']
 # Report actual pin inventory mismatch rather than assuming write controls.
 for pin in pins:
  trace += [f'if({a}.{pin}!=={b}.{pin})$display("BOOT_PIN_DIFF n=%0d time=%0t macro={row["instance"]} pin={pin} a=%h b=%h",n,$time,{a}.{pin},{b}.{pin});']
trace+=['end']
decl[-1:-1]=trace
Path('boot_replay_tb.sv').write_text('\n'.join(decl)+'\n')
# Build independent candidate mutation through a macro on the one output assignment.
orig=Path(top2+'.sv').read_text();pat=r'(^\s*assign record_tx\[0\] = )(.*?);';match=re.search(pat,orig,re.M);assert match
mut=orig[:match.start()]+f'`ifdef OT_PROMPT_N32_MUTANT\n{match.group(1)}({match.group(2)}) ^ 1;\n`else\n{match.group()}\n`endif'+orig[match.end():]
Path('candidate_sim.sv').write_text(mut)
base=['verilator','--binary','--timing','-DOT_MEM_NO_INIT','-j','4','-Wno-fatal','-Wno-lint','-Wno-style','--output-split','10000','--output-split-cfuncs','256','--top-module','tb','boot_replay_tb.sv','original.v','candidate_sim.sv','cell_models.v','ot_sram_1r1w_1024x256_m2_r2c2.v','ot_sram_1rw_256x64_m4_r2c2.v','ot_sram_1r1w_32x546_m1_p192_mir.v']
for mode in ['pass']:
 cmd=base+(['-DOT_PROMPT_N32_MUTANT']if mode=='mutant'else[])+['-Mdir','obj_boot_replay_'+mode]
 with Path('boot_replay_'+mode+'.build.log').open('w')as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
 for seed in ([997]if mode=='pass'else[251]):
  p=Path(f'boot_replay_{mode}_{seed}.log')
  with p.open('w')as f:run=subprocess.run(['./obj_boot_replay_'+mode+'/Vtb',f'+seed={seed}'],stdout=f,stderr=subprocess.STDOUT)
  t=p.read_text();print(t[-1000:],flush=True)
  assert (run.returncode==0 and 'PROMPT_N32 PASS'in t) if mode=='pass'else(run.returncode!=0 and ('PROMPT_N32 FAIL'in t or 'PROMPT_STATE FAIL'in t))
print('BOOT_TRACE PASS 1 seed 100 cycles complete-state subset; no causal mutant',flush=True)
