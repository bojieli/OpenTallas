#!/usr/bin/env python3
"""Randomized original/COPY0 relation, independent new copies, complete real SRAM state."""
from pathlib import Path
import importlib.util,json,re,subprocess,sys
sp=importlib.util.spec_from_file_location('tl','textbook_lint.py');m=importlib.util.module_from_spec(sp);sys.modules['tl']=m;sp.loader.exec_module(m)
mods=m.parse_verilog(Path('guard_original.v').read_text());g,top=m.flatten(mods,None);ports=mods[top]
top2=sys.argv[1]if len(sys.argv)>1 else'qkd_hr_core_prompt_n32';decl=['`timescale 1ns/1ps','module tb;','integer seed=251;integer n=0;integer visible_diffs=0;','reg ck_core=0;always #5 ck_core=~ck_core;']
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
variant=sys.argv[2] if len(sys.argv)>2 else 'exact'
assert variant in ('exact','missing','inverted','late')
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
hold_checks=[]
hold_decls=[]
access_checks=[]
for row in record['macros']:
 a='a.\\'+row['original']+' ';b='b.'+row['instance']
 idx=len(hold_decls)//2
 hold_decls += [f'reg [$bits({a}.arr[0])-1:0] init_arr_{idx}[0:$size({a}.arr)-1];',f'reg [$bits({a}.rd_out)-1:0] init_rd_{idx};']
 init += [f'for(integer r=0;r<$size({a}.arr);r++)init_arr_{idx}[r]={a}.arr[r];'] if False else []
 init += [f'for(integer r=0;r<$size({a}.arr);r++)begin',f'for(integer k=0;k<$bits({a}.arr[0]);k++){a}.arr[r][k]=$random(seed)&1;',f'{b}.arr[r]={a}.arr[r];','end',f'for(integer k=0;k<$bits({a}.rd_out);k++){a}.rd_out[k]=$random(seed)&1;',f'{b}.rd_out={a}.rd_out;']
 init += [f'for(integer r=0;r<$size({a}.arr);r++)init_arr_{idx}[r]={a}.arr[r];',f'init_rd_{idx}={a}.rd_out;']
 hold_checks += [f'for(integer r=0;r<$size({a}.arr);r++)if({a}.arr[r]!==init_arr_{idx}[r] || {b}.arr[r]!==init_arr_{idx}[r])$fatal(1,"GUARD_HOLD_FAIL arr macro{idx} row=%0d",r);',f'if({a}.rd_out!==init_rd_{idx} || {b}.rd_out!==init_rd_{idx})$fatal(1,"GUARD_HOLD_FAIL rd_out macro{idx}");']
 pins=['ce_in'] if row['type'].startswith('ot_sram_1rw_') else ['r_ce_in','w_ce_in']
 for pin in pins:access_checks += [f'if({a}.{pin}!==0 || {b}.{pin}!==0)$fatal(1,"GUARD_ACCESS_FAIL macro{idx} {pin} firstedge=%0t",$time);']
 state_checks += [f'for(integer r=0;r<$size({a}.arr);r++)if({a}.arr[r]!=={b}.arr[r])$fatal(1,"PROMPT_STATE FAIL macro_arr {row["instance"]} cycle=%0d row=%0d",n,r);',f'if({a}.rd_out!=={b}.rd_out)$fatal(1,"PROMPT_STATE FAIL macro_rd_out {row["instance"]} cycle=%0d",n);']
