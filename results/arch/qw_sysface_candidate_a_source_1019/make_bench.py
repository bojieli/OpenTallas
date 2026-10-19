from pathlib import Path
import re
p=Path(__file__).parent
states=[('accepted_v',1),('host_epoch_valid',1),('host_tag',59),('host_gen',2),('host_fusedcap',1),('host_image_epoch',16),('host_image_digest',64),('fault',1)]
ins=[('receive_slot',1),('rx_v',1),('rx_record',548),('program_begin_v',1),('program_ready',1),('installed_fusedcap',1),('program_epoch',16),('program_digest',64),('head_context_v',1),('head_stage',6),('head_token',18),('head_position',18),('native_active',1)]
cat=lambda names:'{'+','.join(names)+'}'
statecat=cat([s for s,w in states]);outcat=cat([s for s,w in states]+['host_epoch'])
ports=ins+[('rst_n',1),('ck',1)]
decl=lambda name,w:f'[{w-1}:0] {name}' if w>1 else name
b='`timescale 1ns/1ps\nmodule tb;\n'+''.join('reg '+decl(n,w)+';\n' for n,w in ports)
b+='wire [160:0] old_out,new_out; reg [144:0] state; integer cases=0, i,j,k,seed=32\'h19a019a0; reg [676:0] inputs;\n'
for inst,mod in [('a','qfd_host_native_context_rx'),('b','qfd_host_native_context_rx_candidate_a')]:
 b+='wire '+decl(inst+'_'+n,w)+';\n' if False else ''
 b+=''.join('wire '+decl(inst+'_'+n,w)+';\n' for n,w in states+[('host_epoch',16)])
 b+=mod+' '+inst+'('+','.join('.'+n+'('+n+')' for n,w in ports)+','+','.join('.'+n+'('+inst+'_'+n+')' for n,w in states+[('host_epoch',16)])+');\n'
 b+='assign '+('old_out' if inst=='a' else 'new_out')+'='+cat([inst+'_'+n for n,w in states]+[inst+'_host_epoch'])+';\n'
b+='task check; begin #1; if(old_out !== new_out) begin $display("DUT_MISMATCH case=%0d inputs=%h state=%h old=%h new=%h",cases,inputs,state,old_out,new_out); $fatal(1); end end endtask\n'
b+='task deposit; begin\n'+''.join(cat([inst+'.'+n for n,w in states])+'=state;\n' for inst in ['a','b'])+'end endtask\n'
b+='task step; begin ck=0; '+cat([n for n,w in ins])+'=inputs; deposit; #1; ck=1; check; ck=0; cases=cases+1; end endtask\n'
b+='task base; begin rst_n=1; ck=0; receive_slot=1; rx_v=1; rx_record=0; program_begin_v=0; program_ready=1; installed_fusedcap=1; program_epoch=16\'h1234; program_digest=64\'habcdef0123456789; head_context_v=0; head_stage=1; head_token=42; head_position=7; native_active=0; rx_record[542:539]=12; rx_record[538:533]=63; rx_record[532:517]=program_epoch; rx_record[58:43]=program_epoch; rx_record[36:19]=42; rx_record[18:6]=7; rx_record[61]=1; rx_record[77:62]=program_epoch; rx_record[141:78]=program_digest; state={1\'b0,1\'b1,rx_record[58:0],2\'b0,1\'b1,program_epoch,program_digest,1\'b0}; inputs='+cat([n for n,w in ins])+'; end endtask\n'
b+='initial begin\nbase; step;\n'
# systematic every input bit 0/1/X/Z, every state bit 0/1/X/Z, all head stages
b+='for(i=0;i<677;i=i+1) for(j=0;j<4;j=j+1) begin base; case(j) 0:inputs[i]=0; 1:inputs[i]=1; 2:inputs[i]=1\'bx; 3:inputs[i]=1\'bz; endcase step; end\n'
b+='for(i=0;i<145;i=i+1) for(j=0;j<4;j=j+1) begin base; case(j) 0:state[i]=0; 1:state[i]=1; 2:state[i]=1\'bx; 3:state[i]=1\'bz; endcase step; end\n'
b+='for(i=0;i<64;i=i+1) begin base; head_context_v=1; head_stage=i; native_active=1; inputs='+cat([n for n,w in ins])+'; step; end\n'
# random independently arbitrary states/inputs, then mostlyvalid X perturbation + priors
b+='for(i=0;i<20000;i=i+1) begin base; for(j=0;j<677;j=j+1) inputs[j]=$random(seed); for(j=0;j<145;j=j+1) state[j]=$random(seed); step; end\n'
b+='for(i=0;i<20000;i=i+1) begin base; for(j=0;j<16;j=j+1) begin k=$unsigned($random(seed))%677; case($unsigned($random(seed))%4) 0:inputs[k]=0;1:inputs[k]=1;2:inputs[k]=1\'bx;3:inputs[k]=1\'bz;endcase end for(j=0;j<8;j=j+1) begin k=$unsigned($random(seed))%145; case($unsigned($random(seed))%4) 0:state[k]=0;1:state[k]=1;2:state[k]=1\'bx;3:state[k]=1\'bz;endcase end step; end\n'
b+='for(i=0;i<4;i=i+1) begin base; rst_n=1; deposit; #1; rst_n=0; check; if(old_out!==161\'d0) $fatal(1,"ASYNC_RESET_FAIL"); cases=cases+1; rst_n=1; rx_v=1; receive_slot=1; #1; ck=1; check; ck=0; cases=cases+1; end\n'
b+='for(i=0;i<4;i=i+1) begin base; deposit; #1; case(i) 0:rst_n=0;1:rst_n=1;2:rst_n=1\'bx;3:rst_n=1\'bz;endcase check; #1;ck=1;check;ck=0;cases=cases+1;end\n'
b+='$display("ALL_OUTPUT_4STATE_PASS cases=%0d outputs=161 retained_state=145 inputs=677",cases); $finish; end\nendmodule\n'
p.joinpath('tb.sv').write_text(b)
# formal nextstate transforms keep source expression/RHS intact, only split present/next symbols
mods=[]
for file,mod in [('original.sv','old_next'),('candidate_a.sv','new_next')]:
 s=p.joinpath(file).read_text();s=s[s.index('module '):]
 header='module '+mod+'('+','.join('input wire '+decl(n,w) for n,w in ins+[('rst_n',1)])+',input wire [144:0] state,output wire [160:0] result);\n'
 body=s[s.index(');')+2:]
 body=''.join('wire '+decl(n,w)+'; reg '+decl(n+'_next',w)+';\n' for n,w in states)+'wire [15:0] host_epoch;\nassign '+statecat+'=state;\n'+body
 body=re.sub(r'always @\(posedge ck or negedge rst_n\)begin','always @* begin\n'+''.join(n+'_next='+n+';\n' for n,w in states),body)
 for n,w in states:body=re.sub(r'\b'+n+r'\s*<=',n+'_next=',body)
 body=body.replace('endmodule','assign result='+cat([n+'_next' for n,w in states]+['host_tag_next[58:43]'])+';\nendmodule')
 mods.append(header+body)
