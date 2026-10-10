`timescale 1ns/1ps
// Protected full-record replay storage. Real 128x256 1R1W macro ports.
// Request edge0 -> macro read edge1 -> direct capture edge2 -> syndrome edge3
// -> corrected response edge4. Client reserves response space BEFORE request.
// Write accepted edge0 commits edge1; read requests must be >=2 edges later.
// All payload, full sequence, and session identity participate in SECDED.
module ot_hbm_replay_sram #(
 parameter W=551, SW=12, EW=16, DEPTH=512,
 parameter MUT=0,
 // MUXREG=1 (sys-takeover 2026-10-09, opt-in): the bank-select mux of the captured words gets its own register before
 // the SECDED syndrome (collvmpub b2 -> u_dec.s1 path); +1 read edge (response edge5).
 parameter MUXREG=0,
 // NOEPOCH=1 (sys-takeover 2026-10-09, opt-in; review S4/S5): no session/epoch identity and no sequence in the stored
 // record or its checks; SECDED covers the replay payload only.  Go-back-N sequence numbers on the link are unchanged.
 parameter NOEPOCH=0,
 // DECPIPE=1 (sys-takeover 2026-10-10, opt-in): the SECDED decoder's column match gets its own register (DPIPE); +1 read edge.
 parameter DECPIPE=0,
 // ADDRREP=1 (sys-takeover 2026-10-10, opt-in): every macro gets its own write / read enable and address flops
 // (ot_sc_rep_ff, keep_hierarchy): collvmpub_fix5s TT -408 was ONE merged wa register driving the macros of every store
 // across the block (517 ps of wire).  Same edge as wa / wp; values identical.
 parameter ADDRREP=0,
 parameter AW=$clog2(DEPTH), NB=DEPTH/128,
 parameter BW=NB>1?$clog2(NB):1,
 parameter RW=NOEPOCH?W:W+SW+EW, NC=(RW+255)/256, CW=NC*266, NM=(CW+255)/256
)(
 input wire clk,rst_n,
 input wire w_valid,input wire[W-1:0] w_data,
 input wire[SW-1:0] w_seq,input wire[EW-1:0] w_session,
 input wire r_valid,input wire[SW-1:0] r_seq,input wire[EW-1:0] r_session,
 output wire o_valid,output wire[W-1:0] o_data,
 output wire[SW-1:0] o_seq,output wire[EW-1:0] o_session,
 output wire o_ce,o_ue
);
 wire[NC*256-1:0] record_in;
 if(NOEPOCH) begin:g_rec_plain assign record_in={{(NC*256-W){1'b0}},w_data}; end
 else begin:g_rec_full assign record_in={{(NC*256-RW){1'b0}},w_session,w_seq,w_data}; end
 wire[CW-1:0] encoded;
 for(genvar c=0;c<NC;c=c+1) begin:g_enc
  ot_secded_enc #(.K(256),.R(10),.MUT(MUT)) u_enc(.clk(clk),.d(record_in[c*256+:256]),.q(encoded[c*266+:266]));
 end
 reg wp,rp;
 reg[AW-1:0] wa,ra;
 reg[BW-1:0] b1,b2;
 wire[BW-1:0] rb=(NB==1)?0:(ra>>7);
 wire[BW-1:0] wb=(NB==1)?0:(wa>>7);
 wire[NM*256-1:0] macro_d={{(NM*256-CW){1'b0}},encoded};
 reg[NM*256-1:0] captured[0:NB-1];
 for(genvar b=0;b<NB;b=b+1) begin:g_bank
  localparam BANK_INDEX=b;
  wire[NM*256-1:0] raw;
  for(genvar m=0;m<NM;m=m+1) begin:g_macro
   wire m_rce,m_wce;wire[6:0] m_ra,m_wa;
   if(ADDRREP!=0) begin:g_rep
    ot_sc_rep_ff u_rce(.clk(clk),.rst_n(rst_n),.d(r_valid && (NB==1 || r_seq[AW-1:7]==BANK_INDEX)),.q(m_rce));
`ifdef OT_REPLAY_MUT_ADDRREP
    ot_sc_rep_ff u_wce(.clk(clk),.rst_n(rst_n),.d(w_valid && (NB==1 || w_seq[AW-1:7]!=BANK_INDEX)),.q(m_wce));   // mutant: wrong bank
