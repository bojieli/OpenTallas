`timescale 1ns/1ps
// Pin-safe queue wrapper around the unchanged golden fence. PINRET=1 adds
// lane-local output registers and registered accepted-beat credit returns.
// PINRET=0 retains the previously benched p2 queue implementation. Added
// output latency is two clocks and peak output throughput one beat/four clocks.
module ot_gpu_rf_visibility_fence_p #(parameter integer MUT = 0, PINRET = 0, MUT_RETURN = 0) (   // MUT 1: bench mutant (cap_last dropped)
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
 ot_sc_pfifo #(.W(18), .S(2), .G(64)) u_op(.clk(clk),.rst_n(rn),.in_valid(op_valid),.in_ready(op_ready),.in_data({op_epoch,op_vectors}),
  .out_valid(i_op_v),.out_ready(i_op_r),.out_data({i_op_e,i_op_n}));
 wire i_cap_v,i_cap_r,i_cap_l; wire [7:0] i_cap_e; wire [8:0] i_cap_a; wire [4095:0] i_cap_d;
 ot_sc_pfifo #(.W(4114), .S(2), .G(128)) u_cap(.clk(clk),.rst_n(rn),.in_valid(cap_valid),.in_ready(cap_ready),
  .in_data({cap_epoch,cap_addr,cap_last,cap_data}),.out_valid(i_cap_v),.out_ready(i_cap_r),.out_data({i_cap_e,i_cap_a,i_cap_l,i_cap_d}));
 wire i_ack_v,i_ack_r; wire [0:0] i_ack_nd;
 ot_sc_pfifo #(.W(1), .S(2), .G(64)) u_ack(.clk(clk),.rst_n(rn),.in_valid(host_ack_valid),.in_ready(host_ack_ready),.in_data(1'b0),
  .out_valid(i_ack_v),.out_ready(i_ack_r),.out_data(i_ack_nd));
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
 // Default-off registered credit return and pin output register.
 generate if (PINRET) begin : g_pinret
 ot_fence_pin_return #(.W(4105), .MUT_RETURN(MUT_RETURN)) u_hw(
  .clk(clk),.rst_n(rn),.in_valid(w_hw_v),.in_ready(w_hw_r),.in_data({w_dst,w_wd}),
  .out_valid(host_wr_valid),.out_ready(host_wr_ready),.out_data({host_dst,host_wdata}));
 ot_fence_pin_return #(.W(8), .MUT_RETURN(MUT_RETURN)) u_fn(
  .clk(clk),.rst_n(rn),.in_valid(w_fv),.in_ready(w_fr),.in_data(w_fe),
  .out_valid(fence_valid),.out_ready(fence_ready),.out_data(fence_epoch));
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
 always @(posedge clk) begin vector_ACK_addr<=w_vaa;vector_ACK_epoch<=w_vae; end
endmodule
