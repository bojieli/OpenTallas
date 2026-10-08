`timescale 1ns/1ps
// Actual D1 replacement for one slot removed from the upstream D35 ring.
// No extra total delay slot; valid reset and enabled data match original D1.
module ot_ha2_hub_launch_single #(parameter integer W=544, INJ=2)(
 input wire clk,rst_n,input wire[INJ-1:0] v_in,
 input wire[INJ*W-1:0] d_in,output wire[INJ-1:0] v_out,
 output wire[INJ*W-1:0] d_out,output wire quiet);
 wire[INJ-1:0] q;
 for(genvar i=0;i<INJ;i=i+1)begin:g_lane
  ot_ha2_delay_quiet #(.W(W),.D(1)) u_delay
   (.clk(clk),.rst_n(rst_n),.v_in(v_in[i]),.d_in(d_in[i*W+:W]),
    .v_out(v_out[i]),.d_out(d_out[i*W+:W]),.quiet(q[i]));
 end
 assign quiet=&q;
endmodule
