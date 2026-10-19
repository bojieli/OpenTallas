// Fixed N-edge alignment through SRAM; no credit, ready or backpressure.
// Every edge writes one residue and reads the next residue. The synchronous
// read returns the word N-1 sample intervals old, exactly N register stages.
`timescale 1ns/1ps
`default_nettype none
module hnx_pl_pad_sram #(parameter integer W=818, N=3, MUT=0) (
 input wire ck, rst_n,
 input wire [W-1:0] d,
 output wire [W-1:0] q
);
 localparam integer NB=(W+255)/256;
 localparam integer AW=(N<=2)?1:$clog2(N);
 reg [AW-1:0] phase;
 wire [AW-1:0] next_phase=(phase==N-1)?0:phase+1'b1;
 wire [6:0] wa=phase;
 wire [6:0] ra=(MUT==1)?phase:next_phase;
 wire [NB*256-1:0] wd={{(NB*256-W){1'b0}},d};
 wire [NB*256-1:0] rd;
 always @(posedge ck) begin
  if (!rst_n) phase<=0;
  else phase<=next_phase;
 end
 genvar b;
 generate for(b=0;b<NB;b=b+1) begin:g_bank
  ot_sram_1r1w_128x256_m1_r2c2 u_mem (
   .clk(ck),.r_ce_in(rst_n),.r_addr_in(ra),.rd_out(rd[b*256+:256]),
   .w_ce_in(rst_n),.w_addr_in(wa),.wd_in(wd[b*256+:256]),
   .w_mask_in({256{1'b1}}),.rr_en(2'b0),.rr_addr(14'b0),
   .cr_en(2'b0),.cr_sel(16'b0));
 end endgenerate
 assign q=rd[W-1:0];
 initial begin
  if(N<2 || N>128 || W<1) $fatal(1,"HNXPAD invalid shape");
 end
endmodule
`default_nettype wire
