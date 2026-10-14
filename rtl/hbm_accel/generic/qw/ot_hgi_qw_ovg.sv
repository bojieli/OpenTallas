`timescale 1ns/1ps
`default_nettype none
// No-macro gather leaf. Existing gather pin registers, OR4 output register and
// launch/header registers are reassigned without adding a pipeline edge.
module ot_hgi_qw_ovg (
 input wire clk, rst_n,
 input wire [1023:0] l_gp0, l_gp1, l_gp2, l_gp3,
 input wire c_gv,
 input wire [17:0] c_gh,
 output wire dec_rst_n,
 output reg x_v,
 output reg [17:0] x_hd,
 output reg [1023:0] x
);
 reg f_rst; always @(posedge clk) f_rst <= rst_n;
 wire [2:0] rr_n;
 ot_rst_relay #(.REGIONS(3)) u_rst (.clk(clk), .rst_n_in(f_rst), .rst_n(rr_n));
 assign dec_rst_n = rr_n[2];
 always @(posedge clk or negedge rr_n[0])
  if (!rr_n[0]) x_v <= 0; else x_v <= c_gv;
 reg [1023:0] gpf [0:3];
 always @(posedge clk) begin
  x_hd <= c_gh;
  gpf[0] <= l_gp0; gpf[1] <= l_gp1; gpf[2] <= l_gp2; gpf[3] <= l_gp3;
  x <= (gpf[0] | gpf[1]) | (gpf[2] | gpf[3]);
 end
endmodule
`default_nettype wire
