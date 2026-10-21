`default_nettype none
// HBM-SVGREL8 2026-10-20: HARDENED ot_hbm_svc_sm8_landing_bank (LBANKS 4: one 256x256 SRAM = four 64-row landing
// blocks; that module stays byte-identical).  Same identity checks (epoch, ordinal%8 bank, row < count, duplicate),
// same faults.  Changes:
//   * response FIFO = the reviewed, fingerprinted ot_hbm_svc_async_fifo, unchanged (the only primitive the HBM CDC
//     admission accepts for a crossing; its internal 8-slot decode / read mux is the reviewed primitive's);
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
 wire packet_v,packet_take,underflow;wire [IW-1:0] packet;
 ot_hbm_svc_async_fifo #(.WIDTH(IW),.DEPTH(RESPONSE_DEPTH)) u_response(
  .wr_clk(hbm_clk),.wr_rst_n(hbm_rst_n),.wr_valid(in_v),.wr_ready(in_ready),.wr_data(in_data),.wr_overflow(overflow),
  .rd_clk(stream_clk),.rd_rst_n(stream_rst_n),.rd_valid(packet_v),.rd_ready(packet_take),.rd_data(packet),.rd_underflow(underflow));
 // ROUND 3 (census: the 256-way seen / 4-way bank lookups decoded straight from the FIFO head had 72-97-load nets):
 // stage A (pop edge, data-independent: packet_take = packet_v && !stop && !sticky as before) captures the head word
 // into reader-family registers -- gated by the FIFO's rd_valid through per-slice ANDs with KEPT qualifier flops -- and
 // its {bank,row} as a REGISTERED ONE-HOT (256) plus a one-hot bank; stage B (next edge) checks the identity on the
 // registers, writes the SRAM (same edge as the WREG master's registered write) and reports completion (same edge as
 // its registered complete_v).  Faults are detected one edge later.
 (* keep="true",dont_touch="true" *) reg[17:0]cq_k;   // [7:0] data slices, [8] fields, [16:9] one-hot slices, [17] bank one-hot
 always @(posedge stream_clk or negedge sr[1])if(!sr[1])cq_k<=0;else cq_k<={18{1'b1}};
 wire[17:0]cap_en=cq_k&{18{packet_v}};
 wire [10:0] ordinal=packet[IW-1:IW-11];wire [LB-1:0] bank=packet[271+LB:272];wire [15:0] epoch=packet[271:256];
 wire [5:0] row=ordinal[8:3];
 wire [255:0] sel_d=256'd1<<{bank,row};
 reg [255:0] w_data_q,sel_q;reg [LB-1:0] p_bank;reg [5:0] p_row;reg [2:0] p_lo;reg [15:0] p_epoch;reg [LBANKS-1:0] bsel_q;
 reg take_q;
 (* keep="true",dont_touch="true" *) reg[8:0]tk_k;     // = take_q: seen-update slices (8) + per-bank counters (1)
 (* keep="true",dont_touch="true" *) reg[LBANKS*4-1:0]ren_k;
 reg[15:0]r_epoch;reg[6:0]r_count;
 reg [LBANKS-1:0] valid_q;reg [15:0] epoch_q[0:LBANKS-1];reg [6:0] count_q[0:LBANKS-1],received_q[0:LBANKS-1];
 reg [255:0] seen_q;reg sticky;
 reg b_valid,b_epoch,b_count;reg [6:0] b_cnt,b_rcv;integer b,c;
 always @*begin
  b_valid=0;b_epoch=0;b_cnt=0;b_rcv=0;
  for(b=0;b<LBANKS;b=b+1)if(bsel_q[b])begin
   b_valid=b_valid|valid_q[b];b_epoch=b_epoch|(epoch_q[b]==p_epoch);b_cnt=b_cnt|count_q[b];b_rcv=b_rcv|received_q[b];
  end
 end
 wire seen_hit=|(sel_q&seen_q);
 (* keep="true" *) wire identity_ok=b_valid&&b_epoch&&p_lo==BANK&&{1'b0,p_row}<b_cnt&&!seen_hit;
 wire landing_write=take_q&&identity_ok;   // take_q carries the pop-edge !stop && !sticky (as packet_take)
 assign packet_take=packet_v&&!stop&&!sticky;
 wire complete_now=landing_write&&b_rcv+1'b1==b_cnt;
 assign complete_v=complete_now;assign complete_bank=p_bank;assign fault=sticky||underflow;
 wire [8:0] upd;
 for(genvar u=0;u<9;u=u+1)begin:g_upd
  (* keep="true" *) wire w=tk_k[u]&&identity_ok;
  assign upd[u]=w;
 end
 always @(posedge stream_clk or negedge sr[0])begin
  if(!sr[0])begin valid_q<=0;sticky<=0;take_q<=0;tk_k<=0;ren_k<=0;end
  else begin
   take_q<=packet_take;tk_k<={9{packet_take}};
   for(b=0;b<LBANKS;b=b+1)for(c=0;c<4;c=c+1)ren_k[b*4+c]<=reserve_v&&reserve_bank==b;
   for(b=0;b<LBANKS;b=b+1)if(ren_k[b*4])valid_q[b]<=1;
   if(take_q&&!identity_ok)sticky<=1;
  end
 end
 always @(posedge stream_clk)begin
  r_epoch<=reserve_epoch;r_count<=reserve_total>BANK?7'((reserve_total+7-BANK)/8):7'd0;
  for(c=0;c<8;c=c+1)begin
   if(cap_en[c])w_data_q[c*32+:32]<=packet[c*32+:32];
   if(cap_en[9+c])sel_q[c*32+:32]<=sel_d[c*32+:32];
  end
  if(cap_en[8])begin p_bank<=bank;p_row<=row;p_lo<=ordinal[2:0];p_epoch<=epoch;end
  if(cap_en[17])for(b=0;b<LBANKS;b=b+1)bsel_q[b]<=bank==b;
  for(b=0;b<LBANKS;b=b+1)begin
   if(ren_k[b*4])begin epoch_q[b]<=r_epoch;count_q[b]<=r_count;end
   if(ren_k[b*4+1])seen_q[b*64+:32]<=0;
   if(ren_k[b*4+2])seen_q[b*64+32+:32]<=0;
   if(ren_k[b*4+3])received_q[b]<=0;
   else if(upd[8]&&bsel_q[b])received_q[b]<=received_q[b]+1'b1;
  end
  for(c=0;c<8;c=c+1)if(upd[c])seen_q[c*32+:32]<=seen_q[c*32+:32]|sel_q[c*32+:32];
 end
 ot_sram_1r1w_256x256_m2_r2c2 u_payload(
  .clk(stream_clk),.r_ce_in(read_v&&!stop&&!sticky),.r_addr_in({read_bank,read_row}),.rd_out(read_data),
  .w_ce_in(landing_write),.w_addr_in({p_bank,p_row}),.wd_in(w_data_q),.w_mask_in({256{1'b1}}),
  .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
endmodule
`default_nettype wire
