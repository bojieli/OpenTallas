`timescale 1ns/1ps
// Pin-safe queue wrapper around the unchanged golden fence. PINRET=1 adds
// lane-local output registers and registered accepted-beat credit returns.
// PINRET=0 retains the previously benched p2 queue implementation. Added
// output latency is two clocks and peak output throughput one beat/four clocks.
// INPIN=1 (hgi-1010/idleB 2026-10-10, opt-in, default off): the op / cap / ack pin FIFOs capture their pins in bare
// pin flops (ot_sc_pfifo PINREG=2): routed fb-93f2ee279-lvt TT -42 was ONLY input -> reg (cap_valid -> 66 u_cap we
// copies, host_ack_valid -> u_ack.in_ready: 10-12 levels behind the 518 ps die-link input budget), reg2reg +137.
// +1 edge on each input queue; the fence holds one write outstanding, so the rate is unchanged.
// HOLDBUF=n (opt-in): n retained BUFx2 cells in front of every input data pin flop and behind every output data
// flop (FF hold -2..-3 on cap_data -> storage and u_fn.out_data -> fence_epoch): a hold floor by construction.
module ot_gpu_rf_visibility_fence_p #(parameter integer MUT = 0, PINRET = 0, MUT_RETURN = 0, INPIN = 0, HOLDBUF = 0) (   // MUT 1: bench mutant (cap_last dropped); MUT 3: INPIN reservation dropped
 input wire clk,rst_n,
 input wire op_valid,output wire op_ready,
 input wire [7:0] op_epoch,input wire [9:0] op_vectors,
 input wire cap_valid,output wire cap_ready,
 input wire [7:0] cap_epoch,input wire [8:0] cap_addr,
 input wire cap_last,input wire [4095:0] cap_data,
 input wire producer_done_valid,input wire [7:0] producer_done_epoch,
 output wire host_wr_valid,input wire host_wr_ready,
 output wire [8:0] host_dst,output wire [4095:0] host_wdata,
 input wire host_ack_valid,output wire host_ack_ready,
 input wire ack_retire_enable,
 output reg vector_ACK_visible,output reg [8:0] vector_ACK_addr,output reg [7:0] vector_ACK_epoch,
 output reg writes_visible,output wire fence_valid,input wire fence_ready,output wire [7:0] fence_epoch,
 output reg pending_write,output reg fault
);
 reg [1:0] rs;
 always @(posedge clk or negedge rst_n) if(!rst_n) rs<=2'b00; else rs<={rs[0],1'b1};
 wire rn=rs[1];
 // inputs
 localparam integer IPR = INPIN ? 2 : 0;
 wire [17:0] b_op_d; wire [4113:0] b_cap_d; wire [7:0] b_pd_e;
 generate if (HOLDBUF > 0) begin : g_hbi
  ot_s81_head_min_buffer #(.W(18), .ENABLE(1), .DEPTH(HOLDBUF)) u_hb_op(.d({op_epoch,op_vectors}), .q(b_op_d));
  ot_s81_head_min_buffer #(.W(4114), .ENABLE(1), .DEPTH(HOLDBUF)) u_hb_cap(.d({cap_epoch,cap_addr,cap_last,cap_data}), .q(b_cap_d));
  ot_s81_head_min_buffer #(.W(8), .ENABLE(1), .DEPTH(HOLDBUF)) u_hb_pd(.d(producer_done_epoch), .q(b_pd_e));
 end else begin : g_nhbi
  assign b_op_d = {op_epoch,op_vectors}; assign b_cap_d = {cap_epoch,cap_addr,cap_last,cap_data}; assign b_pd_e = producer_done_epoch;
 end endgenerate
 wire i_op_v,i_op_r; wire [7:0] i_op_e; wire [9:0] i_op_n;
 ot_sc_pfifo #(.W(18), .S(2), .G(64), .PINREG(IPR)) u_op(.clk(clk),.rst_n(rn),.in_valid(op_valid),.in_ready(op_ready),.in_data(b_op_d),
  .out_valid(i_op_v),.out_ready(i_op_r),.out_data({i_op_e,i_op_n}));
 wire i_cap_v,i_cap_r,i_cap_l; wire [7:0] i_cap_e; wire [8:0] i_cap_a; wire [4095:0] i_cap_d;
 ot_sc_pfifo #(.W(4114), .S(2), .G(128), .PINREG(IPR), .MUT(MUT == 3 ? 2 : 0)) u_cap(.clk(clk),.rst_n(rn),.in_valid(cap_valid),.in_ready(cap_ready),
  .in_data(b_cap_d),.out_valid(i_cap_v),.out_ready(i_cap_r),.out_data({i_cap_e,i_cap_a,i_cap_l,i_cap_d}));
 wire i_ack_v,i_ack_r; wire [0:0] i_ack_nd;
 ot_sc_pfifo #(.W(1), .S(2), .G(64), .PINREG(IPR)) u_ack(.clk(clk),.rst_n(rn),.in_valid(host_ack_valid),.in_ready(host_ack_ready),.in_data(1'b0),
  .out_valid(i_ack_v),.out_ready(i_ack_r),.out_data(i_ack_nd));
 reg i_pd_v,i_are; reg [7:0] i_pd_e;
 always @(posedge clk or negedge rn) if(!rn) begin i_pd_v<=0;i_are<=0; end else begin i_pd_v<=producer_done_valid;i_are<=ack_retire_enable; end
 always @(posedge clk) i_pd_e<=b_pd_e;
 // the original fence
 wire w_hw_v,w_hw_r,w_fv,w_fr,w_vav,w_wv,w_pw,w_f; wire [8:0] w_dst,w_vaa; wire [4095:0] w_wd; wire [7:0] w_vae,w_fe;
 ot_gpu_rf_visibility_fence #(.ENABLE(1)) u_f(.clk(clk),.rst_n(rn),
  .op_valid(i_op_v),.op_ready(i_op_r),.op_epoch(i_op_e),.op_vectors(i_op_n),
  .cap_valid(i_cap_v),.cap_ready(i_cap_r),.cap_epoch(i_cap_e),.cap_addr(i_cap_a),.cap_last(MUT == 1 ? 1'b0 : i_cap_l),.cap_data(i_cap_d),
  .producer_done_valid(i_pd_v),.producer_done_epoch(i_pd_e),
  .host_wr_valid(w_hw_v),.host_wr_ready(w_hw_r),.host_dst(w_dst),.host_wdata(w_wd),
  .host_ack_valid(i_ack_v),.host_ack_ready(i_ack_r),.ack_retire_enable(i_are),
  .vector_ACK_visible(w_vav),.vector_ACK_addr(w_vaa),.vector_ACK_epoch(w_vae),
  .writes_visible(w_wv),.fence_valid(w_fv),.fence_ready(w_fr),.fence_epoch(w_fe),.pending_write(w_pw),.fault(w_f));
 // Default-off registered credit return and pin output register.
 generate if (PINRET) begin : g_pinret
 wire [4104:0] o_hw_d; wire [7:0] o_fe;
 ot_fence_pin_return #(.W(4105), .MUT_RETURN(MUT_RETURN)) u_hw(
  .clk(clk),.rst_n(rn),.in_valid(w_hw_v),.in_ready(w_hw_r),.in_data({w_dst,w_wd}),
  .out_valid(host_wr_valid),.out_ready(host_wr_ready),.out_data(o_hw_d));
 ot_fence_pin_return #(.W(8), .MUT_RETURN(MUT_RETURN)) u_fn(
  .clk(clk),.rst_n(rn),.in_valid(w_fv),.in_ready(w_fr),.in_data(w_fe),
  .out_valid(fence_valid),.out_ready(fence_ready),.out_data(o_fe));
 if (HOLDBUF > 0) begin : g_hbo
  ot_s81_head_min_buffer #(.W(4105), .ENABLE(1), .DEPTH(1)) u_hb_hw(.d(o_hw_d), .q({host_dst,host_wdata}));
  ot_s81_head_min_buffer #(.W(8), .ENABLE(1), .DEPTH(1)) u_hb_fe(.d(o_fe), .q(fence_epoch));
 end else begin : g_nhbo
  assign {host_dst,host_wdata} = o_hw_d; assign fence_epoch = o_fe;
 end
 end else begin : g_old
 // outputs
 ot_sc_pfifo #(.W(4105), .S(2), .G(128)) u_hw(.clk(clk),.rst_n(rn),.in_valid(w_hw_v),.in_ready(w_hw_r),.in_data({w_dst,w_wd}),
  .out_valid(host_wr_valid),.out_ready(host_wr_ready),.out_data({host_dst,host_wdata}));
 ot_sc_pfifo #(.W(8), .S(2), .G(64)) u_fn(.clk(clk),.rst_n(rn),.in_valid(w_fv),.in_ready(w_fr),.in_data(w_fe),
  .out_valid(fence_valid),.out_ready(fence_ready),.out_data(fence_epoch));
 end endgenerate
 always @(posedge clk or negedge rn)
  if(!rn) begin vector_ACK_visible<=0;writes_visible<=0;pending_write<=0;fault<=0; end
  else begin vector_ACK_visible<=w_vav;writes_visible<=w_wv;pending_write<=w_pw;fault<=w_f; end
 reg [8:0] vq_a; reg [7:0] vq_e;
 always @(posedge clk) begin vq_a<=w_vaa;vq_e<=w_vae; end
 generate if (HOLDBUF > 0) begin : g_hbv
  wire [16:0] vb;
  ot_s81_head_min_buffer #(.W(17), .ENABLE(1), .DEPTH(1)) u_hb_va(.d({vq_a,vq_e}), .q(vb));
  always @* {vector_ACK_addr,vector_ACK_epoch} = vb;
 end else begin : g_nhbv
  always @* begin vector_ACK_addr = vq_a; vector_ACK_epoch = vq_e; end
 end endgenerate
endmodule