`else
    ot_sc_rep_ff u_wce(.clk(clk),.rst_n(rst_n),.d(w_valid && (NB==1 || w_seq[AW-1:7]==BANK_INDEX)),.q(m_wce));
`endif
    for(genvar k=0;k<7;k=k+1) begin:g_a
     ot_sc_rep_ff u_ra(.clk(clk),.rst_n(rst_n),.d(r_seq[k]),.q(m_ra[k]));
     ot_sc_rep_ff u_wa(.clk(clk),.rst_n(rst_n),.d(w_seq[k]),.q(m_wa[k]));
    end
   end else begin:g_shr
    assign m_rce=rp && rb==BANK_INDEX; assign m_wce=wp && wb==BANK_INDEX; assign m_ra=ra[6:0]; assign m_wa=wa[6:0];
   end
   ot_sram_1r1w_128x256_m1_r2c2 u_mem(
    .clk(clk),.r_ce_in(m_rce),.r_addr_in(m_ra),.rd_out(raw[m*256+:256]),
    .w_ce_in(m_wce),.w_addr_in(m_wa),.wd_in(macro_d[m*256+:256]),
    .w_mask_in({256{1'b1}}),.rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
  end
  always @(posedge clk) captured[b]<=raw;
 end
 reg[3:0] vp;
 reg[SW-1:0] seqp[0:6];reg[EW-1:0] ep[0:6];
 reg[NM*256-1:0] msel;
 always @(posedge clk) msel<=captured[b2];
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin wp<=0;rp<=0;vp<=0; end
  else begin wp<=w_valid;rp<=r_valid;vp<={vp[2:0],r_valid};end
 end
 always @(posedge clk) begin
  wa<=w_seq[AW-1:0];ra<=r_seq[AW-1:0];b1<=rb;b2<=b1;
  seqp[0]<=r_seq;ep[0]<=r_session;
  for(integer t=1;t<7;t=t+1) begin seqp[t]<=seqp[t-1];ep[t]<=ep[t-1];end
 end
 wire[NC*256-1:0] corrected;
 wire[NC-1:0] valid,ce,ue;
 for(genvar c=0;c<NC;c=c+1) begin:g_dec
  ot_secded_dec #(.K(256),.R(10),.DPIPE(DECPIPE)) u_dec(.clk(clk),.rst_n(rst_n),.v(MUXREG?vp[3]:vp[2]),
   .w(MUXREG?msel[c*266+:266]:captured[b2][c*266+:266]),.ov(valid[c]),.d(corrected[c*256+:256]),
   .ce(ce[c]),.ue(ue[c]),.n_ce(),.n_ue());
 end
 wire[SW-1:0] stored_seq=corrected[W+:SW];
 wire[EW-1:0] stored_epoch=corrected[W+SW+:EW];
 assign o_valid=&valid;
 localparam integer SQ=4+(MUXREG!=0)+(DECPIPE!=0);
 wire[SW-1:0] seq_o=seqp[SQ];wire[EW-1:0] ep_o=ep[SQ];
 assign o_ue=o_valid && ((|ue) || (!NOEPOCH && (stored_seq!=seq_o || stored_epoch!=ep_o)));
 assign o_ce=o_valid && |ce;
 assign o_data=o_ue ? {W{1'b0}}:corrected[W-1:0];
 assign o_seq=seq_o;assign o_session=ep_o;
 initial begin
  if(DEPTH<128 || DEPTH%128 || (DEPTH&(DEPTH-1)) || AW>SW) $fatal(1,"invalid SRAM replay depth");
 end
endmodule
