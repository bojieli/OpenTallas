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
initial begin
base; step;
for(i=0;i<677;i=i+1) for(j=0;j<4;j=j+1) begin base; case(j) 0:inputs[i]=0; 1:inputs[i]=1; 2:inputs[i]=1'bx; 3:inputs[i]=1'bz; endcase step; end
for(i=0;i<145;i=i+1) for(j=0;j<4;j=j+1) begin base; case(j) 0:state[i]=0; 1:state[i]=1; 2:state[i]=1'bx; 3:state[i]=1'bz; endcase step; end
for(i=0;i<64;i=i+1) begin base; head_context_v=1; head_stage=i; native_active=1; inputs={receive_slot,rx_v,rx_record,program_begin_v,program_ready,installed_fusedcap,program_epoch,program_digest,head_context_v,head_stage,head_token,head_position,native_active}; step; end
for(i=0;i<20000;i=i+1) begin base; for(j=0;j<677;j=j+1) inputs[j]=$random(seed); for(j=0;j<145;j=j+1) state[j]=$random(seed); step; end
for(i=0;i<20000;i=i+1) begin base; for(j=0;j<16;j=j+1) begin k=$unsigned($random(seed))%677; case($unsigned($random(seed))%4) 0:inputs[k]=0;1:inputs[k]=1;2:inputs[k]=1'bx;3:inputs[k]=1'bz;endcase end for(j=0;j<8;j=j+1) begin k=$unsigned($random(seed))%145; case($unsigned($random(seed))%4) 0:state[k]=0;1:state[k]=1;2:state[k]=1'bx;3:state[k]=1'bz;endcase end step; end
for(i=0;i<4;i=i+1) begin base; rst_n=1; deposit; #1; rst_n=0; check; if(old_out!==161'd0) $fatal(1,"ASYNC_RESET_FAIL"); cases=cases+1; rst_n=1; rx_v=1; receive_slot=1; #1; ck=1; check; ck=0; cases=cases+1; end
for(i=0;i<4;i=i+1) begin base; deposit; #1; case(i) 0:rst_n=0;1:rst_n=1;2:rst_n=1'bx;3:rst_n=1'bz;endcase check; #1;ck=1;check;ck=0;cases=cases+1;end
$display("ALL_OUTPUT_4STATE_PASS cases=%0d outputs=161 retained_state=145 inputs=677",cases); $finish; end
endmodule
