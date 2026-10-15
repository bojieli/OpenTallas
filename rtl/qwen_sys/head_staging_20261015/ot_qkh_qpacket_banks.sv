`timescale 1ns/1ps
// Actual recipe-2 area requires two physical banks for Q519. The low bank
// carries {Q[255:0],beat[5:0],valid}; the high bank carries Q[511:256].
// Both advance on the same compiler edge, with independently compensated roots.
module ot_qkh_qpacket_banks #(parameter integer MUT=0)(
 input wire clk_lo,clk_hi,rst_n,
 input wire [518:0] d,
 output wire [518:0] q
);
 ot_qkh_packet_pipe #(.W(263),.MUT(MUT==1?1:0)) u_low
   (.clk(clk_lo),.rst_n(rst_n),.d(d[262:0]),.q(q[262:0]));
 ot_qkh_packet_pipe #(.W(256),.MUT(MUT==2?2:0)) u_high
   (.clk(clk_hi),.rst_n(rst_n),.d(d[518:263]),.q(q[518:263]));
endmodule

module ot_qkh_qpacket_fork2 #(parameter integer MUT=0)(
 input wire clk0_lo,clk0_hi,clk1_lo,clk1_hi,rst_n,
 input wire [518:0] d,
 output wire [518:0] q0,q1
);
 ot_qkh_qpacket_banks #(.MUT(MUT)) u_branch0
   (.clk_lo(clk0_lo),.clk_hi(clk0_hi),.rst_n(rst_n),.d(d),.q(q0));
 ot_qkh_qpacket_banks u_branch1
   (.clk_lo(clk1_lo),.clk_hi(clk1_hi),.rst_n(rst_n),.d(d),.q(q1));
endmodule
