`timescale 1ns/1ps
// Registered-write, registered OLD-read memory. q holds when re=0, exactly
// ot_s81ph_mem1r1w WREG1. Reset-distinct16-bit forwarding slices prevent shared
// enabled payload muxes and output selects. No additional write/read edges.
module ot_sram_oldread_wreg #(parameter integer W=553, AW=9, NS=(W+15)/16, NB=(W+127)/128, NA=(NS+15)/16, MUT=0)(
 input wire clk, input wire [NS-1:0] rst_n,
 input wire we, input wire [NA*AW-1:0] wa, input wire [W-1:0] wd,
 input wire re, input wire [NA*AW-1:0] ra, output wire [W-1:0] q);
 reg wv; wire [NA*AW-1:0] waddr; reg [W-1:0] wdata;
 always @(posedge clk or negedge rst_n[0]) if(!rst_n[0]) wv<=0;else wv<=we;
 always @(posedge clk) wdata<=wd;
 wire [NB*128-1:0] padded={{(NB*128-W){1'b0}},wdata},raw;
 genvar b,s,a;
 generate for(a=0;a<NA;a=a+1) begin:g_address
   (* keep="true" *) reg [AW-1:0] address_r;
   assign waddr[a*AW+:AW]=address_r;
   always @(posedge clk or negedge rst_n[16*a]) if(!rst_n[16*a]) address_r<=0;else address_r<=wa[a*AW+:AW];
 end
 for(b=0;b<NB;b=b+1) begin:g_bank
   ot_sram_1r1w_512x128_m4_r2c2 u_m(.clk(clk),.r_ce_in(re),.r_addr_in(9'(ra[AW*(b/2)+:AW])),.rd_out(raw[128*b+:128]),
     .w_ce_in(wv),.w_addr_in(9'(waddr[AW*(b/2)+:AW])),.wd_in(padded[128*b+:128]),.w_mask_in({128{1'b1}}),
     .rr_en(2'b00),.rr_addr(14'd0),.cr_en(2'b00),.cr_sel(14'd0));
 end
 for(s=0;s<NS;s=s+1) begin:g_slice
   localparam integer LO=16*s, SW=(W-LO<16)?W-LO:16;
   (* keep="true" *) reg valid_r,select_r;
   (* keep="true" *) reg [AW-1:0] addr_r;
   reg [SW-1:0] forwarded;
   wire hit=(MUT==1)?1'b0:(valid_r && ra[AW*(s/16)+:AW]==addr_r);
   always @(posedge clk or negedge rst_n[s])
     if(!rst_n[s]) begin valid_r<=0;addr_r<=0;select_r<=0;end
     else begin valid_r<=we;addr_r<=wa[AW*(s/16)+:AW];if(re) select_r<=hit;end
   always @(posedge clk) if(re && hit) forwarded<=wdata[LO+:SW];
   assign q[LO+:SW]=select_r?forwarded:raw[LO+:SW];
 end endgenerate
`ifndef SYNTHESIS
 initial if(AW>9 || W<1) $fatal(1,"oldread memory requires1..512rows");
`endif
endmodule
