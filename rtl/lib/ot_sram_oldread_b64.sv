`timescale 1ns/1ps
// S81-COLL bank64 (LEAD-S81 decision 10-19): registered-write, registered OLD-read memory on the 64-bit bank family
// (ot_sram_1r1w2c_256x64_m1: 34.584 x 41.352 um, 106 contacts on a 41.352 um face = 2.56 pins/um, <= 6/um rule).
// Same ports, parameters and caller-visible cycle behaviour as ot_sram_oldread_wreg (512x128 r2c2 banks, whose
// 219/218 contacts on 29.736 um = 7.4 pins/um violate the face-density rule):
//   * registered write port (valid / address per caller group, data shared), so every macro write pin is a flop;
//   * a read at edge n returns the word as it was BEFORE the logical write presented at edge n (OLD), and the word
//     written by the logical write of edge n-1 (still in the write register) is forwarded;
//   * q holds while the group's read enable is low.
// Storage: NB = ceil(W/64) bank columns x ND = 2^(AW-8) depth halves (AW 9: 2 x 256 rows).  The depth half of a read
// is registered per slice beside the forwarding select (hi_r), so the 2:1 depth merge is a registered one-hot select,
// <= SB loads per flop, no extra edge.  The macro read is SUPPRESSED when the registered write targets the same
// address in the same edge (the dual-clock macro leaves a same-address read/write undefined); that read is exactly
// the forwarded case, so the macro word is never used.  No ECC, no repair (academic-validation policy).
module ot_sram_oldread_b64 #(parameter integer W=553, AW=9, SB=16, GA=16, NS=(W+SB-1)/SB, NB=(W+63)/64, NA=(NS+GA-1)/GA, GROUP_IO=0, MUT=0)(
 input wire clk, input wire [NS-1:0] rst_n,
 input wire we, input wire [NA*AW-1:0] wa, input wire [W-1:0] wd,
 input wire re, input wire [NA*AW-1:0] ra, output wire [W-1:0] q,
 input wire [NA-1:0] we_group, re_group);
 localparam integer ND = (AW > 8) ? (1 << (AW - 8)) : 1;
 localparam integer BA = (AW > 8) ? 8 : AW;           // bank row address bits
 wire [NA-1:0] w_en=(GROUP_IO!=0)?we_group:{NA{we}};
 wire [NA-1:0] r_en=(GROUP_IO!=0)?re_group:{NA{re}};
 wire [NA-1:0] wvalid; wire [NA*AW-1:0] waddr; reg [W-1:0] wdata;
 always @(posedge clk) wdata<=wd;
 wire [NB*64-1:0] padded={{(NB*64-W){1'b0}},wdata};
 wire [NB*64-1:0] raw [0:ND-1];
 genvar b,s,a,d;
 generate for(a=0;a<NA;a=a+1) begin:g_address
   (* keep="true" *) reg [AW-1:0] address_r;
   reg valid_r; assign wvalid[a]=valid_r;
   always @(posedge clk or negedge rst_n[GA*a]) if(!rst_n[GA*a]) valid_r<=0;else valid_r<=w_en[a];
   assign waddr[a*AW+:AW]=address_r;
   always @(posedge clk or negedge rst_n[GA*a]) if(!rst_n[GA*a]) address_r<=0;else address_r<=wa[a*AW+:AW];
 end
 for(b=0;b<NB;b=b+1) begin:g_bank
   localparam integer G=(64*b)/(GA*SB);               // caller group owning this column's first bit
   wire [AW-1:0] rab=ra[AW*G+:AW], wab=waddr[AW*G+:AW];
   wire collide=wvalid[G] && (wab==rab);
   for(d=0;d<ND;d=d+1) begin:g_depth
     wire wsel=(ND==1) ? 1'b1 : (wab[AW-1:BA]==d);
     wire rsel=(ND==1) ? 1'b1 : (rab[AW-1:BA]==d);
     wire r_ce=r_en[G] && rsel && ((MUT==2) ? 1'b1 : !collide);
     wire w_ce=wvalid[G] && wsel;
     if(BA==8) begin:g_256
       ot_sram_1r1w2c_256x64_m1 u_m(.wclk(clk),.rclk(clk),.r_ce_in(r_ce),.r_addr_in(rab[7:0]),.rd_out(raw[d][64*b+:64]),
         .w_ce_in(w_ce),.w_addr_in(wab[7:0]),.wd_in(padded[64*b+:64]),.w_mask_in({64{1'b1}}));
     end else begin:g_small
       ot_sram_1r1w2c_256x64_m1 u_m(.wclk(clk),.rclk(clk),.r_ce_in(r_ce),.r_addr_in(8'(rab[BA-1:0])),.rd_out(raw[d][64*b+:64]),
         .w_ce_in(w_ce),.w_addr_in(8'(wab[BA-1:0])),.wd_in(padded[64*b+:64]),.w_mask_in({64{1'b1}}));
     end
`ifndef SYNTHESIS
     always @(posedge clk) if(rst_n[0] && r_ce && w_ce && rab[BA-1:0]==wab[BA-1:0])
       $fatal(1,"COLL_COLLISION_UNSAFE bank64 macro read/write same address bank%0d depth%0d",b,d);
`endif
   end
 end
 for(s=0;s<NS;s=s+1) begin:g_slice
   localparam integer LO=SB*s, SW=(W-LO<SB)?W-LO:SB;
   (* keep="true" *) reg valid_r,select_r,hi_r;
   (* keep="true" *) reg [AW-1:0] addr_r;
   reg [SW-1:0] forwarded;
   wire [AW-1:0] ras=ra[AW*(s/GA)+:AW];
   wire hit=(MUT==1)?1'b0:(valid_r && ras==addr_r);
   always @(posedge clk or negedge rst_n[s])
     if(!rst_n[s]) begin valid_r<=0;addr_r<=0;select_r<=0;hi_r<=0;end
     else begin
       valid_r<=w_en[s/GA];addr_r<=wa[AW*(s/GA)+:AW];
       if(r_en[s/GA]) begin select_r<=hit; hi_r<=(ND==1)?1'b0:ras[AW-1]; end
     end
   always @(posedge clk) if(r_en[s/GA] && hit) forwarded<=wdata[LO+:SW];
   wire [SW-1:0] word=(ND==1 || !hi_r) ? raw[0][LO+:SW] : raw[ND-1][LO+:SW];
   assign q[LO+:SW]=select_r?forwarded:word;
 end endgenerate
`ifndef SYNTHESIS
 initial if(AW>9 || W<1 || (SB!=8 && SB!=16) || GA<1 || ((64%(GA*SB))!=0 && ((GA*SB)%64)!=0))
   $fatal(1,"ot_sram_oldread_b64 requires 1..512 rows and 64-bit aligned groups");
`endif
endmodule
