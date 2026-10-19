`timescale 1ns/1ps
// Small 1R1W SRAM banks with registered write pins and exact registered OLD-data read.
// A read after the previous cycle write forwards its registered payload. No schedule cycles added.
module dsdv_mu_mem #(parameter integer W=64, parameter integer AW=6, parameter integer N=(W+15)/16)(
 input wire ck, we, input wire [N-1:0] rst_n, input wire [AW-1:0] wa, input wire [W-1:0] wd,
 input wire [AW-1:0] ra, output wire [W-1:0] q);
 reg wv; wire [N-1:0] hitq; reg [AW-1:0] waddr; reg [W-1:0] wdata, fd;
 wire hit=wv && ra==waddr;
 always @(posedge ck or negedge rst_n[0])
   if (!rst_n[0]) wv<=1'b0; else wv<=we;
 always @(posedge ck) begin waddr<=wa; wdata<=wd; fd<=wdata; end
 wire [N*16-1:0] padded={{(N*16-W){1'b0}},wdata}, raw;
 wire [N*16-1:0] forwarded={{(N*16-W){1'b0}},fd}, picked;
 genvar k; generate for(k=0;k<N;k=k+1) begin:g_bank
   // Reset-distinct select copies cannot merge; each drives at most16data-bitmuxes.
   (* keep *) reg hit_r;
   assign hitq[k]=hit_r;
   always @(posedge ck or negedge rst_n[k]) if(!rst_n[k]) hit_r<=1'b0; else hit_r<=hit;
   assign picked[16*k+:16]=hitq[k] ? forwarded[16*k+:16] : raw[16*k+:16];
   ot_sram_1r1w_64x16_m1 u_m(.clk(ck), .r_ce_in(1'b1), .r_addr_in(6'(ra)),
    .rd_out(raw[16*k+:16]), .w_ce_in(wv), .w_addr_in(6'(waddr)),
    .wd_in(padded[16*k+:16]), .w_mask_in(16'hffff));
 end endgenerate
 assign q=picked[W-1:0];
`ifndef SYNTHESIS
 initial if(AW>6) $fatal(1,"dsdv_mu_mem requires depth <=64");
`endif
endmodule
