`default_nettype none
// HBM-SVGREL8 2026-10-20: HARDENED ot_hbm_svc_sm8_landing_bank (LBANKS 4: one 256x256 SRAM = four 64-row landing
// blocks; that module stays byte-identical).  Same identity checks (epoch, ordinal%8 bank, row < count, duplicate),
// same faults.  Changes:
//   * response FIFO = the reviewed, fingerprinted ot_hbm_svc_async_fifo, unchanged (the only primitive the HBM CDC
//     admission accepts for a crossing); rel8e: 57 bit-sliced 5-bit instances in lockstep (see below);
//   * SRAM write port from STREAM flops (as the fg2 WREG=1 master): the accepted word lands one stream edge later and
//     complete_v is registered with it (landing -> resident +1 stream edge, before the elastic block_ready); a macro pin
//     then reads only stream-family flops.  The capture registers load while the FIFO head is valid (storage read only
//     under rd_valid, as reviewed_gray_fifos proves), through per-slice AND gates with KEPT qualifier flops (each AND
//     drives <= 32 capture enables; packet_v itself drives only the ANDs);
//   * the reserve arrives REGISTERED (the producer's per-bank copy) and is registered once more here into KEPT per-slot
//     enable copies (each <= 32 flops): a block's bank state is set 2 stream edges after its reserve (the first response
//     of a block needs the descriptor crossing + DRAM, >> 2 edges; a bank is only re-reserved after its drain);
//   * reset only on control (valid, sticky, write strobe, completion, reserve enables) from ot_rst_fanout leaves.
module ot_hbm_svc_sm8_landing_bank_h #(
 parameter [2:0] BANK=0,parameter integer RESPONSE_DEPTH=8,parameter integer LBANKS=4,
 parameter integer LB=(LBANKS>2)?2:1,parameter integer IW=283+LB
)(
 input wire hbm_clk,hbm_rst_n,stream_clk,stream_rst_n,
 input wire in_v,output wire in_ready,input wire [IW-1:0] in_data,
 output wire overflow,
 input wire reserve_v,input wire [LB-1:0] reserve_bank,input wire [15:0] reserve_epoch,
 input wire [11:0] reserve_total,input wire stop,
 output wire complete_v,output wire [LB-1:0] complete_bank,output wire fault,
 input wire read_v,input wire [LB-1:0] read_bank,input wire [5:0] read_row,
 output wire [255:0] read_data
);
 initial if(LBANKS!=4)$fatal(1,"landing_bank_h: LBANKS 4 (one 256x256 macro)");
 wire[1:0]sr;
 ot_rst_fanout #(.N(2)) u_sr(.clk(stream_clk),.rst_n_in(stream_rst_n),.rst_n(sr));
 // HBM-COLLECT11 2026-10-21 (rel8e, COORDINATOR DECISION 2: no census waiver for the FIFO's 571-load read/write
 // select decode): the response FIFO is RSN BIT-SLICED instances of the reviewed ot_hbm_svc_async_fifo, byte-identical
 // module (hash pin intact), only WIDTH differs (RSW = 5 bits: mapped DEPTH16 census max 32 loads;
 // 285 = 57 x 5).  Every instance has its own Gray pointers, synchronisers and reset syncs (the reviewed CDC proof holds
 // per instance).  LOCKSTEP: an instance's pointer resolution can lag another's by one edge (independent synchronisers),
 // so ready/valid are AND-REDUCED, never taken from instance 0: a push is offered to every instance only when ALL are
 // ready (in_ready = &wr_ready), a pop only when ALL are valid (packet_v = &rd_valid).  Each instance therefore fires
 // on exactly the same edges, its binary pointers stay equal to every other's, and the heads of all instances are the
 // same entry whenever packet_v.  wr_overflow / rd_underflow (OR-reduced) stay 0 by construction.  Per-instance push /
 // pop enables carry their own KEPT qualifier flop (wq_k / cq_k), so no shared fire node fans out to 57 pointer sets.
 localparam integer RSW=5,RSN=(IW+RSW-1)/RSW;
 initial if(RSN*RSW!=IW)$fatal(1,"landing_bank_h: IW must be RSN x RSW");
 wire packet_v,packet_take,underflow;wire [IW-1:0] packet;
 wire [RSN-1:0] rs_wr_ready,rs_rd_valid,rs_ov,rs_un;
 localparam integer FG=(RSN+15)/16;
 wire [FG-1:0] write_group,pop_group;
 // HBMc/TILES 10-22 (native census: a constant-input AND is transparent, so and2(packet_take,1) left packet_take with 58
 // loads): each pop group is a real 2-input AND of packet_v and take_ok (= packet_take, same edge, same function).
 wire take_ok;
 for(genvar fg=0;fg<FG;fg=fg+1)begin:g_handshake_tree
  ot_hbm_svc_local_and2 u_wr(.a(in_v),.b(in_ready),.y(write_group[fg]));
  ot_hbm_svc_local_and2 u_rd(.a(packet_v),.b(take_ok),.y(pop_group[fg]));
 end
 // Eight slices per reset leaf: one FIFO reset comb pin and one qualifier reset
 // per slice. Both-side reset still asserts asynchronously through every leaf.
 localparam integer RRG=(RSN+7)/8;
 wire [RRG-1:0] wr_leaf,rd_leaf;
 ot_rst_fanout #(.N(RRG)) u_wr_leaf(.clk(hbm_clk),.rst_n_in(hbm_rst_n),.rst_n(wr_leaf));
 ot_rst_fanout #(.N(RRG)) u_rd_leaf(.clk(stream_clk),.rst_n_in(sr[1]),.rst_n(rd_leaf));
 (* keep="true",dont_touch="true" *) reg [RSN-1:0] wq_k;   // hbm-side per-slice push qualifiers (1 after reset)

 assign in_ready=&rs_wr_ready;assign packet_v=&rs_rd_valid;
 assign overflow=|rs_ov;assign underflow=|rs_un;
 // stream-side per-slice qualifiers: cq_k[i] gates slice i's head capture (with ITS OWN rd_valid, so each h bit reads
 // only its own instance's storage under that instance's rd_valid) and slice i's pop (with the AND-reduced packet_take)
 (* keep="true",dont_touch="true" *) reg[RSN-1:0]cq_k;

 wire[RSN-1:0]cap_en=cq_k&rs_rd_valid;
 genvar rs;
 generate for(rs=0;rs<RSN;rs=rs+1)begin:rsl
  always @(posedge hbm_clk or negedge wr_leaf[rs/8])
   if(!wr_leaf[rs/8])wq_k[rs]<=0;else wq_k[rs]<=1'b1;
  always @(posedge stream_clk or negedge rd_leaf[rs/8])
   if(!rd_leaf[rs/8])cq_k[rs]<=0;else cq_k[rs]<=1'b1;
  wire write_slice,pop_slice;
  ot_hbm_svc_local_and2 u_wr_slice(.a(write_group[rs/16]),.b(wq_k[rs]),.y(write_slice));
  ot_hbm_svc_local_and2 u_rd_slice(.a(pop_group[rs/16]),.b(cq_k[rs]),.y(pop_slice));
  ot_hbm_svc_async_fifo #(.WIDTH(RSW),.DEPTH(RESPONSE_DEPTH)) u_response(
   .wr_clk(hbm_clk),.wr_rst_n(wr_leaf[rs/8]),.wr_valid(write_slice),.wr_ready(rs_wr_ready[rs]),
   .wr_data(in_data[rs*RSW+:RSW]),.wr_overflow(rs_ov[rs]),
   .rd_clk(stream_clk),.rd_rst_n(rd_leaf[rs/8]),.rd_valid(rs_rd_valid[rs]),.rd_ready(pop_slice),
   .rd_data(packet[rs*RSW+:RSW]),.rd_underflow(rs_un[rs]));
 end endgenerate
 // HBM-COLLECT10 2026-10-21 (rel8c): REGISTERED FIFO HEAD.  r2 decoded the identity check / seen / received / sticky
 // updates straight from the FIFO head (8-slot storage mux -> epoch/row/bank compare -> 256 seen bits): every such
 // register was a cross-family storage consumer, 492,643 bounded storage->consumer pairs in the gate's OT_GF census
 // (61.8k per landing bank) whose per-pair finite-path proof stalled synth_odb > 8 h (rel8a/b).  Now stage A (pop edge,
 // packet_take = packet_v && !stop && !sticky as before) copies the RAW head word into reader-family registers h_*
 // (loaded while rd_valid, through per-slice ANDs with KEPT qualifier flops; each h bit reads only its 8 storage bits);
 // stage B (next edge) runs the identity check / seen / received / sticky / completion on h_* (no storage in its cone)
 // and registers the SRAM write (w_*) as before.  +1 stream edge landing -> resident and +1 edge to a fault on a bad
 // identity (elastic HBM side, before block_ready; go slots unchanged).  A packet popped in the edge a bad one is being
 // checked is dropped (sticky blocks stage B): the bank is in fault either way.
 // reserve stage 2: KEPT per-slot enables [slot*4+c] (c0: valid/epoch/count 24, c1/c2: seen halves 32, c3: received 7)
 // HBMc/TILES 10-22: 8 KEPT copies per slot (k: 0 epoch[7:0], 1 epoch[15:8], 2 count + valid, 3..6 seen quarter k-3,
 // 7 received); rel8e had 4 (c0 24 b, c1/c2 32 b: 47 mapped load pins with the hold muxes).
 (* keep="true",dont_touch="true" *) reg[LBANKS*8-1:0]ren_k;
 reg[15:0]r_epoch;reg[6:0]r_count;
 // bank state as FLAT vectors (rel8c): reg arrays indexed by the registered h_bank were inferred as yosys $mem and
 // MEMORY_DFF cloned h_bank into an anonymous read-address flop (gate r1 OT_GF unapproved crossing mem -> _318839_)
 reg [LBANKS-1:0] valid_q;reg [LBANKS*16-1:0] epoch_q;reg [LBANKS*7-1:0] count_q,received_q;
 reg [LBANKS*64-1:0] seen_q;reg sticky;
 // stage A: raw head registers (h_v = popped this edge)
 // (rel8e) one IW-bit head register hq, loaded per RSW-bit slice; fields are its bit ranges as in the packet
 reg h_v;reg [IW-1:0] hq;
 wire [255:0] h_data=hq[255:0];wire [10:0] h_ordinal=hq[IW-1:IW-11];wire [LB-1:0] h_bank=hq[271+LB:272];
 wire [15:0] h_epoch=hq[271:256];
 // stage B on registers only
 wire [5:0] row=h_ordinal[8:3];
 // Static one-hot bank/row reads keep binary packet identity out of wide
 // 256-way read/write mux selects. Real local gates serve <=16 data bits.
 wire [LBANKS-1:0] ep_sel,ctl_sel;
 wire [LBANKS*4-1:0] seen_sel,seen_clear,seen_write;
 wire [63:0]row_sel;
 wire [LBANKS*64-1:0]seen_set;
 wire[LBANKS-1:0] rcv_sel;
 for(genvar bs=0;bs<LBANKS;bs=bs+1)begin:g_bank_select
  // hit = (h_bank == bs) as real 2-input ANDs of this slot's kept bank copy bits (LB 2)
  localparam [1:0] BS=bs;
  wire hb1=BS[1]?hbank_k[bs][1]:!hbank_k[bs][1];
  wire hb0=BS[0]?hbank_k[bs][0]:!hbank_k[bs][0];
  ot_hbm_svc_local_and2 u_e(.a(hb1),.b(hb0),.y(ep_sel[bs]));
  ot_hbm_svc_local_and2 u_c(.a(hb1),.b(hb0),.y(ctl_sel[bs]));
  ot_hbm_svc_local_and2 u_r(.a(hb1),.b(hb0),.y(rcv_sel[bs]));
  for(genvar sg=0;sg<4;sg=sg+1)begin:g_seen_group
   ot_hbm_svc_local_and2 u_s(.a(hb1),.b(hb0),.y(seen_sel[bs*4+sg]));
   assign seen_clear[bs*4+sg]=ren_k[bs*8+3+sg];
  end
 end
 // HBMc/TILES 10-22: row / bank decodes read KEPT same-edge copies of the head bits (loaded with the head slice that
 // holds them), not constant-input AND "buffers" (transparent to the native census: hq row bits had 100 loads).
 (* keep="true",dont_touch="true" *) reg[5:0] row_k[0:7];
 (* keep="true",dont_touch="true" *) reg[LB-1:0] hbank_k[0:LBANKS-1];
 integer rk,rkb;
 always @(posedge stream_clk)begin
  for(rk=0;rk<8;rk=rk+1)for(rkb=0;rkb<6;rkb=rkb+1)if(cap_en[(IW-11+3+rkb)/RSW])row_k[rk][rkb]<=packet[IW-11+3+rkb];
  for(rk=0;rk<LBANKS;rk=rk+1)for(rkb=0;rkb<LB;rkb=rkb+1)if(cap_en[(272+rkb)/RSW])hbank_k[rk][rkb]<=packet[272+rkb];
 end
 for(genvar rr=0;rr<64;rr=rr+1)begin:g_row_select
  assign row_sel[rr]=(row_k[rr/8]==rr);
 end
 reg [15:0]b_epoch;reg [6:0]b_count,b_rcv;reg b_valid,b_seen;
 integer br,cr;
 always @*begin
  b_epoch=0;b_count=0;b_rcv=0;b_valid=0;b_seen=0;
  for(br=0;br<LBANKS;br=br+1)begin
   b_epoch=b_epoch|(epoch_q[br*16+:16]&{16{ep_sel[br]}});
   b_count=b_count|(count_q[br*7+:7]&{7{ctl_sel[br]}});
   b_rcv=b_rcv|(received_q[br*7+:7]&{7{ctl_sel[br]}});
   b_valid=b_valid|(valid_q[br]&ctl_sel[br]);
   for(cr=0;cr<64;cr=cr+1)
    b_seen=b_seen|(seen_q[br*64+cr]&seen_sel[br*4+cr/16]&row_sel[cr]);
  end
 end
 wire identity_ok=b_valid&&b_epoch==h_epoch&&h_ordinal[2:0]==BANK&&
                 {1'b0,row}<b_count&&!b_seen;
 wire take_b=h_v&&!sticky;
 wire landing_write=take_b&&identity_ok;
 wire[LBANKS-1:0] received_capture;
 for(genvar rcv=0;rcv<LBANKS;rcv=rcv+1)begin:g_received_capture
  ot_hbm_svc_local_and2 u_capture(.a(landing_write),.b(rcv_sel[rcv]),.y(received_capture[rcv]));
 end
 for(genvar wb=0;wb<LBANKS;wb=wb+1)begin:g_seen_write
  for(genvar wg=0;wg<4;wg=wg+1)begin:g_group
   ot_hbm_svc_local_and2 u_w(.a(landing_write),.b(seen_sel[wb*4+wg]),.y(seen_write[wb*4+wg]));
   for(genvar wr=0;wr<16;wr=wr+1)begin:g_bit
    ot_hbm_svc_local_and2 u_s(.a(seen_write[wb*4+wg]),.b(row_sel[wg*16+wr]),.y(seen_set[wb*64+wg*16+wr]));
   end
  end
 end
 assign take_ok=!stop&&!sticky;
 assign packet_take=packet_v&&take_ok;
 wire complete_now=landing_write&&b_rcv+1'b1==b_count;
 wire[LBANKS*2-1:0] epoch_capture;
 wire[LBANKS-1:0] count_capture;
 genvar ec;
 generate for(ec=0;ec<LBANKS;ec=ec+1)begin:reserve_capture_local
  assign epoch_capture[ec*2]=ren_k[ec*8];
  assign epoch_capture[ec*2+1]=ren_k[ec*8+1];
  assign count_capture[ec]=ren_k[ec*8+2];
 end endgenerate
 reg w_ce_q,cmp_q;reg [LB-1:0] w_bank_q;reg [5:0] w_row_q;reg [255:0] w_data_q;
 assign complete_v=cmp_q;assign complete_bank=w_bank_q;assign fault=sticky||underflow;
`ifdef SVGH_MUT
 localparam integer HM=`SVGH_MUT;     // bench negative control 6 (HBM-COLLECT10): landing row bit 0 flipped
`else
 localparam integer HM=0;
