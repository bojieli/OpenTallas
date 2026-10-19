from pathlib import Path
p=Path(__file__).parent
s=p.joinpath('tb.sv').read_text(); start=s.index('initial begin\n'); s=s[:start]+'''function val4(input integer v); case(v) 0:val4=0;1:val4=1;2:val4=1'bx;3:val4=1'bz;endcase endfunction
integer q;
initial begin
// Seven live control inputs and arbitrary prior fault: all 4^8 combinations.
for(i=0;i<65536;i=i+1) begin base; q=i;
receive_slot=val4(q%4);q=q/4; rx_v=val4(q%4);q=q/4;
program_begin_v=val4(q%4);q=q/4;program_ready=val4(q%4);q=q/4;
installed_fusedcap=val4(q%4);q=q/4;head_context_v=val4(q%4);q=q/4;
native_active=val4(q%4);q=q/4;state[0]=val4(q%4);
inputs={receive_slot,rx_v,rx_record,program_begin_v,program_ready,installed_fusedcap,program_epoch,program_digest,head_context_v,head_stage,head_token,head_position,native_active};step;end
// Actual active head check, every stage and every head tuple bit including X/Z.
for(i=0;i<64;i=i+1) begin base;receive_slot=0;rx_v=0;head_context_v=1;head_stage=i;head_token=43;inputs={receive_slot,rx_v,rx_record,program_begin_v,program_ready,installed_fusedcap,program_epoch,program_digest,head_context_v,head_stage,head_token,head_position,native_active};step;end
for(i=0;i<42;i=i+1) for(j=0;j<4;j=j+1) begin base;receive_slot=0;rx_v=0;head_context_v=1; {head_stage,head_token,head_position}[i]=val4(j);end
'''
# variable indexed concatenation is not legal assignment in Icarus; explicit slice variable.
s=s[:s.index('for(i=0;i<42;')]+'''for(i=0;i<42;i=i+1) for(j=0;j<4;j=j+1) begin base;receive_slot=0;rx_v=0;head_context_v=1;
if(i<18)head_position[i]=val4(j);else if(i<36)head_token[i-18]=val4(j);else head_stage[i-36]=val4(j);
inputs={receive_slot,rx_v,rx_record,program_begin_v,program_ready,installed_fusedcap,program_epoch,program_digest,head_context_v,head_stage,head_token,head_position,native_active};step;end
// Installed image mutation while active with receive disabled: every image tuple bit.
for(i=0;i<81;i=i+1) for(j=0;j<4;j=j+1) begin base;receive_slot=0;rx_v=0;native_active=1;
if(i<64)program_digest[i]=val4(j);else if(i<80)program_epoch[i-64]=val4(j);else installed_fusedcap=val4(j);
inputs={receive_slot,rx_v,rx_record,program_begin_v,program_ready,installed_fusedcap,program_epoch,program_digest,head_context_v,head_stage,head_token,head_position,native_active};step;end
$display("DIRECTED_ALL_OUTPUT_4STATE_PASS cases=%0d controls=65536 active_head=232 active_image=324",cases);$finish;end
endmodule
'''
p.joinpath('tb_directed.sv').write_text(s)
p.joinpath('run_directed.sh').write_text('''#!/bin/bash
set -eu
mkdir -p logs_directed
sha256sum original.sv candidate_a.sv tb_directed.sv run_directed.sh > logs_directed/inputs.sha256
/usr/bin/time -v -o logs_directed/build.time iverilog -g2012 -s tb -o sim_directed original.sv candidate_a.sv tb_directed.sv > logs_directed/build.log 2>&1
/usr/bin/time -v -o logs_directed/sim.time vvp sim_directed > logs_directed/sim.log 2>&1
cat logs_directed/sim.log
''')
