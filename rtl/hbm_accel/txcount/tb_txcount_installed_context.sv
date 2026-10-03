`timescale 1ns/1ps
// Existing archived W4 real two-mirror RF + W6 successor; no ACK timer.
// Local fixture only: source-drain levels are fixture inputs, no CDC/refresh credit. Actual guarded-SM/issuer context joins, not an operator golden.
module tb_txcount_installed_context;
 parameter LIVE_STATE=0;
 reg clk=0;always #0.5 clk=~clk;
 reg por_n=1,rst_n=1;
 localparam[54:0] OWNER={7'd127,3'd5,32'hfe123456,4'd15,9'd511};
 reg rd_valid=0,rsp_ready=0,wr_valid=0;
 reg[8:0] rd_a=511,rd_b=511,wr_addr=511;
 reg[4095:0] wr_data={128{32'h3f812345}};
 wire rd_ready,rsp_valid,wr_ready,ack_valid,ack_ready,ack_identity_fault;
 wire[4095:0] rsp_a,rsp_b;wire[45:0] ack_owner;wire[8:0] ack_slot;
 wire[45:0] wr_owner=OWNER[54:9];
 wire actual_rf_ack_accept,actual_rf_ack_fault;
 wire [54:0] actual_rf_ack_owner55;
 ot_gpu_full_sm_service_guarded #(.ENABLE(1),.ACK_ID(1),.OPT_CONTEXT(1),.INSTANCE_ID(33)) sm(
 .clk(clk),.rst_n(rst_n),.host_rd_valid(rd_valid),.host_rd_ready(rd_ready),.host_a(rd_a),.host_b(rd_b),
 .host_rsp_valid(rsp_valid),.host_rsp_ready(rsp_ready),.host_rsp_a(rsp_a),.host_rsp_b(rsp_b),
 .host_wr_valid(wr_valid),.host_wr_ready(wr_ready),.host_dst(wr_addr),.host_wdata(wr_data),
 .host_ack_valid(ack_valid),.host_ack_ready(ack_ready),.host_owner(wr_owner),.host_ack_owner(ack_owner),.host_ack_slot(ack_slot),.identity_fault(ack_identity_fault),
 .simd_valid(1'b0),.simd_ready(),.simd_mul(1'b0),.simd_a(9'b0),.simd_b(9'b0),.simd_dst(9'b0),.simd_done(),.simd_done_ready(1'b0),.simd_fault(),.simd_owner(46'b0),.simd_done_owner(),.simd_done_slot(),
 .scratch_valid(1'b0),.scratch_write(1'b0),.scratch_ready(),.scratch_addr(10'b0),.scratch_wdata(512'b0),.scratch_done(),.scratch_done_ready(1'b0),.scratch_rdata(),
 .simd_context_permit(1'b0),.rd_permit(1'b1),.wr_permit(1'b1),.rf_rsp_allow(1'b1),.rf_ack_allow(1'b1),
 .simd_binding_valid(1'b0),.simd_KV_related(1'b0),.simd_source_identity(64'b0),.simd_key(20'b0),
 .host_rd_binding_valid(1'b1),.host_rd_KV_related(1'b0),.host_rd_identity(64'hfedcba9876543210),.host_rd_key(20'd37),
 .host_wr_binding_valid(1'b1),.host_wr_KV_related(1'b0),.host_wr_identity(64'hfedcba9876543210),.host_wr_key(20'd37),
 .host_rd_continuation_valid(1'b0),.host_wr_continuation_valid(1'b0),
 .rf_ack_accept(actual_rf_ack_accept),.rf_ack_owner55(actual_rf_ack_owner55),.rf_ack_fault(actual_rf_ack_fault));
 reg req_valid=0,visible_ready=0,drain_req_ready=0,drain_rsp_valid=0;
 reg reset_scope=1,has_owner=0;
 wire req_ready,visible_valid,drain_req_valid,drain_rsp_ready,wfault,quarantine,retire_valid;
 wire[54:0] visible_identity,drain_req_identity;
 wire dr_has,dr_scope;
 ot_hbm_w6_source_select #(.ENABLE(1),.LIVE_STATE(LIVE_STATE)) fence(
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
 reg issue_valid=0,producer_valid=0,terminal_valid=0,reverse_valid=0;
 reg published_ready=0,frame_ready=0,input_terminal_ready=0,input_reverse_ready=0;
 wire issue_ready,backend_go_valid,producer_ready,terminal_ready,reverse_ready,publish_valid,frame_valid,input_terminal_valid,input_reverse_valid,issuer_busy,issuer_fault;
 wire [238:0] backend_go_tuple,frame_tuple;wire [54:0] backend_go_owner,frame_owner;
 localparam [238:0] GO={64'h1234,11'd13,64'hfedcba9876543210,64'h100000000,1'b1,5'd1,11'd37,9'd511,10'd512};
 wire go_accept=backend_go_valid&&wr_ready&&req_ready;
 ot_gpu_qwen_full_issuer_sm_r2 #(.ENABLE(1),.INDEX(33)) issuer(
 .clk(clk),.por_n(por_n),.run_enable(1'b1),.session_valid(1'b1),.session_id(64'h1234),
 .issue_valid(issue_valid),.row_barrier_ready(1'b1),.backend_go_ready(wr_ready&&req_ready),.issue_tuple(GO),.issue_owner(OWNER),
 .inputs_bound_valid(issue_valid),.inputs_bound_tuple(GO),.inputs_bound_mask(7'b101),.issue_output_page_mask(32'd1),.inputs_bound_ready(),
 .issue_ready(issue_ready),.backend_go_valid(backend_go_valid),.backend_go_tuple(backend_go_tuple),.backend_go_owner(backend_go_owner),
 .producer_visible_valid(producer_valid),.producer_visible_tuple(GO),.producer_visible_ready(producer_ready),
 .rf_range_ack_valid(actual_rf_ack_accept),.rf_range_ack_owner(actual_rf_ack_owner55),.rf_range_ack_tuple(GO),.rf_range_ack_page_mask(32'd1),.rf_range_ack_ready(),
 .whole_terminal_valid(terminal_valid),.whole_terminal_tuple(GO),.whole_terminal_ready(terminal_ready),
 .whole_reverse_valid(reverse_valid),.whole_reverse_tuple(GO),.whole_reverse_ready(reverse_ready),
 .publish_valid(publish_valid),.publish_ready(published_ready),.publish_tuple(),.publish_owner(),.publish_page_mask(),
 .frame_retire_valid(frame_valid),.frame_retire_ready(frame_ready),.frame_retire_tuple(frame_tuple),.frame_retire_owner(frame_owner),
 .input_terminal_valid(input_terminal_valid),.input_terminal_ready(input_terminal_ready),.input_terminal_tuple(),.input_terminal_mask(),
 .input_reverse_valid(input_reverse_valid),.input_reverse_ready(input_reverse_ready),.input_reverse_tuple(),.input_reverse_mask(),.busy(issuer_busy),.fault(issuer_fault));
 reg complete_ready=0;wire complete_valid,cfault,join_retained;wire [238:0] complete_tuple;
 wire br=!join_retained;
 wire wa=actual_rf_ack_accept,fa=visible_valid&&visible_ready;
 ot_hbm_txcount_capture_join #(.ENABLE(1),.INDEX(33)) joined(
 .clk(clk),.por_n(por_n),.rst_n(rst_n),.go_accept(go_accept),.go_tuple(backend_go_tuple),.go_owner55(backend_go_owner),.go_page_mask(32'd1),
 .rf_ack_accept(actual_rf_ack_accept),.rf_ack_owner55(actual_rf_ack_owner55),
 .w6_visible_accept(fa),.w6_visible_owner55(visible_identity),
 .producer_visible_accept(producer_valid&&producer_ready),.producer_visible_tuple(GO),
 .frame_retire_accept(frame_valid&&frame_ready),.frame_retire_tuple(frame_tuple),.frame_retire_owner55(frame_owner),
 .source_fault(issuer_fault||actual_rf_ack_fault||wfault),
 .dependency_valid(complete_valid),.dependency_ready(complete_ready),.dependency_tuple(complete_tuple),.dependency_owner55(),.dependency_page_mask(),.retained(join_retained),.fault(cfault));
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
 @(negedge clk);issue_valid=1;#0.01;ck(issue_ready&&go_accept,"actual guarded SM and W6 accept issuer GO");tick;
 @(negedge clk);issue_valid=0;req_valid=1;tick;@(negedge clk);req_valid=0;wr_valid=1;
 while(!wr_ready)tick;tick;@(negedge clk);wr_valid=0;
 while(!visible_valid)tick;
 @(negedge clk);producer_valid=1;#0.01;ck(producer_ready,"actual issuer whole-visibility capture");tick;@(negedge clk);producer_valid=0;
 ck(ack_edge>0&&!complete_valid&&!cfault,"real common ACK alone cannot complete");
 repeat(5)begin tick;ck(visible_valid&&!complete_valid,"visibility backpressure not counted");end
 @(negedge clk);visible_ready=1;complete_ready=1;tick;@(negedge clk);visible_ready=0;
 ck(complete_valid&&!cfault&&!wfault,"actual matched visibility and ACK complete");
 tick;ck(complete_edge>visible_edge&&!complete_valid,"scheduler consumes on positive next edge");
 $display("HA1_LOCAL_MEASURE ack_to_counter_complete=%0d visible_to_counter_complete=%0d wire_CDC_refresh_included=0",complete_edge-ack_edge,complete_edge-visible_edge);
 repeat(5)begin tick;ck(!complete_valid&&join_retained&&issuer_busy&&!retire_valid&&!drain_req_valid,"scheduler completion retains W6 consumer debt");end
 // Read the actual two operand mirrors after publication.
 @(negedge clk);rd_valid=1;while(!rd_ready)tick;tick;@(negedge clk);rd_valid=0;
 while(!rsp_valid)tick;
 ck(rsp_a===wr_data&&rsp_b===wr_data,"both actual RF copies exact");
 ck(complete_tuple==GO,"full native64 identity retained independently of backend owner");
 @(negedge clk);published_ready=1;tick;@(negedge clk);published_ready=0;terminal_valid=1;tick;
 @(negedge clk);terminal_valid=0;reverse_valid=1;tick;@(negedge clk);reverse_valid=0;
 ck(input_terminal_valid&&input_reverse_valid&&!frame_valid,"actual input notification debt still owns issuer");
 input_terminal_ready=1;input_reverse_ready=1;tick;@(negedge clk);input_terminal_ready=0;input_reverse_ready=0;
 ck(frame_valid&&join_retained,"actual frame closure offered, join retained");
 frame_ready=1;tick;@(negedge clk);frame_ready=0;
 ck(!issuer_busy&&!issuer_fault&&!join_retained&&!cfault,"join releases observer only on actual frame retirement");
 ck(!retire_valid&&!drain_req_valid,"W6 consumer/drain debt not cleared by actual issuer frame");
 $display("PASS_HA1_INSTALLED_CONTEXT live_state=%0d checks=%0d actual_guarded_SM=1 actual_issuer=1 W6_debt_retained=1",LIVE_STATE,checks);$finish;
 end
endmodule
