`timescale 1ns/1ps
// mtp-hbm 2026-10-08: pipeline-cut variant of ot_gpu_rf_visibility_fence (ENABLE = 1) for die-pin timing.
// fence_a1 (10-05) re-STA under the current IO model: internal reg->reg +258 ps TT, but in->out FEEDTHROUGH paths
// (cap_addr -> cap_legal compare -> host_wr_valid, -613.6 ps TT against the consistent die-link split; cap_data ->
// host_wdata is a 4,096-bit wire) cannot close at any IO budget.  Fix (template D, transaction-level exact): the
// ORIGINAL module, unmodified, between registered slices:
//   op_* / cap_* / host_ack in:  ot_hfd_mtp_skid (ready from a flop, data into a flop)
//   host_wr / fence out:          ot_hfd_mtp_skid (valid and data from flops)
//   every other input / output:   one flop at the pin.
// Same writes, ACKs, fences and faults in the same order; +1 cycle on each crossing (capture->write +2, ACK
// visibility +2, fence +1).
module ot_gpu_rf_visibility_fence_p #(parameter integer MUT = 0) (   // MUT 1: bench mutant (cap_last dropped)
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
 wire i_op_v,i_op_r; wire [7:0] i_op_e; wire [9:0] i_op_n;
 ot_hfd_mtp_skid #(.W(18)) u_op(.clk(clk),.rst_n(rn),.in_v(op_valid),.in_ready(op_ready),.in_d({op_epoch,op_vectors}),
  .out_v(i_op_v),.out_ready(i_op_r),.out_d({i_op_e,i_op_n}));
 wire i_cap_v,i_cap_r,i_cap_l; wire [7:0] i_cap_e; wire [8:0] i_cap_a; wire [4095:0] i_cap_d;
 ot_hfd_mtp_skid #(.W(4114)) u_cap(.clk(clk),.rst_n(rn),.in_v(cap_valid),.in_ready(cap_ready),
  .in_d({cap_epoch,cap_addr,cap_last,cap_data}),.out_v(i_cap_v),.out_ready(i_cap_r),.out_d({i_cap_e,i_cap_a,i_cap_l,i_cap_d}));
 wire i_ack_v,i_ack_r; wire [0:0] i_ack_nd;
 ot_hfd_mtp_skid #(.W(1)) u_ack(.clk(clk),.rst_n(rn),.in_v(host_ack_valid),.in_ready(host_ack_ready),.in_d(1'b0),
  .out_v(i_ack_v),.out_ready(i_ack_r),.out_d(i_ack_nd));
 reg i_pd_v,i_are; reg [7:0] i_pd_e;
 always @(posedge clk or negedge rn) if(!rn) begin i_pd_v<=0;i_are<=0; end else begin i_pd_v<=producer_done_valid;i_are<=ack_retire_enable; end
 always @(posedge clk) i_pd_e<=producer_done_epoch;
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
 // outputs
 ot_hfd_mtp_skid #(.W(4105)) u_hw(.clk(clk),.rst_n(rn),.in_v(w_hw_v),.in_ready(w_hw_r),.in_d({w_dst,w_wd}),
  .out_v(host_wr_valid),.out_ready(host_wr_ready),.out_d({host_dst,host_wdata}));
 ot_hfd_mtp_skid #(.W(8)) u_fn(.clk(clk),.rst_n(rn),.in_v(w_fv),.in_ready(w_fr),.in_d(w_fe),
  .out_v(fence_valid),.out_ready(fence_ready),.out_d(fence_epoch));
 always @(posedge clk or negedge rn)
  if(!rn) begin vector_ACK_visible<=0;writes_visible<=0;pending_write<=0;fault<=0; end
  else begin vector_ACK_visible<=w_vav;writes_visible<=w_wv;pending_write<=w_pw;fault<=w_f; end
 always @(posedge clk) begin vector_ACK_addr<=w_vaa;vector_ACK_epoch<=w_vae; end
endmodule
