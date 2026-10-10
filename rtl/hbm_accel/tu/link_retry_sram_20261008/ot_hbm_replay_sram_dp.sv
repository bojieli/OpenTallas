`timescale 1ns/1ps
// redesign-hbm 2026-10-09 (owner: no cycle / area limit; structural alternatives): DEEP-PIPELINED DECODE successor of
// ot_hbm_replay_sram.sv (same module name, parameters and ports; a route / bench uses ONE of the two files).
// hbm_retry545_cl5-51ac71c99 TT -87.4 / SS -488 (22 levels): seqp[*] (== b2, merged by opt) -> u_dec.s1: the bank select
// b2 fans out to the 1,024-bit 4:1 bank mux, then one 256-input XOR tree per syndrome bit, all in one edge.
// Borrowed ideas: replicated control trees (one registered bank-select copy per 64 captured bits, fanout <= 64) and
// generous pipelining at every hop (partial syndromes per 64-bit chunk, registered, then the 4-way combine).
//   request edge0 -> macro read edge1 -> capture edge2 -> BANK-SELECTED word edge3 -> 4 partial syndromes edge4
//   -> syndrome (4-way XOR, registered with 4 replicas) edge5 -> located-data edge6 -> flags edge7 -> registered response edge8 (was edge4: +4 edges)
// The +4 edges are on the REPLAY read only (a link-error path; the pipeline waits on rd_v / read_pending, no fixed
// latency is assumed); the forward token path is unchanged (0 cycles).  Same Hsiao code (ot_secded_cols.svh), same
// correction / poison rules, same transaction tags: exact.
module ot_hbm_replay_sram #(
 parameter W=551, SW=12, EW=16, DEPTH=512,
 parameter MUT=0,
 parameter AW=$clog2(DEPTH), NB=DEPTH/128,
 parameter BW=NB>1?$clog2(NB):1,
 parameter RW=W+SW+EW, NC=(RW+255)/256, CW=NC*266, NM=(CW+255)/256
)(
 input wire clk,rst_n,
 input wire w_valid,input wire[W-1:0] w_data,
 input wire[SW-1:0] w_seq,input wire[EW-1:0] w_session,
 input wire r_valid,input wire[SW-1:0] r_seq,input wire[EW-1:0] r_session,
 output wire o_valid,output wire[W-1:0] o_data,
 output wire[SW-1:0] o_seq,output wire[EW-1:0] o_session,
 output wire o_ce,o_ue
);
 localparam LAT=8, NS=(NM*256+63)/64;           // NS bank-select replicas (one per 64 captured bits)
 wire[NC*256-1:0] record_in={{(NC*256-RW){1'b0}},w_session,w_seq,w_data};
 wire[CW-1:0] encoded;
 for(genvar c=0;c<NC;c=c+1) begin:g_enc
  ot_secded_enc #(.K(256),.R(10),.MUT(MUT)) u_enc(.clk(clk),.d(record_in[c*256+:256]),.q(encoded[c*266+:266]));
 end
 reg wp,rp;
 reg[AW-1:0] wa,ra;
 reg[BW-1:0] b1;
 (* keep *) reg[BW-1:0] b2r[0:NS-1];             // replicated bank select (registered, fanout <= 64 each)
 wire[BW-1:0] rb=(NB==1)?0:(ra>>7);
 wire[BW-1:0] wb=(NB==1)?0:(wa>>7);
 wire[NM*256-1:0] macro_d={{(NM*256-CW){1'b0}},encoded};
 reg[NM*256-1:0] captured[0:NB-1];
 for(genvar b=0;b<NB;b=b+1) begin:g_bank
  localparam BANK_INDEX=b;
  wire[NM*256-1:0] raw;
  for(genvar m=0;m<NM;m=m+1) begin:g_macro
   ot_sram_1r1w_128x256_m1_r2c2 u_mem(
    .clk(clk),.r_ce_in(rp && rb==BANK_INDEX),.r_addr_in(ra[6:0]),.rd_out(raw[m*256+:256]),
    .w_ce_in(wp && wb==BANK_INDEX),.w_addr_in(wa[6:0]),.wd_in(macro_d[m*256+:256]),
    .w_mask_in({256{1'b1}}),.rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
  end
  always @(posedge clk) captured[b]<=raw;
 end
 // edge3: the bank-selected word, each 64-bit slice selected by its own select replica
 reg[NM*256-1:0] wsel;
 for(genvar s=0;s<NS;s=s+1) begin:g_sel
`ifndef OT_REPLAY_DP_MUT_SEL
  always @(posedge clk) wsel[s*64+:64]<=captured[b2r[s]][s*64+:64];
`else
  always @(posedge clk) wsel[s*64+:64]<=captured[b1][s*64+:64];     // MUTANT: select one edge early (wrong bank on a crossing)
`endif
 end
 reg[LAT-1:0] vp;
 reg[SW-1:0] seqp[0:LAT];reg[EW-1:0] ep[0:LAT];
 integer t;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin wp<=0;rp<=0;vp<=0; end
  else begin wp<=w_valid;rp<=r_valid;vp<={vp[LAT-2:0],r_valid};end
 end
 always @(posedge clk) begin
  wa<=w_seq[AW-1:0];ra<=r_seq[AW-1:0];b1<=rb;
  for(t=0;t<NS;t=t+1) b2r[t]<=b1;
  seqp[0]<=r_seq;ep[0]<=r_session;
  for(t=1;t<=LAT;t=t+1) begin seqp[t]<=seqp[t-1];ep[t]<=ep[t-1];end
 end
 wire[NC*256-1:0] corrected;
 wire[NC-1:0] valid,ce,ue;
 for(genvar c=0;c<NC;c=c+1) begin:g_dec
  ot_secded_dec_dp #(.K(256),.R(10)) u_dec(.clk(clk),.rst_n(rst_n),.v(vp[3]),
   .w(wsel[c*266+:266]),.ov(valid[c]),.d(corrected[c*256+:256]),.ce(ce[c]),.ue(ue[c]));
 end
 wire[SW-1:0] stored_seq=corrected[W+:SW];
 wire[EW-1:0] stored_epoch=corrected[W+SW+:EW];
 // Decoder response edge7 -> registered response edge8. Tags remain aligned
 // with their request even if the retry cursor/session moves while in flight.
 reg response_v, response_ce, response_ue;
 reg [W-1:0] response_data;
 reg [SW-1:0] response_seq;
 reg [EW-1:0] response_epoch;
 wire bad_response = (|ue) || stored_seq!=seqp[LAT-1] || stored_epoch!=ep[LAT-1];
 always @(posedge clk or negedge rst_n)
   if(!rst_n) begin response_v<=0; response_ce<=0; response_ue<=0; end
   else begin response_v<=&valid; response_ce<=(&valid) && |ce;
     response_ue<=(&valid) && bad_response; end
 always @(posedge clk) begin
   response_data<=corrected[W-1:0];
   response_seq<=seqp[LAT-1]; response_epoch<=ep[LAT-1];
 end
 assign o_valid=response_v; assign o_ue=response_ue; assign o_ce=response_ce;
 assign o_data=response_ue ? {W{1'b0}}:response_data;
 assign o_seq=response_seq; assign o_session=response_epoch;
 initial begin
  if(DEPTH<128 || DEPTH%128 || (DEPTH&(DEPTH-1)) || AW>SW) $fatal(1,"invalid SRAM replay depth");
 end
endmodule

// the 4-edge decoder ot_secded_dec_dp lives in rtl/common/ot_secded_dec_dp.sv (beside ot_secded_cols.svh)
