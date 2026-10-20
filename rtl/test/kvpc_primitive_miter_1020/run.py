#!/usr/bin/env python3
"""Fleet-only actual mapped vs structural primitive copy lifecycle miter. Source inputs are immutable external paths."""
import argparse,hashlib,json,re,subprocess,importlib.util,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--diag',action='store_true');p.add_argument('--inputs',type=Path,required=True);p.add_argument('--models',type=Path,required=True);p.add_argument('--macro',type=Path,required=True);p.add_argument('--parser',type=Path,required=True);p.add_argument('--top',choices=['qkd_kvs_pc','qkd_kvs_pc_h'],required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--edges',type=int,default=20000);p.add_argument('--threads',type=int,default=8);a=p.parse_args()
a.out.mkdir(parents=True,exist_ok=True);o=a.out.resolve();src=a.inputs/a.top
original=src/'original.v';candidate=src/(a.top+'_n32.sv');text=candidate.read_text()
P=[(n,d,int(w)+1 if w else 1) for d,w,n in re.findall(r'^  (input|output) wire (?:\[(\d+):0\] )?(\w+);',text[:text.index("endmodule")],re.M)]
assert P and len(P)>25
ins=[(n,w) for n,d,w in P if d=='input' and n not in ['ck','hck','rst_n','hrst_n']];outs=[(n,w) for n,d,w in P if d=='output']
L=['`timescale 1ps/1fs','module tb;','reg ck=0,hck=0,run_ck=1,run_hck=1; always #417 if(run_ck) ck=~ck; initial begin #0.3;forever #512 if(run_hck) hck=~hck;end','reg rst_n=1,hrst_n=1; integer mut=0,t=0,seed=1,dummy,checks=0,er_v=0,her_v=0,reset_checks=0; reg compare_on=0; wire dut_rst_n=rst_n && !(mut==2 && t>=1000 && t<1008);']
for n,w in ins:L.append(f'reg [{w-1}:0] {n}=0;')
for n,w in outs:L.append(f'wire [{w-1}:0] r_{n},d_{n};')
for name,pre in [(a.top,'r_'),(a.top+'_n32','d_')]:
 conn=', '.join(f'.{n}({pre+n if d=="output" else "dut_rst_n" if pre=="d_" and n=="rst_n" else n})' for n,d,w in P)
 L.append(f'{name} {"u_ref" if pre=="r_" else "u_dut"} ({conn});')
L+=['task compare; begin','checks++; if(r_pc__er[0])er_v++;if(r_pc__her[0])her_v++;if(!rst_n||!hrst_n)reset_checks++;']
for n,w in outs:
 rhs=f'd_{n}';rhs=f'(d_{n} ^ {w}\'(mut==1))' if n=='pc__fo' else rhs
 if n in ['pc__er','pc__her']:
  cond=f'(r_{n}[0] !== {rhs}[0]) || (r_{n}[260:259] !== {rhs}[260:259]) || (r_{n}[0] && (r_{n}[258:1] !== {rhs}[258:1]))'
 else:cond=f'r_{n} !== {rhs}'
 L.append(f'if({cond})$fatal(1,"KVPC_PRIMITIVE FAIL top={a.top} mut=%0d t=%0d out={n} ref=%h dut=%h rst=%b/%b",mut,t,r_{n},d_{n},rst_n,hrst_n);')
L+=['end endtask','always @(negedge ck) begin #0.01;if(compare_on)compare;end','always @(negedge hck) begin #0.02;if(compare_on)compare;end','initial begin','dummy=$value$plusargs("mut=%d",mut);dummy=$value$plusargs("seed=%d",seed);dummy=$urandom(seed);']
for n,w in ins:
 if n=='pc__pc':L.append(f'{n}=5\'d9;')
 elif n=='pc__cfg_stack':L.append(f'{n}=2\'d2;')
