`timescale 1ns/1ps
// Private exact selected-anchor HWIN source; namespace projection only.
// HWIN21cb: the SRAM read address is a REGISTER (ra_r) loaded one edge earlier with the precomputed
// pointer-after-next (ra_d = inc(next pointer), built by the parent from registered state in parallel with
// the advance compare). No compare/advance logic sits between ra_r and r_addr_in. The capture register
// loads the SRAM word only when the head advanced last cycle (load_r = registered advance); otherwise it
// holds and takes same-address writes through current_hit. Public edges unchanged (cycle-exact miter).
module dsdv_mu_hwin_capture_1019_mem_early_capture #(parameter integer W=64, parameter integer AW=6, parameter integer N=(W+15)/16, parameter integer S=(W+7)/8, parameter integer RA_RESET=1)(
 input wire ck, we, input wire [S-1:0] rst_n, input wire [AW-1:0] wa, input wire [W-1:0] wd,
 input wire [AW-1:0] ra_current, ra_d, input wire load_d, output wire [W-1:0] q);
 reg wv; wire [S-1:0] hitq; reg [AW-1:0] waddr; reg [W-1:0] wdata, fd;
`ifndef EC_MUT
`define EC_MUT 0
`endif
 localparam integer MUT=`EC_MUT;
 (* keep *) reg [AW-1:0] ra_r;
 always @(posedge ck or negedge rst_n[0]) if(!rst_n[0]) ra_r<=AW'(RA_RESET); else ra_r<=ra_d;
 wire [AW-1:0] read_address=(MUT==1)?ra_current:(MUT==4)?ra_r+1'b1:ra_r;
 wire hit=wv && read_address==waddr;
 always @(posedge ck or negedge rst_n[0])
   if (!rst_n[0]) wv<=1'b0; else wv<=we;
 // Reset-distinct registered addresses keep event-bank ports physically independent.
 always @(posedge ck or negedge rst_n[0]) if(!rst_n[0]) waddr<={AW{1'b0}}; else waddr<=wa;
 always @(posedge ck) begin wdata<=wd; fd<=wdata; end
 wire [N*16-1:0] padded={{(N*16-W){1'b0}},wdata}, raw;
 wire [N*16-1:0] forwarded={{(N*16-W){1'b0}},fd}, picked;
 genvar k; generate
 for(k=0;k<S;k=k+1) begin:g_select
   localparam integer LO=8*k, SW=(W-LO<8)?W-LO:8;
   // Each reset-distinct select drives at most eight payload mux bits.
   (* keep *) reg hit_r, load_r;
   assign hitq[k]=hit_r;
   always @(posedge ck or negedge rst_n[k]) if(!rst_n[k]) hit_r<=1'b0; else hit_r<=hit;
   // One registered load-select copy per <=8 capture bits (reset-distinct, kept).
   always @(posedge ck or negedge rst_n[k]) if(!rst_n[k]) load_r<=1'b0; else load_r<=load_d;
   wire current_hit;
   (* keep=1,dont_touch=1 *) dsdv_mu_hwin_capture_1019_early_current_hit #(.AW(AW)) u_current_hit
       (.valid(wv),.current_address(ra_current),.write_address(waddr),.hit(current_hit));
   wire [SW-1:0] early_q=(MUT!=3 && hitq[k]) ? forwarded[LO+:SW] : raw[LO+:SW];
   reg [SW-1:0] capture;
   always @(posedge ck) capture <= (MUT!=2 && current_hit) ? wdata[LO+:SW] : load_r ? early_q : capture;
   assign picked[LO+:SW]=capture;
 end
 for(k=0;k<N;k=k+1) begin:g_bank
   ot_sram_1r1w_64x16_m1 u_m(.clk(ck), .r_ce_in(1'b1), .r_addr_in(6'(read_address)),
    .rd_out(raw[16*k+:16]), .w_ce_in(wv), .w_addr_in(6'(waddr)),
    .wd_in(padded[16*k+:16]), .w_mask_in(16'hffff));
 end endgenerate
 assign q=picked[W-1:0];
`ifndef SYNTHESIS
 initial if(AW>6) $fatal(1,"dsdv_mu_hwin_capture_1019_mem_early_capture requires depth <=64");
`endif
endmodule

module dsdv_mu_hwin_capture_1019_early_current_hit #(parameter integer AW=6)(
 input wire valid, input wire [AW-1:0] current_address,write_address, output wire hit);
 assign hit=valid && current_address==write_address;
endmodule
