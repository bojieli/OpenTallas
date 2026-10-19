`timescale 1ns/1ps
// Registered-write, registered OLD-read memory. q holds when re=0, exactly
// ot_s81ph_mem1r1w WREG1. Reset-distinct16-bit forwarding slices prevent shared
// enabled payload muxes and output selects. SB8/GA4 opt-in gives four8-bit
// slices per independent caller-owned we/re/address group. GROUP_IO0 retains
// scalar we/re semantics; callers still supply same-edge replicated addresses.
// No additional write/read edges.
module ot_sram_oldread_wreg #(parameter integer W=553, AW=9, SB=16, GA=16, NS=(W+SB-1)/SB, NB=(W+127)/128, NA=(NS+GA-1)/GA, GROUP_IO=0, MUT=0)(
 input wire clk, input wire [NS-1:0] rst_n,
 input wire we, input wire [NA*AW-1:0] wa, input wire [W-1:0] wd,
 input wire re, input wire [NA*AW-1:0] ra, output wire [W-1:0] q,
 input wire [NA-1:0] we_group, re_group);
 wire [NA-1:0] w_en=(GROUP_IO!=0)?we_group:{NA{we}};
 wire [NA-1:0] r_en=(GROUP_IO!=0)?re_group:{NA{re}};
 wire [NA-1:0] wvalid; wire [NA*AW-1:0] waddr; reg [W-1:0] wdata;
 always @(posedge clk) wdata<=wd;
 wire [NB*128-1:0] padded={{(NB*128-W){1'b0}},wdata},raw;
 genvar b,s,a;
 generate for(a=0;a<NA;a=a+1) begin:g_address
   (* keep="true" *) reg [AW-1:0] address_r;
   reg valid_r; assign wvalid[a]=valid_r;
   always @(posedge clk or negedge rst_n[GA*a]) if(!rst_n[GA*a]) valid_r<=0;else valid_r<=w_en[a];
   assign waddr[a*AW+:AW]=address_r;
   always @(posedge clk or negedge rst_n[GA*a]) if(!rst_n[GA*a]) address_r<=0;else address_r<=wa[a*AW+:AW];
 end
 for(b=0;b<NB;b=b+1) begin:g_bank
   ot_sram_1r1w_512x128_m4_r2c2 u_m(.clk(clk),.r_ce_in(r_en[(128*b)/(GA*SB)]),.r_addr_in(9'(ra[AW*((128*b)/(GA*SB))+:AW])),.rd_out(raw[128*b+:128]),
     .w_ce_in(wvalid[(128*b)/(GA*SB)]),.w_addr_in(9'(waddr[AW*((128*b)/(GA*SB))+:AW])),.wd_in(padded[128*b+:128]),.w_mask_in({128{1'b1}}),
     .rr_en(2'b00),.rr_addr(14'd0),.cr_en(2'b00),.cr_sel(14'd0));
 end
 for(s=0;s<NS;s=s+1) begin:g_slice
   localparam integer LO=SB*s, SW=(W-LO<SB)?W-LO:SB;
   (* keep="true" *) reg valid_r,select_r;
   (* keep="true" *) reg [AW-1:0] addr_r;
   reg [SW-1:0] forwarded;
   wire hit=(MUT==1)?1'b0:(valid_r && ra[AW*(s/GA)+:AW]==addr_r);
   always @(posedge clk or negedge rst_n[s])
     if(!rst_n[s]) begin valid_r<=0;addr_r<=0;select_r<=0;end
     else begin valid_r<=w_en[s/GA];addr_r<=wa[AW*(s/GA)+:AW];if(r_en[s/GA]) select_r<=hit;end
   always @(posedge clk) if(r_en[s/GA] && hit) forwarded<=wdata[LO+:SW];
   assign q[LO+:SW]=select_r?forwarded:raw[LO+:SW];
 end endgenerate
`ifndef SYNTHESIS
 initial if(AW>9 || W<1 || (SB!=8 && SB!=16) || GA<1 || ((128%(GA*SB))!=0 && ((GA*SB)%128)!=0)) $fatal(1,"oldread memory requires1..512rows");
`endif
endmodule
