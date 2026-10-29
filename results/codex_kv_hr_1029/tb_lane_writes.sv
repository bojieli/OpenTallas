`timescale 1ns/1ps
module tb; parameter integer MUTBENCH=0,HCW=39;
integer cycle,role_test,src_test,k,checks=0,diffs=0,rxframes=0;reg[31:0]seed=32'h12345678;
reg  ck=0;
reg  rst_n=0;
reg [2:0] die_id=0;
reg  rx_v=0;
reg [511:0] rx_d=0;
wire  a_rx_cr,b_rx_cr;
wire  a_tx_v,b_tx_v;
wire [511:0] a_tx_d,b_tx_d;
reg  tx_cr=0;
reg [92:0] local_tk=0;
reg [9:0] local_kst=0;
reg [1:0] local_boot=0;
reg  cmd_v=0;
reg [HCW-1:0] cmd_hc=0;
wire  a_cmd_cr,b_cmd_cr;
wire [HCW-1:0] a_hc,b_hc;
wire [743:0] a_tk8,b_tk8;
wire [79:0] a_kst8,b_kst8;
wire [15:0] a_boot8,b_boot8;
wire [7:0] a_seen,b_seen;
wire  a_fault,b_fault;
reg  startup_allowed=0;
reg  local_service_ready=0;
reg [15:0] local_service_epoch=0;
reg  begin_v=0;
reg [15:0] begin_epoch=0;
wire  a_begin_cr,b_begin_cr;
wire  a_begin_available,b_begin_available;
wire  a_service_begin_v,b_service_begin_v;
wire [15:0] a_service_begin_epoch,b_service_begin_epoch;
wire  a_pending_advertised,b_pending_advertised;
wire [15:0] a_pending_epoch,b_pending_epoch;
wire [7:0] a_service_ready8,b_service_ready8;
wire [7:0] a_pending_ack8,b_pending_ack8;
wire [127:0] a_service_epoch8,b_service_epoch8;
wire  a_ingest_permission,b_ingest_permission;
reg  por_n=0;
reg  token_wrap_fence_valid=0;
reg  token_wrap_drained=0;
reg  token_wrap_link_reset_seen=0;
reg  token_wrap_retraining_done=0;
reg  token_allocator_fault=0;
reg  package_abort=0;
reg [3:0] abort_drained=0;
wire  a_token_request_valid,b_token_request_valid;
reg  token_request_ready=0;
wire [17:0] a_token_request_token,b_token_request_token;
wire [17:0] a_token_request_position,b_token_request_position;
wire [1:0] a_token_request_generation,b_token_request_generation;
reg  token_grant_valid=0;
wire  a_token_grant_ready,b_token_grant_ready;
reg [15:0] token_grant_epoch=0;
reg [17:0] token_grant_token=0;
reg [17:0] token_grant_position=0;
reg [1:0] token_grant_generation=0;
reg [58:0] token_grant_tag=0;
reg  allocated_valid=0;
reg  allocated_delivered=0;
reg [15:0] allocated_epoch=0;
reg [17:0] allocated_token=0;
reg [17:0] allocated_position=0;
reg [1:0] allocated_generation=0;
wire  a_token_epoch_valid,b_token_epoch_valid;
wire [15:0] a_token_epoch,b_token_epoch;
wire  a_cancel_valid,b_cancel_valid;
wire [58:0] a_cancel_tag,b_cancel_tag;
wire [1:0] a_cancel_generation,b_cancel_generation;
wire  a_cancel_done,b_cancel_done;
wire  a_cancel_fault,b_cancel_fault;
wire [3:0] a_cancel_drained,b_cancel_drained;
reg  terminal_accepted=0;
qkd_host_ctrl_token_service_packet_collected_mu #(.MU(1),.HCW(HCW),.STRAPPED(1),.ENABLE_SERVICE(1),.ENABLE_TOKEN(1),.CONST_LANE_WRITES(0)) a(.ck(ck),.rst_n(rst_n),.die_id(die_id),.rx_v(rx_v),.rx_d(rx_d),.rx_cr(a_rx_cr),.tx_v(a_tx_v),.tx_d(a_tx_d),.tx_cr(tx_cr),.local_tk(local_tk),.local_kst(local_kst),.local_boot(local_boot),.cmd_v(cmd_v),.cmd_hc(cmd_hc),.cmd_cr(a_cmd_cr),.hc(a_hc),.tk8(a_tk8),.kst8(a_kst8),.boot8(a_boot8),.seen(a_seen),.fault(a_fault),.startup_allowed(startup_allowed),.local_service_ready(local_service_ready),.local_service_epoch(local_service_epoch),.begin_v(begin_v),.begin_epoch(begin_epoch),.begin_cr(a_begin_cr),.begin_available(a_begin_available),.service_begin_v(a_service_begin_v),.service_begin_epoch(a_service_begin_epoch),.pending_advertised(a_pending_advertised),.pending_epoch(a_pending_epoch),.service_ready8(a_service_ready8),.pending_ack8(a_pending_ack8),.service_epoch8(a_service_epoch8),.ingest_permission(a_ingest_permission),.por_n(por_n),.token_wrap_fence_valid(token_wrap_fence_valid),.token_wrap_drained(token_wrap_drained),.token_wrap_link_reset_seen(token_wrap_link_reset_seen),.token_wrap_retraining_done(token_wrap_retraining_done),.token_allocator_fault(token_allocator_fault),.package_abort(package_abort),.abort_drained(abort_drained),.token_request_valid(a_token_request_valid),.token_request_ready(token_request_ready),.token_request_token(a_token_request_token),.token_request_position(a_token_request_position),.token_request_generation(a_token_request_generation),.token_grant_valid(token_grant_valid),.token_grant_ready(a_token_grant_ready),.token_grant_epoch(token_grant_epoch),.token_grant_token(token_grant_token),.token_grant_position(token_grant_position),.token_grant_generation(token_grant_generation),.token_grant_tag(token_grant_tag),.allocated_valid(allocated_valid),.allocated_delivered(allocated_delivered),.allocated_epoch(allocated_epoch),.allocated_token(allocated_token),.allocated_position(allocated_position),.allocated_generation(allocated_generation),.token_epoch_valid(a_token_epoch_valid),.token_epoch(a_token_epoch),.cancel_valid(a_cancel_valid),.cancel_tag(a_cancel_tag),.cancel_generation(a_cancel_generation),.cancel_done(a_cancel_done),.cancel_fault(a_cancel_fault),.cancel_drained(a_cancel_drained),.terminal_accepted(terminal_accepted));
qkd_host_ctrl_token_service_packet_collected_mu #(.MU(1),.HCW(HCW),.STRAPPED(1),.ENABLE_SERVICE(1),.ENABLE_TOKEN(1),.CONST_LANE_WRITES(1),.MUT(MUTBENCH)) b(.ck(ck),.rst_n(rst_n),.die_id(die_id),.rx_v(rx_v),.rx_d(rx_d),.rx_cr(b_rx_cr),.tx_v(b_tx_v),.tx_d(b_tx_d),.tx_cr(tx_cr),.local_tk(local_tk),.local_kst(local_kst),.local_boot(local_boot),.cmd_v(cmd_v),.cmd_hc(cmd_hc),.cmd_cr(b_cmd_cr),.hc(b_hc),.tk8(b_tk8),.kst8(b_kst8),.boot8(b_boot8),.seen(b_seen),.fault(b_fault),.startup_allowed(startup_allowed),.local_service_ready(local_service_ready),.local_service_epoch(local_service_epoch),.begin_v(begin_v),.begin_epoch(begin_epoch),.begin_cr(b_begin_cr),.begin_available(b_begin_available),.service_begin_v(b_service_begin_v),.service_begin_epoch(b_service_begin_epoch),.pending_advertised(b_pending_advertised),.pending_epoch(b_pending_epoch),.service_ready8(b_service_ready8),.pending_ack8(b_pending_ack8),.service_epoch8(b_service_epoch8),.ingest_permission(b_ingest_permission),.por_n(por_n),.token_wrap_fence_valid(token_wrap_fence_valid),.token_wrap_drained(token_wrap_drained),.token_wrap_link_reset_seen(token_wrap_link_reset_seen),.token_wrap_retraining_done(token_wrap_retraining_done),.token_allocator_fault(token_allocator_fault),.package_abort(package_abort),.abort_drained(abort_drained),.token_request_valid(b_token_request_valid),.token_request_ready(token_request_ready),.token_request_token(b_token_request_token),.token_request_position(b_token_request_position),.token_request_generation(b_token_request_generation),.token_grant_valid(token_grant_valid),.token_grant_ready(b_token_grant_ready),.token_grant_epoch(token_grant_epoch),.token_grant_token(token_grant_token),.token_grant_position(token_grant_position),.token_grant_generation(token_grant_generation),.token_grant_tag(token_grant_tag),.allocated_valid(allocated_valid),.allocated_delivered(allocated_delivered),.allocated_epoch(allocated_epoch),.allocated_token(allocated_token),.allocated_position(allocated_position),.allocated_generation(allocated_generation),.token_epoch_valid(b_token_epoch_valid),.token_epoch(b_token_epoch),.cancel_valid(b_cancel_valid),.cancel_tag(b_cancel_tag),.cancel_generation(b_cancel_generation),.cancel_done(b_cancel_done),.cancel_fault(b_cancel_fault),.cancel_drained(b_cancel_drained),.terminal_accepted(terminal_accepted));
always #5 ck=~ck;
initial begin
for(role_test=0;role_test<8;role_test=role_test+1)begin
 rst_n=0;por_n=0;die_id=3'(role_test);repeat(3)@(negedge ck);rst_n=1;por_n=1;startup_allowed=1;local_service_ready=1;local_service_epoch=0;
for(cycle=0;cycle<512;cycle=cycle+1)begin
@(negedge ck); local_tk={$random(seed),$random(seed),$random(seed)};local_kst=10'($random(seed));local_boot=2'($random(seed));tx_cr=0;rx_v=0;
if(role_test==0 && cycle>=16 && cycle%16==0 && cycle<128)begin src_test=(cycle/16);rx_d=0;rx_d[7:0]=8'h21;rx_d[15:8]=8'd2;rx_d[18:16]=3'(src_test);rx_d[31:24]=8'd1;rx_d[47:32]=16'd0;rx_d[140:48]={$random(seed),$random(seed),$random(seed)};rx_d[150:141]=10'($random(seed));rx_d[152:151]=2'($random(seed));rx_d[153]=0;rx_v=1;rxframes=rxframes+1;end
@(posedge ck);#1;checks=checks+1;
if({a_rx_cr,a_tx_v,a_tx_d,a_cmd_cr,a_hc,a_tk8,a_kst8,a_boot8,a_seen,a_fault,a_begin_cr,a_begin_available,a_service_begin_v,a_service_begin_epoch,a_pending_advertised,a_pending_epoch,a_service_ready8,a_pending_ack8,a_service_epoch8,a_ingest_permission,a_token_request_valid,a_token_request_token,a_token_request_position,a_token_request_generation,a_token_grant_ready,a_token_epoch_valid,a_token_epoch,a_cancel_valid,a_cancel_tag,a_cancel_generation,a_cancel_done,a_cancel_fault,a_cancel_drained} !== {b_rx_cr,b_tx_v,b_tx_d,b_cmd_cr,b_hc,b_tk8,b_kst8,b_boot8,b_seen,b_fault,b_begin_cr,b_begin_available,b_service_begin_v,b_service_begin_epoch,b_pending_advertised,b_pending_epoch,b_service_ready8,b_pending_ack8,b_service_epoch8,b_ingest_permission,b_token_request_valid,b_token_request_token,b_token_request_position,b_token_request_generation,b_token_grant_ready,b_token_epoch_valid,b_token_epoch,b_cancel_valid,b_cancel_tag,b_cancel_generation,b_cancel_done,b_cancel_fault,b_cancel_drained})begin diffs=diffs+1;if(diffs<3)$display("DIFF role=%0d cycle=%0d",role_test,cycle);end
end
end
$display("RESULT checks=%0d diffs=%0d rxframes=%0d mutant=%0d HCW=%0d",checks,diffs,rxframes,MUTBENCH,HCW);if((MUTBENCH==0 && diffs!=0)||(MUTBENCH!=0 && diffs==0))$fatal(1,"miter verdict");$finish;end
endmodule