L+=['#0.01;rst_n=0;hrst_n=0;repeat(12)@(negedge ck); compare_on=1; rst_n=1;hrst_n=1;',f'for(t=0;t<{a.edges};t++)begin @(negedge ck);#0.05;']
for n,w in ins:
 if n not in ['pc__pc','pc__cfg_stack']:
  expr='{'+','.join(['$urandom']*((w+31)//32))+'}';L.append(f'{n}={w}\'({expr});')
# Identical independently asserted/released domains; comparison remains enabled through resets and stopped clocks.
L+=['if(t==4000)rst_n=0;if(t==4006)rst_n=1;','if(t==7000)hrst_n=0;if(t==7008)hrst_n=1;','if(t==10000)begin run_hck=0;hrst_n=0;end if(t==10010)hrst_n=1;if(t==10020)run_hck=1;','if(t==13000)begin rst_n=0;hrst_n=0;end if(t==13008)begin rst_n=1;hrst_n=1;end','end',f'if(er_v==0||her_v==0||reset_checks==0)$fatal(1,"KVPC_PRIMITIVE FAIL coverage er=%0d her=%0d reset=%0d",er_v,her_v,reset_checks);',f'$display("KVPC_PRIMITIVE PASS top={a.top} mut=%0d checks=%0d er=%0d her=%0d resetchecks=%0d",mut,checks,er_v,her_v,reset_checks);$finish;end','endmodule']
# The transform preserves each architectural SRAM bank; use common arbitrary corresponding words.
# This is a state-correspondence miter, not an independent-memory-initialization theorem.
meta=json.loads((src/(a.top+'_n32.json')).read_text())
init=['integer power_row; integer independent_copy_diffs=0; reg[63:0] power_word; initial begin #0.001;']
for bank in meta['macros']:
 assert bank['type']=='ot_sram_1r1w2c_32x64_m1',bank
 ref='u_ref.'+chr(92)+bank['original']+' .arr[power_row]'
 dut='u_dut.'+bank['instance']+'.arr[power_row]'
 init.append('for(power_row=0;power_row<32;power_row++)begin power_word={$urandom,$urandom}; '+ref+'=power_word; '+dut+'=power_word; end')
 init.append('power_word={$urandom,$urandom}; '+ref.removesuffix('.arr[power_row]')+'.rd_out=power_word; '+dut.removesuffix('.arr[power_row]')+'.rd_out=power_word;')
spec=importlib.util.spec_from_file_location('miter_source_parser',a.parser)
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
assert hashlib.sha256(a.parser.read_bytes()).hexdigest()==meta['parser_sha256']
g,_=m.flatten(m.parse_verilog(original.read_text()),None);analysis=m.build(g,None)
state_rows=[]
for ci,(typ,name,pins) in enumerate(g.cells):
 if analysis['kind'][ci]!='ff':continue
 assert typ in ['DFFHQNx1_ASAP7_75t_R','DFFASRHQNx1_ASAP7_75t_R'],typ
 ref='u_ref.'+chr(92)+name+' .QN';dut=f'u_dut.u{ci}_c0.u_cell.QN'
 init.append('power_word={$urandom,$urandom}; '+ref+'=power_word[0]; '+dut+'=power_word[0];')
 state_rows.append({'original':name,'copy0':f'u{ci}_c0.u_cell','type':typ})
new_ff_copies=0
for row in meta['copied_cells']:
 if row['kind']!='ff':continue
 for k in range(1,row['copies']):
  ci=row['cell'];new_ff_copies+=1
  init.append(f'power_word={{$urandom,$urandom}};u_dut.u{ci}_c{k}.u_cell.QN=power_word[0]; independent_copy_diffs+=(u_dut.u{ci}_c{k}.u_cell.QN !== u_dut.u{ci}_c0.u_cell.QN);')
init.append(f'$display("KVPC_POWERUP retained_ff={len(state_rows)} SRAMs={len(meta["macros"])} new_ff={new_ff_copies} independent_diffs=%0d",independent_copy_diffs);')
init.append('if(independent_copy_diffs==0)$fatal(1,"KVPC_POWERUP FAIL no independent new-copy state observed");')
(o/'state_bijection.json').write_text(json.dumps({'macros':meta['macros'],'macro_state':['arr[0:31] each64bits','registered rd_out64bits'],'retained_ff':state_rows,'new_copies':'independent per-new-copy $urandom draws before reset; never aliased to master'},indent=2)+'\n')
if a.diag:
 audit=['integer audit_prints=0; integer audit_f,audit_m,audit_q,audit_row;task state_audit(input integer phase);begin audit_f=0;audit_m=0;audit_q=0;']
 for row in state_rows:
  ref='u_ref.'+chr(92)+row['original']+' ';dut='u_dut.'+row['copy0']
  audit.append(f'if({ref}.QN !== {dut}.QN)begin audit_f++;if(audit_prints<16)begin audit_prints++;$display("KVPC_ARCH_DIFF phase=%0d time=%0t ci={row["copy0"]} refQ/D/CLK=%b/%b/%b dutQ/D/CLK=%b/%b/%b",phase,$time,{ref}.QN,{ref}.D,{ref}.CLK,{dut}.QN,{dut}.D,{dut}.CLK);end end')
 for bank in meta['macros']:
  ref='u_ref.'+chr(92)+bank['original']+' ';dut='u_dut.'+bank['instance']
  audit.append(f'for(audit_row=0;audit_row<32;audit_row++)if({ref}.arr[audit_row] !== {dut}.arr[audit_row])audit_m++;if({ref}.rd_out !== {dut}.rd_out)audit_q++;')
 audit.append('$display("KVPC_STATE_AUDIT phase=%0d time=%0t t=%0d ff=%0d memwords=%0d readregs=%0d",phase,$time,t,audit_f,audit_m,audit_q);if(phase==0 && (audit_f||audit_m||audit_q))$fatal(1,"KVPC_STATE_RELATION FAIL initial architectural state differs");end endtask')
 audit.append('always @(posedge ck or posedge hck)begin #0.002;if(t<8)state_audit(1);end')
 L[-1:-1]=audit
 init.append('state_audit(0);')
init.append('end')
L[-1:-1]=init
trace=['always @(negedge ck or negedge hck) if(t<8)begin']
for row in meta['copied_cells']:
 if row['kind']!='ff':continue
 ci=row['cell'];suffixes=['D','CLK','QN']+(['RESETN','SETN'] if row['type']=='DFFASRHQNx1_ASAP7_75t_R' else [])
 exprs=[f'u_dut.u{ci}_c{k}.u_cell.{pin}' for k in [0,1] for pin in suffixes]
 trace.append('$display("KVPC_COPY_STATE ci='+str(ci)+' time=%0t t=%0d rst=%b/%b c0/c1_'+','.join(suffixes)+'='+','.join(['%b']*len(exprs))+'",$time,t,rst_n,hrst_n,'+','.join(exprs)+');')
trace.append('end');L[-1:-1]=trace
(o/'tb.sv').write_text('\n'.join(L)+'\n')
# Actual SRAM write-data bank permutation only inside the candidate primitive wrapper; runtime-controlled causal mutant.
assert text.count('.wd_in(wd_in)')==1
text=text.replace('.wd_in(wd_in)','.wd_in(tb.mut==3 ? {wd_in[55:0],wd_in[63:56]} : wd_in)')
# A separate late enabled mutant swaps two entire 64-bit macro read banks.
bus=[]
for index,bank in enumerate(meta['macros'][:2]):
 instance=bank['instance'].removesuffix('.u_cell')
 pattern=r'(?m)^  \w+ '+re.escape(instance)+r' \([^\n]+\);$'
 match=re.search(pattern,text);assert match,instance
 line=match.group();rd=re.search(r'\.rd_out\(([^)]+)\)',line);assert rd
 bus.append(rd.group(1));new=line[:rd.start(1)]+f'miter_bank{index}'+line[rd.end(1):]
 text=text[:match.start()]+new+text[match.end():]
insert='wire[63:0] miter_bank0,miter_bank1;\n'+''.join(f'assign {value}=(tb.mut==4 && tb.t>=200)?miter_bank{1-index}:miter_bank{index};\n' for index,value in enumerate(bus))
text=text.replace('endmodule',insert+'endmodule',1)
(o/'candidate_test.sv').write_text(text)
files=[original,o/'candidate_test.sv',a.models/'comb_models.v',a.models/'canonical_ASR_normalized.v',a.models/'canonical_DFF_normalized.v',a.macro,o/'tb.sv']
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
(o/'inputs.json').write_text(json.dumps({str(f):sha(f) for f in files+[candidate,a.parser,src/(a.top+'_n32.json')]},indent=2)+'\n')
ver=Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
cmd=[str(ver),'--binary','--timing','--x-initial','unique','--x-assign','unique','-DOT_MEM_NO_INIT','-Wno-fatal','-Wno-MULTIDRIVEN','-Wno-TIMESCALEMOD','-Wno-UNOPTFLAT','--top-module','tb','-j',str(a.threads),'--output-split','10000','--output-split-cfuncs','100','--Mdir',str(o/'obj'),'-o','sim']+[str(f) for f in files]
(o/'command.json').write_text(json.dumps(cmd,indent=2)+'\n')
with (o/'build.log').open('w') as log:rc=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT).returncode
if rc:raise SystemExit(rc)
results={}
for mut,seed in ([(0,11)] if a.diag else [(0,11),(0,29),(1,11),(2,11),(3,11),(4,11)]):
 name=f'm{mut}_s{seed}';log=o/(name+'.log')
 with log.open('w')as f:run=subprocess.run([str(o/'obj/sim'),f'+mut={mut}',f'+seed={seed}',f'+verilator+seed+{seed}','+verilator+rand+reset+2'],stdout=f,stderr=subprocess.STDOUT)
 s=log.read_text();expected='KVPC_PRIMITIVE PASS' if mut==0 else 'KVPC_PRIMITIVE FAIL top='+a.top
 results[name]={'rc':run.returncode,'expected':expected,'witness':str(log),'pass':(expected in s and ((run.returncode==0)==(mut==0)))}
 print(name,results[name],flush=True)
(o/'results.json').write_text(json.dumps(results,indent=2)+'\n')
raise SystemExit(0 if all(x['pass'] for x in results.values())else 1)
