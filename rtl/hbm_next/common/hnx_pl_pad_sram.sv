// Fixed N-edge alignment through SRAM; no credit, ready or backpressure.
// Every edge writes one residue and reads the next residue. The synchronous
// read returns the word N-1 sample intervals old, exactly N register stages.
`timescale 1ns/1ps
`default_nettype none
module hnx_pl_pad_sram #(parameter integer W=818, N=3, MUT=0, SMALL=0, OUTREG=0, INREG=0) (
 input wire ck, rst_n,
 input wire [W-1:0] d,
 output wire [W-1:0] q
);
 localparam integer MB=SMALL?128:256;
 localparam integer NB=(W+MB-1)/MB;
 localparam integer MN=N-OUTREG-INREG;
 localparam integer AW=(MN<=2)?1:$clog2(MN);
 reg [AW-1:0] phase;
 wire [AW-1:0] next_phase=(phase==MN-1)?0:phase+1'b1;
 wire [6:0] wa=phase;
 wire [6:0] ra=(MUT==1)?phase:next_phase;
 wire [W-1:0] din;
 generate if(INREG) begin:g_in
  reg [W-1:0] dreg;
  always @(posedge ck) dreg<=d;
  assign din=dreg;
 end else begin:g_direct_in
  assign din=d;
 end endgenerate
 wire [NB*MB-1:0] wd={{(NB*MB-W){1'b0}},din};
 wire [NB*MB-1:0] rd;
 always @(posedge ck) begin
  if (!rst_n) phase<=0;
  else phase<=next_phase;
 end
 genvar b;
 generate for(b=0;b<NB;b=b+1) begin:g_bank
  if(SMALL) begin:g_small
   ot_sram_1r1w_32x128_m1 u_mem (
    .clk(ck),.r_ce_in(rst_n),.r_addr_in(ra[4:0]),.rd_out(rd[b*128+:128]),
    .w_ce_in(rst_n),.w_addr_in(wa[4:0]),.wd_in(wd[b*128+:128]),.w_mask_in({128{1'b1}}));
  end else begin:g_large
   ot_sram_1r1w_128x256_m1_r2c2 u_mem (
    .clk(ck),.r_ce_in(rst_n),.r_addr_in(ra),.rd_out(rd[b*256+:256]),
    .w_ce_in(rst_n),.w_addr_in(wa),.wd_in(wd[b*256+:256]),
    .w_mask_in({256{1'b1}}),.rr_en(2'b0),.rr_addr(14'b0),
    .cr_en(2'b0),.cr_sel(16'b0));
  end
 end endgenerate
 generate if(OUTREG) begin:g_out
  reg [W-1:0] qreg;
  always @(posedge ck) qreg<=rd[W-1:0];
  assign q=qreg;
 end else begin:g_direct
  assign q=rd[W-1:0];
 end endgenerate
 initial begin
  if(MN<2 || MN>(SMALL?32:128) || W<1 || OUTREG<0 || OUTREG>1 || INREG<0 || INREG>1) $fatal(1,"HNXPAD invalid shape");
 end
endmodule
// Small control alignment uses an addressed flop ring (below2kb), never
// a chain of short direct flop-to-flop paths. Output capture is one edge.
module hnx_pl_pad_ring #(parameter integer W=26, N=3, MUT=0) (
 input wire ck, rst_n,
 input wire [W-1:0] d,
 output reg [W-1:0] q
);
 localparam integer AW=(N<=2)?1:$clog2(N);
 reg [AW-1:0] phase;
 reg [W-1:0] bank[0:N-1];
 wire [AW-1:0] np=(phase==N-1)?0:phase+1'b1;
 always @(posedge ck) begin
  if(!rst_n) phase<=0;
  else begin
   phase<=np;
   bank[phase]<=d;
   q<=bank[(MUT==1)?phase:np];
  end
 end
 initial if(W*N>2048 || N<2) $fatal(1,"HNXRING invalid shape");
endmodule
`default_nettype wire
