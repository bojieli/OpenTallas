`timescale 1ns/1ps
`default_nettype none
// Scalar physical entry pins expose seven related roots. Each macro source
// reaches exactly one SRAM provider; clk reaches the request/write boundary registers and clk_rd (r7, read face)
// the read-data / return output registers.
module ot_hbm_su_static_bank6_clock_physical #(parameter integer MUT_COHERENCE=0,MUT_RETURN=0)(
 input wire clk,clk_rd,clk_macro0,clk_macro1,clk_macro2,clk_macro3,clk_macro4,clk_macro5,rst_n,
 input wire[5:0]read_v,input wire[53:0]read_addr,
 output wire[191:0]read_data,output wire[5:0]read_return,
 input wire write_v,input wire[8:0]write_addr,input wire[31:0]write_data
);
 ot_hbm_su_static_pinned_bank #(.READERS(6),.RB(9),.MUT_COHERENCE(MUT_COHERENCE),.MUT_RETURN(MUT_RETURN),.RD_ROOT(1))u_bank(
  .clk(clk),.clk_rd(clk_rd),.clk_macro({clk_macro5,clk_macro4,clk_macro3,clk_macro2,clk_macro1,clk_macro0}),.rst_n(rst_n),
  .read_v(read_v),.read_addr(read_addr),.read_data(read_data),.read_return(read_return),
  .write_v(write_v),.write_addr(write_addr),.write_data(write_data));
endmodule
`default_nettype wire