top='module proof('+','.join('input wire '+decl(n,w) for n,w in ins+[('rst_n',1)])+',input wire [144:0] state,output wire ok);\nwire [160:0] a,b;\n'
for inst,mod in [('a','old_next'),('b','new_next')]:top+=mod+' u_'+inst+'('+','.join('.'+n+'('+n+')' for n,w in ins+[('rst_n',1)])+',.state(state),.result('+inst+'));\n'
top+='assign ok=a==b; endmodule\n'
p.joinpath('proof.sv').write_text('\n'.join(mods)+top)
p.joinpath('proof.ys').write_text('read_verilog -formal proof.sv\nhierarchy -top proof\nproc\nflatten\nopt_clean\nsat -verify -prove ok 1 -show-inputs -show-outputs\n')
# explicit mutate actual DUT only
mut=p.joinpath('candidate_a.sv').read_text().replace('assign bad_predicate[4]=!(rx_record[511:142]==0);','assign bad_predicate[4]=1\'b0; // deliberate reserved-bit-check omission')
p.joinpath('mutant_reserved.sv').write_text(mut)
p.joinpath('run.sh').write_text('''#!/bin/bash
set -u
mkdir -p logs
hostname > logs/host.txt
iverilog -V > logs/iverilog_version.txt 2>&1
yosys -V > logs/yosys_version.txt 2>&1
sha256sum *.sv *.ys *.py run.sh > logs/inputs.sha256
/usr/bin/time -v -o logs/build.time iverilog -g2012 -s tb -o sim original.sv candidate_a.sv tb.sv > logs/build.log 2>&1 || exit $?
/usr/bin/time -v -o logs/sim.time vvp sim > logs/sim.log 2>&1
rc=$?; echo "$rc" > logs/sim.rc
if [ "$rc" -ne 0 ]; then cat logs/sim.log; exit "$rc"; fi
/usr/bin/time -v -o logs/formal.time yosys -Q -s proof.ys > logs/formal.log 2>&1
rc=$?; echo "$rc" > logs/formal.rc
if [ "$rc" -ne 0 ]; then tail -40 logs/formal.log; exit "$rc"; fi
iverilog -g2012 -s tb -o mutant original.sv mutant_reserved.sv tb.sv > logs/mutant_build.log 2>&1 || exit $?
vvp mutant > logs/mutant.log 2>&1
rc=$?; echo "$rc" > logs/mutant.rc
cat logs/sim.log
tail -8 logs/formal.log
cat logs/mutant.log
if [ "$rc" -eq 0 ]; then exit 3; fi
''')
print('bench/proof source bytes',sum(f.stat().st_size for f in p.iterdir()))
