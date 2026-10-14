`timescale 1ns/1ps
`default_nettype none
// Five128-bit command words. Capture the command pins before constant-index
// local bank enables; all640coefficient outputs are registered and retained.
module ot_hgi_hc_coeff_bank(
 input wire clk,rst_n,wr_v,input wire[2:0]wr_index,input wire[127:0]wr_data,
 output reg[127:0]coef0,coef1,coef2,coef3,coef4
);
 wire[0:0]rn;ot_rst_relay #(.REGIONS(1))u_rst(.clk(clk),.rst_n_in(rst_n),.rst_n(rn));
 reg vq;reg[2:0]iq;reg[127:0]dq;
 always @(posedge clk)begin iq<=wr_index;dq<=wr_data;end
 always @(posedge clk or negedge rn[0])if(!rn[0])vq<=0;else vq<=wr_v;
 always @(posedge clk)if(vq)begin
  if(iq==0)coef0<=dq;
  if(iq==1)coef1<=dq;
  if(iq==2)coef2<=dq;
  if(iq==3)coef3<=dq;
  if(iq==4)coef4<=dq;
 end
endmodule
// Test-only operand association mutant; the production master has no overrides.
module ot_hgi_hc_coeff_bank_assoc_mut(
 input wire clk,rst_n,wr_v,input wire[2:0]wr_index,input wire[127:0]wr_data,
 output wire[127:0]coef0,coef1,coef2,coef3,coef4
);
 wire[127:0]bad={wr_data[127:64],wr_data[31:0],wr_data[63:32]};
 ot_hgi_hc_coeff_bank u(.clk(clk),.rst_n(rst_n),.wr_v(wr_v),.wr_index(wr_index),.wr_data(bad),.*);
endmodule
`default_nettype wire
