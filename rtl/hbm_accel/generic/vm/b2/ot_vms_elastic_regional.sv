`timescale 1ns/1ps
`default_nettype none
// New physical candidate master, fixed D8. No old hard-view alias.
// Regional clocks must be source-matched same-phase clocks in the die contract.
module ot_vms_elastic_regional(
 input wire clk, input wire [8:0] data_clk, input wire rst_n,
 input wire [2223:0] f_in, output wire [2223:0] f_out,
 input wire [1:0] cr_in, output wire [1:0] cr_out);
 ot_vms_elastic u(.clk({data_clk,clk}),.rst_n(rst_n),
  .f_in(f_in),.f_out(f_out),.cr_in(cr_in),.cr_out(cr_out));
endmodule
`default_nettype wire