init += state_checks + ['#1;u_rank__u_control__por_n=0;']
Path('guard_trace_relation_'+variant+'.json').write_text(json.dumps(dict(original_copy0_explicit_aligned_ff=ff_count,original_random_ff=80,original_explicit_zero_ff=ff_count-80,independent_new_ff=True,macro_pairs=len(record['macros']),complete_array_and_read_output=True,repair_after_initialization=False,ff_chunk_size=128,complete_original_ff_inventory=True),indent=2))
decl += hold_decls + blocks
decl += [top+' a('+','.join(ca)+');',top2+' b('+','.join(cb)+');','initial begin','if($value$plusargs("seed=%d",seed))begin end','die_id=3\'(seed%8);static_setup_ready=1;link_up=3;',*init,'repeat(100)begin','@(negedge ck_core);','u_rank__u_control__por_n=(n>=12 && !(n>=1000&&n<1012));',*rand,'@(posedge ck_core);#1;','if(n>20)begin',*state_checks]
for p in outs:decl += ['if(a_'+p+'!==b_'+p+')$fatal(1,"PROMPT_N32 FAIL port='+p+' cycle=%0d",n);']
decl += ['end','n=n+1;end','if(visible_diffs!=0)$fatal(1,"GUARD_VISIBLE_FAIL count=%0d",visible_diffs);','$display("PROMPT_N32 PASS cycles=%0d seed=%0d",n,seed);$finish;end','endmodule']
# Diagnose root landing, independently added copies, and fault endpoint FFs.
analysis=m.build(g,None)
leaves=set()
def leaves_of(net,seen):
 net=g.find(net)
 if net in seen:return
 seen.add(net)
 for ci,pin in [analysis['driver'].get(net,(-1,None))]:
  if ci<0:continue
  if analysis['kind'][ci]=='ff':leaves.add(ci)
  elif analysis['kind'][ci]=='comb' or analysis['kind'][ci]=='buf':
   for p,bits in g.cells[ci][2].items():
    if analysis['pin_dir'][ci].get(p)=='in':
     for x in bits:leaves_of(x,seen)
for port in ['package_abort','record_fault','source_cr','available','u_rank__source_fault','u_rank__begin_fault','u_rank__u_control__begin_v','u_rank__u_control__startup_allowed','u_rank__u_control__cmd_v']:
 leaves_of(g.ports[port][1],set())
watched=sorted(leaves|{r['cell']for r in record['copied_cells']if r['kind']=='ff'})
Path('guard_trace_cones.json').write_text(json.dumps([dict(cell=ci,type=g.cells[ci][0],original=g.cells[ci][1],copies=copy_rows.get(ci,{}).get('copies',1),pins={p:[g.net_name[g.find(x)] for x in bits]for p,bits in g.cells[ci][2].items()})for ci in watched],indent=2))
diag=['always @(posedge ck_core)begin','#0.03;if($time<36)begin']
for ci in watched:
 typ,name,pins=g.cells[ci];a='a.\\'+name+' ';b=f'b.u{ci}_c0.u_cell'
 reset='RESETN'if 'RESETN'in pins else None
 copies=copy_rows.get(ci,{}).get('copies',1)
 for k in range(copies):
  c=f'b.u{ci}_c{k}.u_cell'
  resetargs=f'{a}.RESETN,{b}.RESETN,{c}.RESETN'if reset else "1'b1,1'b1,1'b1"
  diag += [f'$display("ROOT_TRACE t=%0t cell={ci} copy={k} QN gold/c0/ck=%b/%b/%b D=%b/%b/%b RESETN=%b/%b/%b",$time,{a}.QN,{b}.QN,{c}.QN,{a}.D,{b}.D,{c}.D,{resetargs});']
diag+=['$display("VALID_CONTEXT t=%0t por=%b record_v=%b/%b ht=%b/%b htcredit=%b cmd_v=%b/%b hc_start=%b/%b",$time,u_rank__u_control__por_n,a_record_tx_v,b_record_tx_v,a_u_rank__u_control__u_packet__ht,b_u_rank__u_control__u_packet__ht,u_rank__u_control__u_packet__htc,a_u_rank__u_control__cmd_v,b_u_rank__u_control__cmd_v,a_hc[38],b_hc[38]);','end end']
decl[-1:-1]=diag
trace=['always @(posedge ck_core) begin','if(!u_rank__u_control__por_n)begin',*access_checks,'#0.01;',*hold_checks,'end']
for row in record['macros']:
 a='a.\\'+row['original']+' ';b='b.'+row['instance']
 if row['type'].startswith('ot_sram_1rw'):
  pins=['ce_in','we_in','addr_in','wd_in','w_mask_in']
 else:pins=['w_ce_in','w_addr_in','wd_in','w_mask_in','r_ce_in','r_addr_in']
 # Report actual pin inventory mismatch rather than assuming write controls.
 for pin in pins:
  trace += [f'if({a}.{pin}!=={b}.{pin})$display("BOOT_PIN_DIFF n=%0d time=%0t macro={row["instance"]} pin={pin} a=%h b=%h",n,$time,{a}.{pin},{b}.{pin});']
