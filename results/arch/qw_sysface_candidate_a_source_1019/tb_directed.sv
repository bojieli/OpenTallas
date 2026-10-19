`timescale 1ns/1ps
module tb;
reg receive_slot;
reg rx_v;
reg [547:0] rx_record;
reg program_begin_v;
reg program_ready;
reg installed_fusedcap;
reg [15:0] program_epoch;
reg [63:0] program_digest;
reg head_context_v;
reg [5:0] head_stage;
reg [17:0] head_token;
reg [17:0] head_position;
reg native_active;
reg rst_n;
reg ck;
wire [160:0] old_out,new_out; reg [144:0] state; integer cases=0, i,j,k,seed=32'h19a019a0; reg [676:0] inputs;
wire a_accepted_v;
wire a_host_epoch_valid;
wire [58:0] a_host_tag;
wire [1:0] a_host_gen;
wire a_host_fusedcap;
wire [15:0] a_host_image_epoch;
wire [63:0] a_host_image_digest;
wire a_fault;
wire [15:0] a_host_epoch;
qfd_host_native_context_rx a(.receive_slot(receive_slot),.rx_v(rx_v),.rx_record(rx_record),.program_begin_v(program_begin_v),.program_ready(program_ready),.installed_fusedcap(installed_fusedcap),.program_epoch(program_epoch),.program_digest(program_digest),.head_context_v(head_context_v),.head_stage(head_stage),.head_token(head_token),.head_position(head_position),.native_active(native_active),.rst_n(rst_n),.ck(ck),.accepted_v(a_accepted_v),.host_epoch_valid(a_host_epoch_valid),.host_tag(a_host_tag),.host_gen(a_host_gen),.host_fusedcap(a_host_fusedcap),.host_image_epoch(a_host_image_epoch),.host_image_digest(a_host_image_digest),.fault(a_fault),.host_epoch(a_host_epoch));
assign old_out={a_accepted_v,a_host_epoch_valid,a_host_tag,a_host_gen,a_host_fusedcap,a_host_image_epoch,a_host_image_digest,a_fault,a_host_epoch};
wire b_accepted_v;
wire b_host_epoch_valid;
wire [58:0] b_host_tag;
wire [1:0] b_host_gen;
wire b_host_fusedcap;
wire [15:0] b_host_image_epoch;
wire [63:0] b_host_image_digest;
wire b_fault;
wire [15:0] b_host_epoch;
qfd_host_native_context_rx_candidate_a b(.receive_slot(receive_slot),.rx_v(rx_v),.rx_record(rx_record),.program_begin_v(program_begin_v),.program_ready(program_ready),.installed_fusedcap(installed_fusedcap),.program_epoch(program_epoch),.program_digest(program_digest),.head_context_v(head_context_v),.head_stage(head_stage),.head_token(head_token),.head_position(head_position),.native_active(native_active),.rst_n(rst_n),.ck(ck),.accepted_v(b_accepted_v),.host_epoch_valid(b_host_epoch_valid),.host_tag(b_host_tag),.host_gen(b_host_gen),.host_fusedcap(b_host_fusedcap),.host_image_epoch(b_host_image_epoch),.host_image_digest(b_host_image_digest),.fault(b_fault),.host_epoch(b_host_epoch));
assign new_out={b_accepted_v,b_host_epoch_valid,b_host_tag,b_host_gen,b_host_fusedcap,b_host_image_epoch,b_host_image_digest,b_fault,b_host_epoch};
task check; begin #1; if(old_out !== new_out) begin $display("DUT_MISMATCH case=%0d inputs=%h state=%h old=%h new=%h",cases,inputs,state,old_out,new_out); $fatal(1); end end endtask
task deposit; begin
{a.accepted_v,a.host_epoch_valid,a.host_tag,a.host_gen,a.host_fusedcap,a.host_image_epoch,a.host_image_digest,a.fault}=state;
{b.accepted_v,b.host_epoch_valid,b.host_tag,b.host_gen,b.host_fusedcap,b.host_image_epoch,b.host_image_digest,b.fault}=state;
end endtask
task step; begin ck=0; {receive_slot,rx_v,rx_record,program_begin_v,program_ready,installed_fusedcap,program_epoch,program_digest,head_context_v,head_stage,head_token,head_position,native_active}=inputs; deposit; #1; ck=1; check; ck=0; cases=cases+1; end endtask
task base; begin rst_n=1; ck=0; receive_slot=1; rx_v=1; rx_record=0; program_begin_v=0; program_ready=1; installed_fusedcap=1; program_epoch=16'h1234; program_digest=64'habcdef0123456789; head_context_v=0; head_stage=1; head_token=42; head_position=7; native_active=0; rx_record[542:539]=12; rx_record[538:533]=63; rx_record[532:517]=program_epoch; rx_record[58:43]=program_epoch; rx_record[36:19]=42; rx_record[18:6]=7; rx_record[61]=1; rx_record[77:62]=program_epoch; rx_record[141:78]=program_digest; state={1'b0,1'b1,rx_record[58:0],2'b0,1'b1,program_epoch,program_digest,1'b0}; inputs={receive_slot,rx_v,rx_record,program_begin_v,program_ready,installed_fusedcap,program_epoch,program_digest,head_context_v,head_stage,head_token,head_position,native_active}; end endtask
function val4(input integer v); case(v) 0:val4=0;1:val4=1;2:val4=1'bx;3:val4=1'bz;endcase endfunction
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
for(i=0;i<42;i=i+1) for(j=0;j<4;j=j+1) begin base;receive_slot=0;rx_v=0;head_context_v=1;
if(i<18)head_position[i]=val4(j);else if(i<36)head_token[i-18]=val4(j);else head_stage[i-36]=val4(j);
inputs={receive_slot,rx_v,rx_record,program_begin_v,program_ready,installed_fusedcap,program_epoch,program_digest,head_context_v,head_stage,head_token,head_position,native_active};step;end
// Installed image mutation while active with receive disabled: every image tuple bit.
for(i=0;i<81;i=i+1) for(j=0;j<4;j=j+1) begin base;receive_slot=0;rx_v=0;native_active=1;
if(i<64)program_digest[i]=val4(j);else if(i<80)program_epoch[i-64]=val4(j);else installed_fusedcap=val4(j);
inputs={receive_slot,rx_v,rx_record,program_begin_v,program_ready,installed_fusedcap,program_epoch,program_digest,head_context_v,head_stage,head_token,head_position,native_active};step;end
$display("DIRECTED_ALL_OUTPUT_4STATE_PASS cases=%0d controls=65536 active_head=232 active_image=324",cases);$finish;end
endmodule
