`timescale 1ns/1ps
// Registered continuous SRAM read, NEW on a current logical same-address write.
// WREG=1 registers macro write pins; its previous logical write also forwards.
// Caller supplies ra = NEXT head and independent same-depth resets per16-bit slice.
// No reset/storage ECC is added to the SRAM. Two unconditional payload registers
// avoid a W-bit hit-enable cone; reset-distinct kept flags each select <=16 bits.
module ot_sram_showahead_1r1w #(
 parameter integer W=553, AW=3, WREG=1, NS=(W+15)/16, MUT=0
)(input wire clk, input wire [NS-1:0] rst_n,
 input wire we, input wire [AW-1:0] wa, input wire [W-1:0] wd,
 input wire [AW-1:0] ra, output wire [W-1:0] q);
 localparam integer NB=(W+127)/128;
 reg wv; reg [AW-1:0] waddr; reg [W-1:0] wdata, prevdata;
 always @(posedge clk or negedge rst_n[0]) if(!rst_n[0]) wv<=1'b0; else wv<=we;
 always @(posedge clk) begin waddr<=wa; wdata<=wd; prevdata<=wdata; end
 wire current_hit=we && wa==ra;
 wire previous_hit=(WREG!=0) && wv && waddr==ra;
 wire mw=(WREG!=0) ? wv : we;
 wire [AW-1:0] mwa=(WREG!=0) ? waddr : wa;
 wire [W-1:0] mwd=(WREG!=0) ? wdata : wd;
 wire [NB*128-1:0] padded={{(NB*128-W){1'b0}},mwd}, raw;
 genvar b,s;
 generate for(b=0;b<NB;b=b+1) begin:g_bank
  ot_sram_1r1w_32x128_m1 u_m(.clk(clk),.r_ce_in(1'b1),.r_addr_in(5'(ra)),
   .rd_out(raw[b*128+:128]),.w_ce_in(mw),.w_addr_in(5'(mwa)),
   .wd_in(padded[b*128+:128]),.w_mask_in({128{1'b1}}));
 end
 for(s=0;s<NS;s=s+1) begin:g_slice
  localparam integer LO=s*16, SW=(W-LO<16)?W-LO:16;
  (* keep="true" *) reg cur_q, prev_q;
  always @(posedge clk or negedge rst_n[s])
   if(!rst_n[s]) begin cur_q<=1'b0; prev_q<=1'b0; end
   else begin cur_q<=(MUT==1)?1'b0:current_hit; prev_q<=(MUT==2)?1'b0:previous_hit; end
  assign q[LO+:SW]=cur_q ? wdata[LO+:SW] : prev_q ? prevdata[LO+:SW] : raw[LO+:SW];
 end endgenerate
`ifndef SYNTHESIS
 initial begin
  if(AW>5 || AW<1 || W<1 || NS!=(W+15)/16) $fatal(1,"ot_sram_showahead_1r1w invalid shape");
 end
`endif
endmodule
