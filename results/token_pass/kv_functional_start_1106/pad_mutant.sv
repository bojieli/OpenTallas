`timescale 1ns/1fs
module start_pad_mutant (
input wire clk,
input wire rraw_R,
input wire rs_R,
output wire pst_D
);
wire se23ca092adc8f9e5_start;
wire se23ca092adc8f9e5_raw;
ot_die_start_reset_relay_pad #(.EDGE_FALL(0)) r_se23ca092adc8f9e5(.clk(clk),.d(rraw_R),.q(se23ca092adc8f9e5_raw));
ot_dp_landing_origin #(.PAD(0),.EDGE_FALL(0)) u_se23ca092adc8f9e5(.clk(clk),.rst_raw_n(se23ca092adc8f9e5_raw),.p_start(rs_R),.start(se23ca092adc8f9e5_start));
wire s1e86f15dd1adadf5_start;
wire s1e86f15dd1adadf5_raw;
ot_die_start_reset_relay_pad #(.EDGE_FALL(1)) r_s1e86f15dd1adadf5(.clk(clk),.d(se23ca092adc8f9e5_raw),.q(s1e86f15dd1adadf5_raw));
ot_dp_landing_origin #(.PAD(0),.EDGE_FALL(1)) u_s1e86f15dd1adadf5(.clk(clk),.rst_raw_n(s1e86f15dd1adadf5_raw),.p_start(se23ca092adc8f9e5_start),.start(s1e86f15dd1adadf5_start));
assign pst_D=s1e86f15dd1adadf5_start;
endmodule
module ot_die_start_reset_relay_pad #(parameter bit EDGE_FALL=0)(input wire clk,input wire d,output wire q);
reg r0,r1;wire x;
if(EDGE_FALL) begin:gf reg rf;always@(negedge clk)rf<=d;assign x=rf;end else begin:gr assign x=d;end
always@(posedge clk)begin r0<=x;r1<=r0;end
assign q=r1;endmodule
