`timescale 1ns/1ps
// Small 1R1W SRAM banks with registered write pins and exact registered OLD-data read.
// A read after the previous cycle write forwards its registered payload. No schedule cycles added.
module dsdv_mu_mem_early_capture #(parameter integer W=64, parameter integer AW=6, parameter integer N=(W+15)/16, parameter integer S=(W+7)/8)(
 input wire ck, we, input wire [S-1:0] rst_n, input wire [AW-1:0] wa, input wire [W-1:0] wd,
 input wire [AW-1:0] ra_current, ra_next, output wire [W-1:0] q);
 reg wv; wire [S-1:0] hitq; reg [AW-1:0] waddr; reg [W-1:0] wdata, fd;
`ifndef EC_MUT
`define EC_MUT 0
`endif
 localparam integer MUT=`EC_MUT;
 wire [AW-1:0] read_address=(MUT==1)?ra_current:(MUT==4)?ra_next+1'b1:ra_next;
 wire hit=wv && read_address==waddr;
 always @(posedge ck or negedge rst_n[0])
   if (!rst_n[0]) wv<=1'b0; else wv<=we;
 // Reset-distinct registered addresses keep event-bank ports physically independent.
 always @(posedge ck or negedge rst_n[0]) if(!rst_n[0]) waddr<={AW{1'b0}}; else waddr<=wa;
 always @(posedge ck) begin wdata<=wd; fd<=wdata; end
 wire [N*16-1:0] padded, raw;
 assign padded={{(N*16-W){1'b0}},wdata};
 wire [N*16-1:0] forwarded, picked;
 assign forwarded={{(N*16-W){1'b0}},fd};
 genvar k; generate
 for(k=0;k<S;k=k+1) begin:g_select
   localparam integer LO=8*k, SW=(W-LO<8)?W-LO:8;
   // Each reset-distinct select drives at most eight payload mux bits.
   (* keep *) reg hit_r;
   assign hitq[k]=hit_r;
   always @(posedge ck or negedge rst_n[k]) if(!rst_n[k]) hit_r<=1'b0; else hit_r<=hit;
   wire current_hit;
   (* keep=1,dont_touch=1 *) dsdv_mu_early_current_hit #(.AW(AW)) u_current_hit
       (.valid(wv),.current_address(ra_current),.write_address(waddr),.hit(current_hit));
   wire [SW-1:0] early_q=(MUT!=3 && hitq[k]) ? forwarded[LO+:SW] : raw[LO+:SW];
   reg [SW-1:0] capture;
   always @(posedge ck) capture <= (MUT!=2 && current_hit) ? wdata[LO+:SW] : early_q;
   assign picked[LO+:SW]=capture;
 end
 for(k=0;k<N;k=k+1) begin:g_bank
   ot_sram_1r1w_64x16_m1 u_m(.clk(ck), .r_ce_in(1'b1), .r_addr_in(6'(read_address)),
    .rd_out(raw[16*k+:16]), .w_ce_in(wv), .w_addr_in(6'(waddr)),
    .wd_in(padded[16*k+:16]), .w_mask_in(16'hffff));
 end endgenerate
 assign q=picked[W-1:0];
`ifndef SYNTHESIS
 initial if(AW>6) $fatal(1,"dsdv_mu_mem_early_capture requires depth <=64");
`endif
endmodule

// Separate kept predicate identities cap each output at eight capture mux bits.
// Upstream address/valid loads still require native mapping census before any gate.
module dsdv_mu_early_current_hit #(parameter integer AW=6)(
 input wire valid, input wire [AW-1:0] current_address,write_address, output wire hit);
 assign hit=valid && current_address==write_address;
endmodule
