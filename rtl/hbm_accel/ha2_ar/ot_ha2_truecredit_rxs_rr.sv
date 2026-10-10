// redesign-hbm 2026-10-09 (owner: no cycle / area limit): RREG + OREG successor of ot_ha2_truecredit_rxs.sv (same module
// name, parameters and ports; a route / bench uses ONE of the two files).  ha2_rxs_inset12-230045607 TT -173 (reg2reg
// -132.6, output -218 at the sign-off IO reference); the pf line (-448) did not help.  Two structural edits:
//   * RREG: the read request is REGISTERED AT THE MACRO INPUTS (r_ce_q / r_addr_q), like the WREG write side: the fetch
//     decision (wp_q != rp compare, credit, bad) reaches flops only, never the SRAM's r_ce / address pins (macro input
//     setup on a combinational compare-AND was the read-side reg->macro class);
//   * OREG: every output leaves a SECOND register (o2 stage, no logic between the two), so the last flop can sit at the
//     pin while the first stays beside the macro capture (the ~560-bit output wire is a flop-to-flop hop).
// Cost: arrival -> send +2 edges (fetch +1, output +1); the credit round trip grows by 2 edges (CRD covers it);
// ~+1.1k flops.  The WREG overtaking hazard (MUTANT 7) is now impossible by construction (the read lands 1 edge later);
// MUTANT 9 (new) delivers one edge early (skips the RREG valid stage) and must be detected.
// SRAM-queue true-credit receiver (stream safe-hbm, 2026-10-08; REVIEW_20261008 row C4, approved design S-C4).
// Transaction-exact successor of ot_ha2_truecredit_receiver_p #(.CREDIT(1)) for the hardened rx block. The flop queue
// (64 x 560 b = 72.9k flops: tag compare -> push -> 35k-flop write enable, 64:1 x 560 read mux) moves into 1R1W SRAM
// using the closed packet-SRAM ii1rw template (hfd_coll_pkt_fifo_ii1, TT +12.05 / FF +17.31):
//   * pin flops on every input (av_q / tag_q / data_q / cr_q), every output leaves a flop;
//   * WREG: the write enable, address and word are registered at the macro inputs (write lands 2 edges after the
//     arrival flop); a read never overtakes it: the read side sees the write pointer one edge late (wp_q);
//   * the read side is a fixed-latency pipeline that never stalls (a credit is taken at fetch):
//       fetch (r_ce, addr = rp) -> rd_out (macro) -> raw_q (capture flop, no logic before it) -> outputs;
//     the tag check against expect_retire happens on raw_q (one edge after the capture);
//   * credit ready (CREDIT=1 contract of receiver_p): receiver_ready[i] is a credit-return pulse, pin flop, counter.
// Write rule unchanged from receiver_p: a registered arrival is written into slot wp whenever the queue is not full;
// wp advances only on a valid (tag-matching) arrival, so a rejected beat lands in a free slot that is never read.
// Fault: sticky (bad tag at arrival, bad tag at retire, overflow, credit overflow); items fetched after a fault are
// dropped (fail-closed), the faulting item itself is delivered as receiver_p does.
// Cost vs receiver_p CREDIT=1: arrival -> readable +1 edge (WREG), fetch -> send_v/return_v +2 edges (macro + capture);
// the credit round trip grows by 2 edges (CRD must cover it for full rate; CRD is the consumer's buffer depth).
// MUTANT 2 corrupts the returned tag, 4 reads slot rp+1, 5 starts the counter one above CRD (over-issue),
// 7 reads one edge early (wp instead of wp_q: overtakes the WREG write), 8 drops every credit-return pulse (deadlock).
module ot_ha2_truecredit_receiver_s #(
 parameter integer W=544, INJ=2, AW=6, TAGW=16, MUTANT=0,
 parameter integer CREDIT=1, CRD=8
)(input wire clk,rst_n,
 input wire[INJ-1:0] arrival_v,receiver_ready,
 input wire[INJ*W-1:0] arrival_data,
 input wire[INJ*TAGW-1:0] arrival_tag,
 output reg[INJ-1:0] send_v,return_v,
 output reg[INJ*W-1:0] send_data,
 output reg[INJ*TAGW-1:0] return_tag,
 output reg quiet,fault);
 initial if(TAGW<=AW)$fatal(1,"HA2 truecredit tags must exceed slot address width");
 initial if(AW!=6)$fatal(1,"HA2 SRAM receiver: 64-deep queue (ot_sram_1r1w_64x512) only");
 initial if(CREDIT!=1)$fatal(1,"HA2 SRAM receiver: credit ready only (CREDIT=1)");
 initial if(CRD<1)$fatal(1,"HA2 truecredit receiver CRD must be >= 1");
 localparam integer D=1<<AW;
 localparam integer FW=W+TAGW;
 localparam integer NM=(FW+511)/512;
 localparam integer CRW=$clog2(CRD+2)+1;
 localparam integer CR0=CRD+((MUTANT==5)?1:0);
 wire[INJ-1:0] bads,idle;
 for(genvar i=0;i<INJ;i=i+1)begin:g_lane
  reg rst_l;
  always @(posedge clk or negedge rst_n)if(!rst_n)rst_l<=1'b0;else rst_l<=1'b1;
  // pin capture
  reg av_q;
  reg[TAGW-1:0] tag_q;
  reg[W-1:0] data_q;
  always @(posedge clk or negedge rst_n)if(!rst_n)av_q<=1'b0;else av_q<=arrival_v[i];
  always @(posedge clk)begin tag_q<=arrival_tag[i*TAGW+:TAGW];data_q<=arrival_data[i*W+:W];end
  reg[TAGW-1:0] expect_arrival,expect_retire;
  reg bad,ovf;
  reg[AW:0] wp,rp,wp_q;
  wire empty=wp==rp;
  wire full=(wp[AW]!=rp[AW])&&(wp[AW-1:0]==rp[AW-1:0]);
  wire readable=((MUTANT==7)?wp:wp_q)!=rp;
  wire valid_arrival=av_q&&tag_q==expect_arrival&&!bad;
  // credit counter (registered cr_ok, as receiver_p CREDIT=1)
  reg cr_q,cr_ok,home_r,cr_ovf;
  reg[CRW-1:0] cred;
  wire fetch=readable&&cr_ok&&!bad;
  wire cr_in=(MUTANT==8)?1'b0:cr_q;
  wire[CRW-1:0] cred_n=cred+CRW'(cr_in)-CRW'(fetch);
  always @(posedge clk or negedge rst_l)
   if(!rst_l)begin cr_q<=1'b0;cred<=CRW'(CR0);cr_ok<=1'b1;home_r<=1'b1;cr_ovf<=1'b0;end
   else begin
    cr_q<=receiver_ready[i];cred<=cred_n;cr_ok<=cred_n!=0;home_r<=cred_n==CRW'(CR0);
    if(cr_in&&!fetch&&cred==CRW'(CR0))cr_ovf<=1'b1;
   end
  wire cr_home=home_r&&!cr_q;
  // WREG write side: slot wp, registered at the macro inputs
  reg w_ce_q;reg[AW-1:0] w_addr_q;reg[NM*512-1:0] wd_q;
  always @(posedge clk or negedge rst_l)if(!rst_l)w_ce_q<=1'b0;else w_ce_q<=av_q&&!full;
  always @(posedge clk)begin
   w_addr_q<=wp[AW-1:0];wd_q<={{(NM*512-FW){1'b0}},tag_q,data_q};
  end
  // storage: NM x 64x512 1R1W macros
  wire[AW-1:0] r_addr=(MUTANT==4)?(rp[AW-1:0]+1'b1):rp[AW-1:0];
  reg r_ce_q;reg[AW-1:0] r_addr_q;                          // RREG: read request registered at the macro inputs
  always @(posedge clk or negedge rst_l)if(!rst_l)r_ce_q<=1'b0;else r_ce_q<=fetch;
  always @(posedge clk)r_addr_q<=r_addr;
  wire[NM*512-1:0] ram_q;
  for(genvar m=0;m<NM;m=m+1)begin:g_ram
   ot_sram_1r1w_64x512_m1_r2c2 storage(.clk(clk),.r_ce_in(r_ce_q),.r_addr_in(r_addr_q),.rd_out(ram_q[m*512+:512]),
    .w_ce_in(w_ce_q),.w_addr_in(w_addr_q),.wd_in(wd_q[m*512+:512]),.w_mask_in({512{1'b1}}),
    .rr_en(2'b0),.rr_addr(12'b0),.cr_en(2'b0),.cr_sel(18'b0));
  end
  // read pipeline: v0 = request at the macro inputs, v1 = macro output valid this edge, v2 = raw_q holds the item
  reg v0,v1,v2;reg[FW-1:0] raw_q;
  always @(posedge clk)raw_q<=ram_q[FW-1:0];
  wire[TAGW-1:0] raw_tag=raw_q[W+:TAGW];
  wire deliver=v2&&!bad;
  reg s1_v,r1_v;reg[TAGW-1:0] r1_tag;reg[W-1:0] s1_d;   // OREG first output stage
  assign bads[i]=bad||ovf||cr_ovf;
  assign idle[i]=empty&&!av_q&&!w_ce_q&&!v0&&!v1&&!v2&&!s1_v&&!r1_v&&!send_v[i]&&!return_v[i]&&cr_home;
  always @(posedge clk or negedge rst_l)
   if(!rst_l)begin
    expect_arrival<=0;expect_retire<=0;bad<=0;ovf<=0;wp<=0;rp<=0;wp_q<=0;v0<=0;v1<=0;v2<=0;
    s1_v<=0;r1_v<=0;send_v[i]<=0;return_v[i]<=0;r1_tag<=0;return_tag[i*TAGW+:TAGW]<=0;
   end else begin
    wp_q<=wp;v0<=fetch;v1<=v0;v2<=(MUTANT==9)?v0:v1;
    s1_v<=deliver;r1_v<=deliver;send_v[i]<=s1_v;return_v[i]<=r1_v;return_tag[i*TAGW+:TAGW]<=r1_tag;
    if(av_q&&!valid_arrival)bad<=1;
    if(valid_arrival)begin
     expect_arrival<=expect_arrival+1'b1;
     if(full)ovf<=1'b1;else wp<=wp+1'b1;
    end
    if(fetch)rp<=rp+1'b1;
    if(deliver)begin
     if(raw_tag!=expect_retire)bad<=1;
     r1_tag<=raw_tag ^ ((MUTANT==2)?TAGW'(1):TAGW'(0));
     expect_retire<=expect_retire+1'b1;
    end
   end
  always @(posedge clk)begin s1_d<=raw_q[W-1:0];send_data[i*W+:W]<=s1_d;end   // OREG: two flops, no logic between
 end
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin quiet<=1'b1;fault<=1'b0;end
  else begin quiet<=&idle;fault<=|bads;end
endmodule