`endif
 integer b,c;
 always @(posedge stream_clk or negedge sr[0])begin
  if(!sr[0])begin valid_q<=0;sticky<=0;w_ce_q<=0;cmp_q<=0;ren_k<=0;h_v<=0;end
  else begin
   h_v<=packet_take;w_ce_q<=landing_write;cmp_q<=complete_now;
   for(b=0;b<LBANKS;b=b+1)for(c=0;c<8;c=c+1)ren_k[b*8+c]<=reserve_v&&reserve_bank==b;
   for(b=0;b<LBANKS;b=b+1)if(ren_k[b*8+2])valid_q[b]<=1;
   if(take_b&&!identity_ok)sticky<=1;
  end
 end
 always @(posedge stream_clk)begin
  r_epoch<=reserve_epoch;r_count<=reserve_total>BANK?7'((reserve_total+7-BANK)/8):7'd0;
  for(c=0;c<RSN;c=c+1)if(cap_en[c])hq[c*RSW+:RSW]<=packet[c*RSW+:RSW];
  // Datapath is sampled every edge; w_ce_q is the sole SRAM transaction qualifier.
  // A hold mux on 256 payload bits made one take_b driver feed >500 mapped pins.
  // Metadata stays qualified, so valid writes and completion identity are unchanged.
  w_data_q<=h_data;
  if(take_b)begin w_bank_q<=h_bank;w_row_q<=(HM==6)?(row^6'd1):row;end
  for(b=0;b<LBANKS;b=b+1)begin
   if(epoch_capture[b*2])epoch_q[b*16+:8]<=r_epoch[7:0];
   if(epoch_capture[b*2+1])epoch_q[b*16+8+:8]<=r_epoch[15:8];
   if(count_capture[b])count_q[b*7+:7]<=r_count;
   for(c=0;c<64;c=c+1)begin
    if(seen_clear[b*4+c/16])seen_q[b*64+c]<=0;
    else if(seen_set[b*64+c])seen_q[b*64+c]<=1'b1;
   end
   if(ren_k[b*8+7])received_q[b*7+:7]<=0;
   else if(received_capture[b])received_q[b*7+:7]<=b_rcv+1'b1;
  end
 end
 ot_sram_1r1w_256x256_m2_r2c2 u_payload(
  .clk(stream_clk),.r_ce_in(read_v&&!stop&&!sticky),.r_addr_in({read_bank,read_row}),.rd_out(read_data),
  .w_ce_in(w_ce_q),.w_addr_in({w_bank_q,w_row_q}),.wd_in(w_data_q),.w_mask_in({256{1'b1}}),
  .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
endmodule
`default_nettype wire
