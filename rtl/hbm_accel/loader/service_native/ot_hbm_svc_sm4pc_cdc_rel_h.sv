`timescale 1ns/1ps
`default_nettype none
// HBM-SVGREL8 2026-10-20: HARDENED four-PC producer of the svg (ot_hbm_svc_sm4pc_cdc_rel_id at the r11 die parameters:
// OVERLAP 1, LBANKS 4, OPEN_IL 0; that module stays byte-identical).  Same descriptor format and checks, same overlap
// owners' address map, same landing identity checks, same fixed-pace drain (4,4,4,4,1 sectors per 5 stream edges after
// a start), same faults.  Changes (safe-design checklist + native census of the r11 mapped netlist):
//   * clocks: ONE stream root and ONE hbm root (the die ties stream_bank_clk / hbm_fifo_clk / hbm_pc_clk to the same PLL
//     nets; the tile is < 1 mm, so each family is one local tree; the only crossings are the reviewed Gray FIFOs);
//   * resets: synchronised leaves from the hard top (s_rst / h_rst, either port reset asserts both families, as the
//     original's reset_both), each <= 32 flops; datapath unreset;
//   * write path removed: the svg service is READ-ONLY (k_we / k_wdata / k_wstrb were constant 0 and k_wr_done only a
//     fault input): no tied functional ports;
//   * K request / response pins through 2-entry registered skids (ot_hbm_svc_pin_skid2_r32): registered pins, no
//     combinational kr_v -> kr_rdy path (+1 hbm edge request, +1 response: HBM boundary, elastic);
//   * the owners issue from the registered block fields one hbm edge after descriptor_fire (no descriptor mux);
//   * response -> landing FIFO: a PC's response ordinal[1:0] is its owner lane = its PC index (the strap PC set
//     {k,0..3}), so FIFO l only ever receives PC l%4: direct wiring, no 4:1 arbitration mux (an ordinal[1:0] != PC
//     response is a fault);
//   * drain output: 4 lanes x 8:1 x 256 b selected by REGISTERED one-hot copies of (read_ordinal + lane) % 8, KEPT per
//     lane per 32-bit slice (was 2.3k-load ordinal flops / 1k-load decode nets);
//   * the reserve reaches the 8 landing banks through registered per-bank copies (+1 stream edge on the bank side only;
//     see ot_hbm_svc_sm8_landing_bank_h); the stream-side bank epoch / total / completion init load while the landing
//     block is unallocated (a block is only read while allocated);
//   * block_ready_v / _bank / _epoch (unread by the feed) removed.
module ot_hbm_svc_sm4pc_cdc_rel_h #(parameter integer OWNER_AW=5, parameter integer RESPONSE_DEPTH=8,
 parameter integer LBANKS=4, parameter integer LB=(LBANKS>2)?2:1)(
 input wire [1:0] id_stack,input wire [2:0] id_sm,
 input wire stream_clk,hbm_clk,
 input wire [11:0] s_rst,input wire [14:0] h_rst,
 input wire [14:0] reserve_row_base,
 input wire reserve_v,output wire reserve_ready,input wire [31:0] reserve_base,
 input wire [11:0] reserve_total,input wire [LB-1:0] reserve_bank,input wire [15:0] reserve_epoch,
 output wire [LBANKS-1:0] block_ready,
 input wire start_v,input wire [LB-1:0] start_bank,input wire [15:0] start_epoch,
 output reg out_v,output reg [3:0] out_mask,output wire [1023:0] out_data,
 output reg [10:0] out_ordinal,output reg [LB-1:0] out_bank,output reg [15:0] out_epoch,
 output reg out_last,output wire fault,
 output wire [3:0] k_v,input wire [3:0] k_rdy,output wire [119:0] k_addr,
 output wire [15:0] k_len,output wire [67:0] k_tag,
 input wire [3:0] kr_v,output wire [3:0] kr_rdy,input wire [67:0] kr_tag,
 input wire [15:0] kr_beat,input wire [1023:0] kr_data
);
`ifdef SVGH_MUT
 localparam integer HM=`SVGH_MUT;     // HBM-SVGREL8 bench negative controls (see the kit README)
