from pathlib import Path
import json,subprocess,concurrent.futures,re
R=Path.cwd();C=json.load(open(R/'contract.json'));profiles=C['profiles']
p0,p1=profiles['0'],profiles['1']
ref=f"""module ref_bank #(parameter integer PROFILE=0, TD=0, ED=0)
(input wire clk,input wire[17:0]tok_i,input wire[15:0]epoch_i,output wire[17:0]tok_o,output wire[15:0]epoch_o);
localparam integer TM=(PROFILE==1)?{p1['tok_max']}:{p0['tok_max']};
localparam integer EM=(PROFILE==1)?{p1['epoch_max']}:{p0['epoch_max']};
generate
 if(TM>0)begin:gt
  (* keep=1 *)reg[17:0]pipe[0:TM-1];
  for(genvar j=0;j<TM;j=j+1)begin:r
   if(j==0)always@(posedge clk)pipe[j]<=tok_i;
   else always@(posedge clk)pipe[j]<=pipe[j-1];
  end
  assign tok_o=(TD==0)?tok_i:pipe[TD-1];
 end else assign tok_o=tok_i;
 if(EM>0)begin:ge
  (* keep=1 *)reg[15:0]pipe[0:EM-1];
  for(genvar j=0;j<EM;j=j+1)begin:r
   if(j==0)always@(posedge clk)pipe[j]<=epoch_i;
   else always@(posedge clk)pipe[j]<=pipe[j-1];
  end
  assign epoch_o=(ED==0)?epoch_i:pipe[ED-1];
 end else assign epoch_o=epoch_i;
endgenerate
endmodule
module gold #(parameter integer PROFILE=0,TD=0,ED=0)
(input wire clk,input wire[17:0]tok_i,input wire[15:0]epoch_i,output wire[17:0]tok_o,output wire[15:0]epoch_o);
ref_bank #(.PROFILE(PROFILE),.TD(TD),.ED(ED))u_bank(.*);
endmodule
module gate #(parameter integer PROFILE=0,STACK=0,GROUP=0,MUT=0)
(input wire clk,input wire[17:0]tok_i,input wire[15:0]epoch_i,output wire[17:0]tok_o,output wire[15:0]epoch_o);
kv_pc_r8_position_bank_v2 #(.PROFILE(PROFILE),.MUT(MUT))u_bank(.clk(clk),.stack_id(STACK[1:0]),.group_id(GROUP[2:0]),.tok_i(tok_i),.epoch_i(epoch_i),.tok_o(tok_o),.epoch_o(epoch_o));
endmodule
"""
(R/'reference.sv').write_text(ref)
def run(v,mut=0):
 tag=f"s{v['stack']}g{v['group']}p{v['profile']}"+('_mut' if mut else '')
 script=f"read_verilog -sv /work/bank.sv /work/reference.sv; chparam -set PROFILE {v['profile']} -set TD {v['tok']} -set ED {v['epoch']} gold; chparam -set PROFILE {v['profile']} -set STACK {v['stack']} -set GROUP {v['group']} -set MUT {mut} gate; hierarchy -check; proc; memory_map; setattr -mod -unset keep_hierarchy; flatten gold gate; opt_clean; equiv_make gold gate equiv; hierarchy -top equiv; equiv_simple -seq 2; equiv_induct -seq 12; equiv_status -assert"
 cmd=['docker','run','--rm','--memory=3g','--cpus=1','-v',str(R)+':/work','-w','/work','openroad/orfs:asap7lock','bash','-lc','source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; exec yosys -Q -T -p "$1"','bash',script]
 r=subprocess.run(cmd,capture_output=True,text=True);log=r.stdout+r.stderr
 (R/(tag+'.log')).write_text(log)
 good=(r.returncode==0 and 'Equivalence successfully proven' in log) if not mut else (r.returncode!=0 and 'No SAT model' not in log and bool(re.search(r'ERROR: Found [0-9]+ unproven .equiv cells',log)))
 result=dict(tag=tag,variant=v,mutant=bool(mut),returncode=r.returncode,pass_=good,tail=log.splitlines()[-3:]);print(json.dumps(result),flush=True);return result
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 results=list(pool.map(run,C['variants']))
victim=next(v for v in C['variants'] if (v['stack'],v['group'])==(C['mutant_position']['stack'],C['mutant_position']['group']))
results.append(run(victim,1))
# Exact 18-bit token +16-bit epoch model for every used physical position.
lines=['module tb;reg clk=0;always #5 clk=~clk;reg[17:0]tok=18\'h2acea;reg[15:0]epoch=16\'h29c1;reg[17:0]th[0:15];reg[15:0]eh[0:15];integer i,cyc=0;',
'always@(posedge clk)begin th[0]<=tok;eh[0]<=epoch;for(i=1;i<16;i=i+1)begin th[i]<=th[i-1];eh[i]<=eh[i-1];end end']
checks=[]
for n,v in enumerate(C['variants']):
 lines.append(f"wire[17:0]t{n};wire[15:0]e{n};kv_pc_r8_position_bank_v2 #(.PROFILE({v['profile']}),.MUT(MODELMUT))u{n}(.clk(clk),.stack_id(2'd{v['stack']}),.group_id(3'd{v['group']}),.tok_i(tok),.epoch_i(epoch),.tok_o(t{n}),.epoch_o(e{n}));")
 td='tok' if v['tok']==0 else f"th[{v['tok']-1}]";ed='epoch' if v['epoch']==0 else f"eh[{v['epoch']-1}]"
 checks.append(f'if(t{n}!=={td} || e{n}!=={ed})$fatal(1,"POSITION_{n}_WORD_MISMATCH");')
lines += ['always@(negedge clk)begin cyc=cyc+1;tok={tok[16:0],tok[17]^tok[10]^tok[2]^tok[0]};epoch={epoch[14:0],epoch[15]^epoch[13]^epoch[12]^epoch[10]};#1;if(cyc>20)begin','\n'.join(checks),'end if(cyc==320)begin $display("ALL28_WORDS_300EDGES_PASS");$finish;end end endmodule']
tb='\n'.join(lines);models=[]
for mut in (0,1):
 src=R/f'model{mut}.sv';src.write_text(tb.replace('MODELMUT',str(mut)))
 binary=R/f'model{mut}'
 comp=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(binary),str(R/'bank.sv'),str(src)],capture_output=True,text=True)
 if comp.returncode: rr=comp
 else:rr=subprocess.run(['vvp',str(binary)],capture_output=True,text=True)
 (R/f'model{mut}.log').write_text(rr.stdout+rr.stderr)
 models.append(dict(mutant=bool(mut),returncode=rr.returncode,pass_=(rr.returncode==0 if mut==0 else rr.returncode!=0 and 'WORD_MISMATCH' in rr.stdout),output=rr.stdout.strip()))
out=dict(scope='Fresh optional component source LEC; every28usedstaticIDvariant, full max-capacity kept banks; not whole-die proof/adoption',positive=sum(x['pass_'] for x in results if not x['mutant']),used=28,mutant_caught=results[-1]['pass_'],models=models,results=results)
(R/'receipt.json').write_text(json.dumps(out,indent=1)+'\n')
raise SystemExit(0 if all(x['pass_'] for x in results+models) else 1)
