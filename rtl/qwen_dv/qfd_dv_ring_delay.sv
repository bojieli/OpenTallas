`timescale 1ns/1ps
// Local finite ring for small scalar and station metadata delays (W<=32).
// Every three-edge segment is the shared, independently kept 24-bit chunk
// primitive: four slots, registered onehot write/read, no wide binary mux.
// A D=12 chain has four segments, D=9 has three. No flow control.
module qfd_dv_ring_delay #(parameter integer W=32,D=1,RESET=0)(
 input wire clk,rst_n,input wire[W-1:0] d,output wire[W-1:0] q
);
 generate if(D==0) begin:g_wire
  assign q=d;
 end else if(D==1) begin:g_one
  reg[W-1:0] data;
  always @(posedge clk) data<=d;
  assign q=data;
 end else begin:g_ring
  localparam integer N=D/3,C=(W+23)/24;
  wire local_reset;
  qfd_dv_reset_tree #(.N(1)) u_rt(.ck(clk),.rst_n(rst_n),.q(local_reset));
  wire[W-1:0] stage[0:N];
  assign stage[0]=d;
  for(genvar i=0;i<N;i=i+1) begin:g_stage
   wire[4*W-1:0] bank;
   wire[11:0] epo;
   wire[4*C-1:0] valid;
   ot_pl_land_chunk_w #(.W(W),.D(4),.CHUNK_BITS(24)) u_w(
    .ck(clk),.rsi(local_reset),.i(stage[i]),.bank(bank),.epo(epo),.vld(valid));
   ot_pl_land_chunk_r #(.W(W),.D(4),.K(2),.CHUNK_BITS(24)) u_r(
    .ck(clk),.rsi(local_reset),.bank(bank),.epo(epo),.vld(valid),.o(stage[i+1]));
  end
  assign q=stage[N];
 end endgenerate
`ifndef SYNTHESIS
 initial if(RESET!=0||(W<1||W>32)||D<0||(D>1&&(D%3!=0||D>12)))
  $fatal(1,"SAFE_RING_DELAY unsupported shape W=%0d D=%0d RESET=%0d",W,D,RESET);
`endif
endmodule