`else
 localparam integer HM=0;
`endif
 initial if(LBANKS!=4||OWNER_AW!=5||RESPONSE_DEPTH!=8)$fatal(1,"sm4pc_cdc_rel_h: r11 parameters only");
 // ---------------- reset leaves: s_rst [0] core, [1] reserve copies, [2] descriptor FIFO writer, [3] fault CDCs,
 // [4..11] landing banks; h_rst [0] core, [1] descriptor FIFO reader, [2..5] PCs (owner + skids), [6..13] banks (FIFO
 // writers), [14] CDCs.  The FIFOs / fault CDCs AND their two leaves into their own reviewed ot_reset_sync per side.
 wire[1:0]sc;wire[2:0]hc;
 ot_rst_fanout #(.N(2)) u_sc(.clk(stream_clk),.rst_n_in(s_rst[0]),.rst_n(sc));
 ot_rst_fanout #(.N(3)) u_hc(.clk(hbm_clk),.rst_n_in(h_rst[0]),.rst_n(hc));
 // strap identity (static): stream-side copies for the reserve check/PC set, hbm-side copy for the re-check
 reg [1:0] stack_s,stack_h;reg [2:0] sm_s;
 always @(posedge stream_clk)begin stack_s<=id_stack;sm_s<=id_sm;end
 always @(posedge hbm_clk)stack_h<=id_stack;
 // descriptor word {pcs20,row_base15,base32,total12,bank LB,epoch16}
 localparam integer T0=16+LB,A0=28+LB,S0=58+LB,R0=60+LB,P0=75+LB,DW=95+LB,IW=283+LB;
 wire [19:0] reserve_pcs={sm_s,2'd3,sm_s,2'd2,sm_s,2'd1,sm_s,2'd0}; // = the four PCs 4k..4k+3 of SM k
 wire [32:0] reserve_end={3'b0,reserve_base[29:0]}+reserve_total;
 wire pcs_unique=reserve_pcs[4:0]!=reserve_pcs[9:5]&&reserve_pcs[4:0]!=reserve_pcs[14:10]&&reserve_pcs[4:0]!=reserve_pcs[19:15]&&reserve_pcs[9:5]!=reserve_pcs[14:10]&&reserve_pcs[9:5]!=reserve_pcs[19:15]&&reserve_pcs[14:10]!=reserve_pcs[19:15];
 wire descriptor_ok=pcs_unique&&reserve_base[29:10]==0&&reserve_base[6:0]==0&&reserve_row_base<32768&&reserve_total!=0&&reserve_total<=512&&reserve_base[31:30]==stack_s&&reserve_end<=33'h040000000;
 reg [LBANKS-1:0] allocated,ready_q;
 reg [15:0] bank_epoch[0:LBANKS-1];reg [11:0] bank_total[0:LBANKS-1];
 reg [7:0] completed_q[0:LBANKS-1];reg stream_fault,hbm_fault;
 wire [7:0] bank_complete,bank_fault;wire [LB-1:0] bank_complete_bank[0:7];
 reg [7:0] complete_event[0:LBANKS-1];
 wire hbf2,stf2;
 ot_hbm_svc_fault_cdc u_hbm_fault_cdc(.wr_clk(hbm_clk),.wr_rst_n(h_rst[14]),
  .rd_clk(stream_clk),.rd_rst_n(s_rst[3]),.src_fault(hbm_fault),.dst_fault(hbf2),.wr_overflow(),.rd_underflow());
 ot_hbm_svc_fault_cdc u_stream_fault_cdc(.wr_clk(stream_clk),.wr_rst_n(s_rst[3]),
  .rd_clk(hbm_clk),.rd_rst_n(h_rst[14]),.src_fault(stream_fault),.dst_fault(stf2),.wr_overflow(),.rd_underflow());
 wire desc_wr_ready,desc_rd_valid,desc_rd_ready,desc_ov,desc_un;
 wire [DW-1:0] desc_data;
 wire desc_wr_reset,desc_rd_reset;
 ot_hbm_svc_local_and2 u_dwrreset(.a(s_rst[2]),.b(1'b1),.y(desc_wr_reset));
 ot_hbm_svc_local_and2 u_drdreset(.a(h_rst[1]),.b(1'b1),.y(desc_rd_reset));
 assign reserve_ready=sc[0]&&!allocated[reserve_bank]&&desc_wr_ready&&!fault;
 wire reserve_fire=reserve_v&&reserve_ready&&descriptor_ok;
 // HBM-COLLECT11 2026-10-21 (rel8e, COORDINATOR DECISION 2): the descriptor FIFO is DSN BIT-SLICED instances of the
 // reviewed ot_hbm_svc_async_fifo (byte-identical module, only WIDTH differs; each <= DSW = 5 bits so a slot-select
 // decode stays bounded (WIDTH5 DEPTH4 mapped max16); DW97 = 19 x 5 + 2).  Own pointers / synchronisers / reset syncs per instance.
 // LOCKSTEP as the landing banks: desc_wr_ready = &wr_ready (in reserve_ready, so reserve_fire offers to all only when
 // all are ready), desc_rd_valid = &rd_valid (pop only when all are valid), so every instance fires on the same edges
 // and all heads are the same descriptor while desc_rd_valid; per-instance push/pop enables carry KEPT qualifier flops.
 localparam integer DSW=5,DSN=(DW+DSW-1)/DSW;
 wire [DW-1:0] desc_wd={reserve_pcs,reserve_row_base,reserve_base,reserve_total,reserve_bank,reserve_epoch};
 wire [DSN-1:0] ds_wr_ready,ds_rd_valid,ds_ov,ds_un;
 (* keep="true",dont_touch="true" *) reg [DSN-1:0] dwq_k;   // stream-side per-slice push qualifiers
 (* keep="true",dont_touch="true" *) reg [DSN-1:0] drq_k;   // hbm-side per-slice pop qualifiers
 always @(posedge stream_clk or negedge s_rst[2])if(!s_rst[2])dwq_k<=0;else dwq_k<={DSN{1'b1}};
 always @(posedge hbm_clk or negedge h_rst[1])if(!h_rst[1])drq_k<=0;else drq_k<={DSN{1'b1}};
 assign desc_wr_ready=&ds_wr_ready;assign desc_rd_valid=&ds_rd_valid;
 assign desc_ov=|ds_ov;assign desc_un=|ds_un;
 genvar ds;
 generate for(ds=0;ds<DSN;ds=ds+1)begin:dsl
  localparam integer W=(ds==DSN-1)?(DW-DSW*(DSN-1)):DSW;
  ot_hbm_svc_async_fifo #(.WIDTH(W),.DEPTH(4)) u_descriptor(
   .wr_clk(stream_clk),.wr_rst_n(desc_wr_reset),.wr_valid(reserve_fire&&dwq_k[ds]),.wr_ready(ds_wr_ready[ds]),
   .wr_data(desc_wd[ds*DSW+:W]),.wr_overflow(ds_ov[ds]),
   .rd_clk(hbm_clk),.rd_rst_n(desc_rd_reset),.rd_valid(ds_rd_valid[ds]),.rd_ready(desc_rd_ready&&drq_k[ds]),
   .rd_data(desc_data[ds*DSW+:W]),.rd_underflow(ds_un[ds]));
 end endgenerate
 assign fault=stream_fault||hbf2||desc_ov||(|bank_fault);
 assign block_ready=ready_q;
 // ---------------- hbm side: block registers (load while no block is issuing), owners, skids, landing FIFO feed
 reg h_active;reg h_fresh;
 (* keep="true",dont_touch="true" *) reg [3:0] hidle_k;   // = !h_active (block-field capture enables, <= 32 b each)
 reg [LB-1:0] h_bank;reg [15:0] h_epoch;reg [29:0] h_base;reg [11:0] h_total;reg [19:0] h_pcs;reg [14:0] h_row_base;
 wire [11:0] rx_left[0:LBANKS-1];wire [3:0] issue_done;integer rb;
 wire [3:0] pc_fault,response_ok;wire [LB-1:0] response_bank[0:3];
 wire [10:0] response_ordinal[0:3];wire [15:0] response_epoch[0:3];
 wire descriptor_fire=desc_rd_valid&&desc_rd_ready;
 reg rx_any;always @*begin rx_any=0;for(rb=0;rb<LBANKS;rb=rb+1)if(rx_left[rb]!=0)rx_any=1;end
 assign desc_rd_ready=!h_active&&!hbm_fault&&hc[0]&&desc_rd_valid&&rx_left[desc_data[T0-1:16]]==0;
 wire desc_good=desc_data[S0+1:S0]==stack_h&&desc_data[T0+11:T0]!=0&&desc_data[T0+11:T0]<=512&&
                {3'b0,desc_data[A0+29:A0]}+desc_data[T0+11:T0]<=33'h040000000;
 // block-field captures: while no block issues AND the descriptor FIFO head is valid (storage read only under
 // rd_valid); one AND per <= 32-bit slice, each with its own KEPT idle copy
 // Real library gates split each capture hold-mux fanout into <=10-bit groups.
 wire[10:0]hcap;
 genvar ch;
 generate for(ch=0;ch<11;ch=ch+1)begin:cap_local
  localparam integer IDLE=(ch<2)?0:(ch<5)?1:(ch<9)?2:3;
  ot_hbm_svc_local_and2 u_gate(.a(hidle_k[IDLE]),.b(desc_rd_valid),.y(hcap[ch]));
 end endgenerate
 always @(posedge hbm_clk)begin
  if(hcap[0])h_pcs[9:0]<=desc_data[P0+:10];
  if(hcap[1])h_pcs[19:10]<=desc_data[P0+10+:10];
  if(hcap[2])h_base[9:0]<=desc_data[A0+:10];
  if(hcap[3])h_base[19:10]<=desc_data[A0+10+:10];
  if(hcap[4])h_base[29:20]<=desc_data[A0+20+:10];
  if(hcap[5])h_row_base[9:0]<=desc_data[R0+:10];
  if(hcap[6])h_row_base[14:10]<=desc_data[R0+10+:5];
  if(hcap[7])h_total[9:0]<=desc_data[T0+:10];
  if(hcap[8])h_total[11:10]<=desc_data[T0+10+:2];
  if(hcap[9])begin h_bank<=desc_data[T0-1:16];h_epoch[7:0]<=desc_data[7:0];end
  if(hcap[10])h_epoch[15:8]<=desc_data[15:8];
 end
 wire [7:0] fifo_wr_ready,fifo_ov;wire [7:0] fifo_wr_valid;wire [IW-1:0] fifo_wr_data[0:7];
 wire [3:0] ri_v,ri_r,ko_v,ko_r;wire [67:0] ri_tag,ko_tag;wire [15:0] ri_beat,ko_len;wire [1023:0] ri_data;wire [119:0] ko_addr;
 wire [3:0] lane_bad;
 wire [3:0] ri_owner,ri_pop,ri_feed,ri_count,owner_stop;
 genvar pc,g;
 generate for(pc=0;pc<4;pc=pc+1)begin:pc_owner
  wire[3:0]pr;
  ot_hbm_svc_local_and2 u_stopbuf(.a(hbm_fault),.b(1'b1),.y(owner_stop[pc]));
  ot_hbm_svc_local_and2 u_ownbuf(.a(ri_r[pc]),.b(1'b1),.y(ri_owner[pc]));
  ot_hbm_svc_local_and2 u_popbuf(.a(ri_r[pc]),.b(1'b1),.y(ri_pop[pc]));
  ot_hbm_svc_local_and2 u_feedbuf(.a(ri_r[pc]),.b(1'b1),.y(ri_feed[pc]));
  ot_hbm_svc_local_and2 u_countbuf(.a(ri_r[pc]),.b(1'b1),.y(ri_count[pc]));
  ot_rst_fanout #(.N(4)) u_pr(.clk(hbm_clk),.rst_n_in(h_rst[2+pc]),.rst_n(pr));
  ot_hbm_svc_prefetch_owner_rel_h #(.OWNER_AW(OWNER_AW),.LB(LB)) u_owner(
   .pc_id({id_sm,2'(pc)}),.clk(hbm_clk),.rst_n(pr[2:0]),.blk_start(h_fresh),
   .block_active(h_active),.block_base(h_base),.block_pcs(h_pcs),.block_row_base(h_row_base),.block_total(h_total),
   .block_bank(h_bank),.block_epoch(h_epoch),.stop(owner_stop[pc]),
   .k_ready(ko_r[pc]),.kr_v(ri_v[pc]),.kr_tag(ri_tag[17*pc+:17]),
   .kr_beat(ri_beat[4*pc+:4]),.response_take(ri_owner[pc]),
   .k_v(ko_v[pc]),.k_addr(ko_addr[30*pc+:30]),.k_len(ko_len[4*pc+:4]),.k_tag(ko_tag[17*pc+:17]),
   .response_ok(response_ok[pc]),.response_ordinal(response_ordinal[pc]),
   .response_epoch(response_epoch[pc]),.response_bank(response_bank[pc]),.fault(pc_fault[pc]),.issue_done(issue_done[pc]));
  ot_hbm_svc_pin_skid2_r32 #(.WIDTH(51)) u_kq(.clk(hbm_clk),.rst_n(pr[3]),.in_v(ko_v[pc]),.in_r(ko_r[pc]),
   .in_data({ko_tag[17*pc+:17],ko_len[4*pc+:4],ko_addr[30*pc+:30]}),.out_v(k_v[pc]),.out_r(k_rdy[pc]),
   .out_data({k_tag[17*pc+:17],k_len[4*pc+:4],k_addr[30*pc+:30]}));
  ot_hbm_svc_pin_skid2_r32 #(.WIDTH(277)) u_kr(.clk(hbm_clk),.rst_n(pr[3]),.in_v(kr_v[pc]),.in_r(kr_rdy[pc]),
   .in_data({kr_data[256*pc+:256],kr_beat[4*pc+:4],kr_tag[17*pc+:17]}),.out_v(ri_v[pc]),.out_r(ri_pop[pc]),
   .out_data({ri_data[256*pc+:256],ri_beat[4*pc+:4],ri_tag[17*pc+:17]}));
  // PC pc feeds landing FIFOs pc (ordinal[2]=0) and pc+4 (ordinal[2]=1) only
  assign lane_bad[pc]=response_ok[pc]&&response_ordinal[pc][1:0]!=2'(pc);
  assign ri_r[pc]=response_ok[pc]&&!lane_bad[pc]&&fifo_wr_ready[{response_ordinal[pc][2],2'(pc)}];
 end endgenerate
 generate for(g=0;g<8;g=g+1)begin:ffeed
  assign fifo_wr_valid[g]=ri_feed[g%4]&&response_ordinal[g%4][2]==(g/4);
  assign fifo_wr_data[g]={response_ordinal[g%4],response_bank[g%4],response_epoch[g%4],ri_data[256*(g%4)+:256]};
 end endgenerate
 integer h_take_b[0:LBANKS-1];integer tp;
 always @*begin
  for(rb=0;rb<LBANKS;rb=rb+1)begin
   h_take_b[rb]=0;
   for(tp=0;tp<4;tp=tp+1)if(ri_count[tp]&&response_bank[tp]==rb)h_take_b[rb]=h_take_b[rb]+1;
  end
 end
 // hc[0]: h_active, h_fresh, hbm_fault, hidle copies (7); hc[1] / hc[2]: rx_left of landing blocks 0-1 / 2-3 (24 each)
 always @(posedge hbm_clk or negedge hc[0])begin
  if(!hc[0])begin h_active<=0;h_fresh<=0;hbm_fault<=0;hidle_k<={4{1'b1}};end
  else begin
   if(stf2||desc_un||(|fifo_ov)||(|pc_fault)||(|lane_bad))hbm_fault<=1;
   if(descriptor_fire)begin
    if(!desc_good)hbm_fault<=1;
    else h_active<=1;
   end
   h_fresh<=descriptor_fire&&desc_good;
   hidle_k<={4{!(h_active?!(!descriptor_fire&&!h_fresh&&(&issue_done)):(descriptor_fire&&desc_good))}};
   // issue phase ends when every owner has issued the block; returns are counted per landing bank
   if(h_active&&!descriptor_fire&&!h_fresh&&(&issue_done))h_active<=0;
   if(descriptor_fire&&rx_left[desc_data[T0-1:16]]!=0)hbm_fault<=1;
   for(rb=0;rb<LBANKS;rb=rb+1)if(h_take_b[rb]!=0&&rx_left[rb]==0)hbm_fault<=1;
   if(|ri_v&&!descriptor_fire&&!rx_any)hbm_fault<=1;
  end
 end
 generate for(g=0;g<LBANKS;g=g+1)begin:g_rx
  reg [11:0] q;assign rx_left[g]=q;
  always @(posedge hbm_clk or negedge hc[1+g/2])
   if(!hc[1+g/2])q<=0;
   else q<=((descriptor_fire&&desc_data[T0-1:16]==g)?desc_data[T0+11:T0]:q)-12'(h_take_b[g]);
 end endgenerate
 // ---------------- stream side: registered per-bank reserve copies, landing banks, drain
 reg [7:0] rsv_v_k;reg [LB-1:0] rsv_bank_k[0:7];reg [15:0] rsv_epoch_k[0:7];reg [11:0] rsv_total_k[0:7];
 integer ri;
 always @(posedge stream_clk or negedge s_rst[1])if(!s_rst[1])rsv_v_k<=0;else rsv_v_k<={8{reserve_fire}};
 always @(posedge stream_clk)for(ri=0;ri<8;ri=ri+1)begin rsv_bank_k[ri]<=reserve_bank;rsv_epoch_k[ri]<=reserve_epoch;rsv_total_k[ri]<=reserve_total;end
 reg draining;reg [LB-1:0] drain_bank;reg [10:0] drain_ordinal;reg [2:0] drain_phase;
 wire [2:0] drain_count=drain_phase==4?3'd1:3'd4;
 wire [255:0] macro_data[0:7];
 wire [11:0] drain_total=bank_total[drain_bank];
 generate for(g=0;g<8;g=g+1)begin:ordinal_bank
  wire [11:0] candidate={3'b0,drain_ordinal[8:3],3'(g)}+((g<drain_ordinal[2:0])?12'd8:12'd0);
  ot_hbm_svc_sm8_landing_bank_h #(.BANK(g),.RESPONSE_DEPTH(RESPONSE_DEPTH),.LBANKS(LBANKS)) u_bank(
   .hbm_clk(hbm_clk),.hbm_rst_n(h_rst[6+g]),.stream_clk(stream_clk),.stream_rst_n(s_rst[4+g]),
   .in_v(fifo_wr_valid[g]),.in_ready(fifo_wr_ready[g]),.in_data(fifo_wr_data[g]),.overflow(fifo_ov[g]),
   .reserve_v(rsv_v_k[g]),.reserve_bank(rsv_bank_k[g]),.reserve_epoch(rsv_epoch_k[g]),.reserve_total(rsv_total_k[g]),.stop(fault),
   .complete_v(bank_complete[g]),.complete_bank(bank_complete_bank[g]),.fault(bank_fault[g]),
   .read_v(draining&&candidate<drain_ordinal+drain_count&&candidate<drain_total),.read_bank(drain_bank),.read_row(candidate[8:3]),.read_data(macro_data[g]));
 end endgenerate
 integer ci;
 always @*begin
  for(rb=0;rb<LBANKS;rb=rb+1)complete_event[rb]=0;
  for(ci=0;ci<8;ci=ci+1)if(bank_complete[ci])complete_event[bank_complete_bank[ci]][ci]=1;
 end
 // drain output select: osel_k[(lane*8+slice)*8+k] = ((read ordinal + lane) % 8 == k), registered from drain_ordinal
 // every edge (the original captured read_ordinal_q only while draining; out_data is only consumed with out_v, i.e.
 // the edge after a draining edge, where both agree)
 (* keep="true",dont_touch="true" *) reg [255:0] osel_k;
 integer ol,os,ok;
 always @(posedge stream_clk)for(ol=0;ol<4;ol=ol+1)for(os=0;os<8;os=os+1)for(ok=0;ok<8;ok=ok+1)
  osel_k[(ol*8+os)*8+ok]<=((drain_ordinal[2:0]+3'(ol)+((HM==2)?3'd1:3'd0))==3'(ok));
 generate for(g=0;g<4;g=g+1)begin:out_lane
  for(genvar s=0;s<8;s=s+1)begin:sl
   reg[31:0]o;integer k;
   always @*begin o=0;for(k=0;k<8;k=k+1)if(osel_k[(g*8+s)*8+k])o=o|macro_data[k][s*32+:32];end
   assign out_data[256*g+s*32+:32]=o;
  end
 end endgenerate
 // stream datapath: bank fields load while the landing block is unallocated (read only while allocated)
 wire[LBANKS-1:0] alloc_epoch,alloc_total,alloc_done;
 genvar ac;
 generate for(ac=0;ac<LBANKS;ac=ac+1)begin:allocation_local
  ot_hbm_svc_local_and2 u_e(.a(allocated[ac]),.b(1'b1),.y(alloc_epoch[ac]));
  ot_hbm_svc_local_and2 u_t(.a(allocated[ac]),.b(1'b1),.y(alloc_total[ac]));
  ot_hbm_svc_local_and2 u_c(.a(allocated[ac]),.b(1'b1),.y(alloc_done[ac]));
 end endgenerate
 integer si,sb;
 always @(posedge stream_clk)begin
  for(sb=0;sb<LBANKS;sb=sb+1)begin
   if(!alloc_epoch[sb])bank_epoch[sb]<=reserve_epoch;
   if(!alloc_total[sb])bank_total[sb]<=reserve_total;
  end
  if(draining&&!fault)begin out_bank<=drain_bank;out_epoch<=bank_epoch[drain_bank];out_ordinal<=drain_ordinal;end
 end
 // sc[1]: completion masks (32)
 always @(posedge stream_clk or negedge sc[1])begin
  if(!sc[1])for(sb=0;sb<LBANKS;sb=sb+1)completed_q[sb]<=0;
  else for(sb=0;sb<LBANKS;sb=sb+1)begin
   if(!alloc_done[sb])for(si=0;si<8;si=si+1)completed_q[sb][si]<=reserve_total<=si;
   else if(|complete_event[sb])completed_q[sb]<=completed_q[sb]|complete_event[sb];
  end
 end
 // sc[0]: control (32 flops)
 always @(posedge stream_clk or negedge sc[0])begin
  if(!sc[0])begin
   allocated<=0;ready_q<=0;stream_fault<=0;
   draining<=0;drain_bank<=0;drain_ordinal<=0;drain_phase<=0;
   out_v<=0;out_mask<=0;out_last<=0;
  end else begin
   out_v<=0;out_last<=0;out_mask<=0;
   if(reserve_v)begin
    if(!reserve_ready||!descriptor_ok)stream_fault<=1;
    else begin allocated[reserve_bank]<=1;ready_q[reserve_bank]<=0;end
   end
   for(sb=0;sb<LBANKS;sb=sb+1)if(|complete_event[sb])begin
    if(&(completed_q[sb]|complete_event[sb]))ready_q[sb]<=1;
   end
   if(start_v)begin
    if(draining||!ready_q[start_bank]||start_epoch!=bank_epoch[start_bank]||fault)stream_fault<=1;
    else begin draining<=1;drain_bank<=start_bank;drain_ordinal<=0;drain_phase<=0;ready_q[start_bank]<=0;end
   end
   if(draining&&!fault)begin
    out_v<=1;drain_phase<=drain_phase==4?0:drain_phase+1'b1;
    for(si=0;si<4;si=si+1)if(si<drain_count&&drain_ordinal+si<drain_total)out_mask[si]<=1;
    if(drain_ordinal+drain_count>=drain_total)begin
     out_last<=1;draining<=0;allocated[drain_bank]<=0;
    end else drain_ordinal<=drain_ordinal+drain_count;
   end
  end
 end
endmodule
`default_nettype wire
