`timescale 1ns/1ps
`default_nettype none
// Dedicated bounded stage-control root; actual MACs and six memory leaves
// have their own clock roots. ML3/LA7/SOR1 descriptor semantics unchanged.
module ot_hgi_hc_bank_control_static(
 input wire clk,rst_n,
 input wire d_v,d_ss,
 input wire [5:0] d_nv,
 input wire [15:0] d_wa,d_xa,
 input wire f_in,
 input wire [3:0] lane_fault,
 input wire [5:0] memory_fault,
 output wire o_v,o_ss,
 output wire [5:0] o_nv,
 output wire [15:0] o_wa,o_xa,
 output reg f_out,
 output reg [31:0] lane_valid,lane_ss,
 output reg lane_go,
 output wire w_read_v,x_read_v,
 output wire [15:0] w_read_addr,x_read_addr
);
 localparam integer NC=8,ML=3,DW=40;
 reg [NC:0] cv;
 reg [DW-2:0] cd[0:NC];
 reg fin_q,w_re,x_re;
 reg [15:0] w_addr,x_addr;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin cv<=0;w_re<=0;x_re<=0;fin_q<=0;f_out<=0;lane_go<=0;end
  else begin
   cv<={cv[NC-1:0],d_v};
   w_re<=cv[0]&&!cd[0][DW-2];x_re<=cv[0];
   fin_q<=f_in;f_out<=fin_q||(|lane_fault)||(|memory_fault);
   lane_go<=cv[1+ML];
  end
 end
 wire [5:0] nv_p=cd[ML][DW-3-:6];
 always @(posedge clk)begin
  cd[0]<={d_ss,d_nv,d_wa,d_xa};
  for(integer j=1;j<=NC;j=j+1)cd[j]<=cd[j-1];
  w_addr<=cd[0][31:16];x_addr<=cd[0][15:0];
  for(integer l=0;l<32;l=l+1)begin
   lane_valid[l]<=cv[ML]&&(l<nv_p);lane_ss[l]<=cd[ML][DW-2];
  end
 end
 assign o_v=cv[8];assign {o_ss,o_nv,o_wa,o_xa}=cd[8];
 assign w_read_v=w_re;assign x_read_v=x_re;assign w_read_addr=w_addr;assign x_read_addr=x_addr;
endmodule
`default_nettype wire
