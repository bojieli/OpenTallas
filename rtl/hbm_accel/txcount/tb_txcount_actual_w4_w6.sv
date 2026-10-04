`timescale 1ns/1ps
// Existing archived W4 real two-mirror RF + W6 successor; no ACK timer.
// Local fixture only: source-drain levels are fixture inputs, no CDC/refresh credit.
module tb_txcount_actual_w4_w6;
 reg clk=0;always #0.5 clk=~clk;
 reg por_n=1,rst_n=1;
 localparam[54:0] OWNER={7'd127,3'd5,32'hfe123456,4'd15,9'd511};
 reg rd_valid=0,rsp_ready=0,wr_valid=0;
 reg[8:0] rd_a=511,rd_b=511,wr_addr=511;
 reg[4095:0] wr_data={128{32'h3f812345}};
 wire rd_ready,rsp_valid,wr_ready,ack_valid,ack_ready,ack_identity_fault;
 wire[4095:0] rsp_a,rsp_b;wire[45:0] ack_owner;wire[8:0] ack_slot;
 wire[45:0] wr_owner=OWNER[54:9];
 ot_gpu_rf_service #(.ACK_ID(1)) rf(.*);
 reg req_valid=0,visible_ready=0,drain_req_ready=0,drain_rsp_valid=0;
 reg reset_scope=1,has_owner=0;
 wire req_ready,visible_valid,drain_req_valid,drain_rsp_ready,wfault,quarantine,retire_valid;
 wire[54:0] visible_identity,drain_req_identity;
 wire dr_has,dr_scope;
 ot_hbm_rf_visibility_fence_live #(.ENABLE(1)) fence(
 .clk(clk),.por_n(por_n),.rst_n(rst_n),.req_valid(req_valid),.req_identity(OWNER),.req_internal_SIMD(1'b0),.req_ready(req_ready),
 .host_ack_valid(ack_valid),.host_ack_identity({ack_owner,ack_slot}),.host_ack_ready(ack_ready),
 .simd_ack_retire_valid(1'b0),.simd_ack_retire_identity(55'b0),.simd_ack_retire_ready(),
 .visible_valid(visible_valid),.visible_identity(visible_identity),.visible_ready(visible_ready),
 .consumer_valid(1'b0),.consumer_identity(55'b0),.consumer_ready(),
 .child_reverse_valid(1'b0),.child_reverse_identity(55'b0),.child_reverse_ready(),
 .parent_reverse_valid(1'b0),.parent_reverse_identity(55'b0),.parent_reverse_ready(),
 .reverse_CDC_valid(1'b0),.reverse_CDC_identity(55'b0),.reverse_CDC_ready(),
 .drain_req_valid(drain_req_valid),.drain_req_identity(drain_req_identity),.drain_req_has_owner(dr_has),.drain_req_reset_scope(dr_scope),.drain_req_ready(drain_req_ready),
 .drain_rsp_valid(drain_rsp_valid),.drain_rsp_identity(55'b0),.drain_rsp_has_owner(has_owner),.drain_rsp_reset_scope(reset_scope),.alldrain_live(9'h1ff),.drain_rsp_ready(drain_rsp_ready),
 .retire_valid(retire_valid),.retire_identity(),.retire_ready(1'b0),.fault(wfault),.quarantine(quarantine));
 reg bv=0,mv=0,complete_ready=0;wire br,mr,complete_valid,cfault;
 wire wa,fa,source_fault;
 ot_hbm_txcount_tap #(.ENABLE(1)) tap(.rf_ack_accept(ack_valid&&ack_ready),.rf_ack_fault(ack_identity_fault),
 .w6_visible_valid(visible_valid),.w6_visible_ready(visible_ready),.w6_fault(wfault),.w4_accept(wa),.w6_accept(fa),.source_fault(source_fault));
 ot_hbm_txcount_sm #(.ENABLE(1)) counter(
 .clk(clk),.por_n(por_n),.rst_n(rst_n),.begin_valid(bv),.begin_ready(br),.begin_rank(7'd127),.begin_job(32'hfe123456),.begin_gen(4'd15),.begin_count(6'd1),
 .manifest_valid(mv),.manifest_ready(mr),.manifest_owner55(OWNER),
 .w4_accept(wa),.w4_index(5'd0),.w4_owner55({ack_owner,ack_slot}),.w4_rank(7'd127),.w4_job(32'hfe123456),.w4_gen(4'd15),
 .w6_accept(fa),.w6_index(5'd0),.w6_owner55(visible_identity),.w6_rank(7'd127),.w6_job(32'hfe123456),.w6_gen(4'd15),
 .source_fault(source_fault),.complete_valid(complete_valid),.complete_ready(complete_ready),.complete_rank(),.complete_job(),.complete_gen(),.fault(cfault));
 integer cyc=0,checks=0,ack_edge=0,visible_edge=0,complete_edge=0;
 always @(posedge clk)begin cyc=cyc+1;if(wa)ack_edge=cyc;if(fa)visible_edge=cyc;if(complete_valid&&complete_ready)complete_edge=cyc;end
 task tick;begin @(posedge clk);#0.1;end endtask
 task ck(input bit ok,input string message);begin checks=checks+1;if(!ok)$fatal(1,"actual W4/W6 %s",message);end endtask
 initial begin
 @(negedge clk);por_n=0;rst_n=0;tick;@(negedge clk);por_n=1;rst_n=1;
 // Existing cold source-drain handshake (fixture all-live inputs).
 while(!drain_req_valid)tick;
 @(negedge clk);drain_req_ready=1;tick;@(negedge clk);drain_req_ready=0;drain_rsp_valid=1;
 while(!drain_rsp_ready)tick;tick;@(negedge clk);drain_rsp_valid=0;reset_scope=0;has_owner=1;
 while(!req_ready)tick;
 @(negedge clk);bv=1;tick;@(negedge clk);bv=0;mv=1;tick;@(negedge clk);mv=0;req_valid=1;
 tick;@(negedge clk);req_valid=0;wr_valid=1;
 while(!wr_ready)tick;tick;@(negedge clk);wr_valid=0;
 while(!visible_valid)tick;
 ck(ack_edge>0&&!complete_valid&&!cfault,"real common ACK alone cannot complete");
 repeat(5)begin tick;ck(visible_valid&&!complete_valid,"visibility backpressure not counted");end
 @(negedge clk);visible_ready=1;complete_ready=1;tick;@(negedge clk);visible_ready=0;
 ck(complete_valid&&!cfault&&!wfault,"actual matched visibility and ACK complete");
 tick;ck(complete_edge>visible_edge&&!complete_valid,"scheduler consumes on positive next edge");
 $display("HA1_LOCAL_MEASURE ack_to_counter_complete=%0d visible_to_counter_complete=%0d wire_CDC_refresh_included=0",complete_edge-ack_edge,complete_edge-visible_edge);
 repeat(5)begin tick;ck(!complete_valid&&br&&!retire_valid&&!drain_req_valid,"scheduler completion retains W6 consumer debt");end
 // Read the actual two operand mirrors after publication.
 @(negedge clk);rd_valid=1;while(!rd_ready)tick;tick;@(negedge clk);rd_valid=0;
 while(!rsp_valid)tick;
 ck(rsp_a===wr_data&&rsp_b===wr_data,"both actual RF copies exact");
 $display("PASS_HA1_ACTUAL_W4_W6 checks=%0d common_ACK_counted=1 fence_handshake_counted=1 consumer_debt_retained=1",checks);$finish;
 end
endmodule
