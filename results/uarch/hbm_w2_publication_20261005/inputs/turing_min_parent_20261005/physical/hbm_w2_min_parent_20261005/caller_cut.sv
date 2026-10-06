`timescale 1ns/1ps
// Same selected NC8/RMAX256/PIO2 output capture edges and NCTX11 identity join.
// These FF payloads replace raw inherited FFs; there is no added queue or stage.
module ot_hbm_w2_parent_caller_cut #(parameter integer ENABLE=0)(
 input wire clk,rst_n,producer_cv,producer_fault,
 input wire [7:0] producer_crow,input wire [255:0] producer_cy,
 input wire producer_busy,producer_arrive,producer_released,
 input wire caller_start,caller_sm_ready,caller_pair,caller_bound,
 input wire [8:0] caller_rows,input wire [31:0] caller_op_a,caller_op_b,
 output wire ctx_ready,rv,output wire [7:0] rrow,output wire [31:0] rop,
 output wire [255:0] rdata,output wire busy,arrive,released,fault
);
 generate if(!ENABLE)begin:off
  assign ctx_ready=0;assign rv=0;assign rrow=0;assign rop=0;assign rdata=0;
  assign busy=0;assign arrive=0;assign released=0;assign fault=0;
 end else begin:on
  wire [265:0] root_word,pio0,pio1;
  wire [2:0] busy0,busy1;
  wire root_fault,pio0_fault,pio1_fault,busy0_fault,busy1_fault,ctx_fault;
  wire view_fault=root_fault|pio0_fault|pio1_fault|busy0_fault|busy1_fault;
  (* keep_hierarchy=1 *) ot_hbm_w2_parent_protected_view #(.WIDTH(266)) u_root(
   .clk(clk),.por_n(rst_n),.we(1'b1),
   .next_data({producer_cv,root_word[264]|producer_fault,producer_crow,producer_cy}),
   .data(root_word),.fault(root_fault));
  (* keep_hierarchy=1 *) ot_hbm_w2_parent_protected_view #(.WIDTH(266)) u_pio0(
   .clk(clk),.por_n(rst_n),.we(1'b1),.next_data(root_word),.data(pio0),.fault(pio0_fault));
  (* keep_hierarchy=1 *) ot_hbm_w2_parent_protected_view #(.WIDTH(266)) u_pio1(
   .clk(clk),.por_n(rst_n),.we(1'b1),.next_data(pio0),.data(pio1),.fault(pio1_fault));
  (* keep_hierarchy=1 *) ot_hbm_w2_parent_protected_view #(.WIDTH(3)) u_busy0(
   .clk(clk),.por_n(rst_n),.we(1'b1),.next_data({producer_busy,producer_arrive,producer_released}),
   .data(busy0),.fault(busy0_fault));
  (* keep_hierarchy=1 *) ot_hbm_w2_parent_protected_view #(.WIDTH(3)) u_busy1(
   .clk(clk),.por_n(rst_n),.we(1'b1),.next_data(busy0),.data(busy1),.fault(busy1_fault));
  wire joined_v,joined_ready;
  ot_hbm_w2_parent_result_join #(.ENABLE(1),.RW(8),.NCTX(11)) u_results(
   .clk(clk),.rst_n(rst_n),.ctx_valid(caller_start&&caller_sm_ready&&!view_fault),
   .ctx_ready(joined_ready),.ctx_pair(caller_pair),.ctx_bound(caller_bound),.ctx_rows(caller_rows),
   .ctx_op_a(caller_op_a),.ctx_op_b(caller_op_b),.rsp_v(pio1[265]&&!view_fault),
   .rsp_row(pio1[263:256]),.out_v(joined_v),.out_row(rrow),.out_operation(rop),
   .pair_complete(),.fault(ctx_fault));
  assign rdata=pio1[255:0];assign {busy,arrive,released}=busy1;
  assign rv=joined_v&&!view_fault;assign ctx_ready=joined_ready&&!view_fault;
  assign fault=pio1[264]|ctx_fault|view_fault;
 end endgenerate
endmodule