trace+=['end']
visible=['always @(posedge ck_core) begin','#0.02;']
for port in outs:
 visible += ['if(a_'+port+'!==b_'+port+')begin visible_diffs=visible_diffs+1;$display("GUARD_VISIBLE_DIFF reset=%b n=%0d port='+port+' a=%h b=%h",u_rank__u_control__por_n,n,a_'+port+',b_'+port+');end']
visible+=['end']
decl[-1:-1]=visible

decl[-1:-1]=trace
Path('guard_trace_tb.sv').write_text('\n'.join(decl)+'\n')
# Build independent candidate mutation through a macro on the one output assignment.
orig=Path(top2+'.sv').read_text()
clamp='u_raw_por_mem_1_w_ce_in (.A(u_rank__u_control__por_n)'
assert clamp in orig
if variant=='missing':orig=orig.replace(clamp,"u_raw_por_mem_1_w_ce_in (.A(1'b1)")
if variant=='inverted':orig=orig.replace(clamp,'u_raw_por_mem_1_w_ce_in (.A(~u_rank__u_control__por_n)')
if variant=='late':
 orig=orig.replace(clamp,'u_raw_por_mem_1_w_ce_in (.A(late_por_q)')
 pos=orig.index('\nendmodule');orig=orig[:pos]+"\nreg late_por_q=1'b1; always @(posedge ck_core)late_por_q<=u_rank__u_control__por_n;\n"+orig[pos:]
pat=r'(^\s*assign record_tx\[0\] = )(.*?);';match=re.search(pat,orig,re.M);assert match
mut=orig[:match.start()]+f'`ifdef OT_PROMPT_N32_MUTANT\n{match.group(1)}({match.group(2)}) ^ 1;\n`else\n{match.group()}\n`endif'+orig[match.end():]
Path('guard_candidate_sim_'+variant+'.sv').write_text(mut)
base=['verilator','--binary','--timing','-DOT_MEM_NO_INIT','-j','4','-Wno-fatal','-Wno-lint','-Wno-style','--output-split','10000','--output-split-cfuncs','256','--top-module','tb','guard_trace_tb.sv','guard_original.v','guard_candidate_sim_'+variant+'.sv','cell_models.v','ot_sram_1r1w_1024x256_m2_r2c2.v','ot_sram_1rw_256x64_m4_r2c2.v','ot_sram_1r1w_32x546_m1_p192_mir.v']
for mode in ['pass']:
 cmd=base+(['-DOT_PROMPT_N32_MUTANT']if mode=='mutant'else[])+['-Mdir','obj_guard_trace_'+mode]
 with Path('guard_trace_'+variant+'_'+mode+'.build.log').open('w')as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
 for seed in ([997]if mode=='pass'else[251]):
  p=Path(f'guard_trace_{mode}_{seed}.log')
  with p.open('w')as f:run=subprocess.run(['./obj_guard_trace_'+mode+'/Vtb',f'+seed={seed}'],stdout=f,stderr=subprocess.STDOUT)
  t=p.read_text();print(t[-1000:],flush=True)
  assert (run.returncode==0 and 'PROMPT_N32 PASS'in t) if variant=='exact' else (run.returncode!=0 and ('GUARD_ACCESS_FAIL'in t or 'GUARD_HOLD_FAIL'in t))
print('GUARD_PROBE expected verdict confirmed variant='+variant+' 1seed100cycles',flush=True)
