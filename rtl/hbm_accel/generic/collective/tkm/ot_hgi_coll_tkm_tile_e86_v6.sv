`timescale 1ns/1ps
// E86 V6 (STEWARD-HBM/IDX-E86 2026-10-21): v5 + KLEAF 1 (kept-leaf CREP select copies, split block compare). Same edges/ports.
module ot_hgi_coll_tkm_tile_e86_v6(
 input wire clk,clk_r0,clk_r1,clk_r2,clk_r3,input wire clr,conv,
 input wire ins_v,input wire [343:0] ins_b,output wire ovf_v,output wire [343:0] ovf_b,
 input wire [343:0] up_in,output wire [343:0] up_out,output wire busy);
 wire [84:0] tau_unused;
 ot_hgi_coll_tkm_tile_rg #(.EW(86),.PT(64),.PRE(1),.CREP(1),.FAN32(2),.SEAM(1),.LT_GROUP(5),.GCFOLD(1),.KLEAF(1)) u(
 .clk(clk),.clk_r0(clk_r0),.clk_r1(clk_r1),.clk_r2(clk_r2),.clk_r3(clk_r3),
 .tid(6'd0),.clr(clr),.conv(conv),.tau_t(6'd0),.tau_l(7'd0),
 .ins_v(ins_v),.ins_b(ins_b),.ovf_v(ovf_v),.ovf_b(ovf_b),.up_in(up_in),.up_out(up_out),.tau_o(tau_unused),.busy(busy));
endmodule
