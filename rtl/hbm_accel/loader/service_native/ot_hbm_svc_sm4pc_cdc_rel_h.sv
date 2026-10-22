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
 input wire [3*LB-1:0] start_bank_k,   // HBMc/TILES 10-22: distinct copies of start_bank (0/1 epoch lo/hi select, 2 ready/drain)
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
 // HBMc/TILES 10-22: sc[2] drain copies (dbank/dord, 87 flops -> own leaves sc[2..4]), sc[5] allocation + copies
 wire[7:0]sc;wire[3:0]hc;   // hc[3]: the 28 hfresh copies
 ot_rst_fanout #(.N(8)) u_sc(.clk(stream_clk),.rst_n_in(s_rst[0]),.rst_n(sc));
 ot_rst_fanout #(.N(4)) u_hc(.clk(hbm_clk),.rst_n_in(h_rst[0]),.rst_n(hc));
 // strap identity (static): stream-side copies for the reserve check/PC set, hbm-side copy for the re-check
 reg [1:0] stack_s,stack_h;reg [2:0] sm_s;
 (* keep="true",dont_touch="true" *) reg [2:0] sm_k[0:3];   // HBMc/TILES 10-22: per-PC-field strap copies (sm_s decodes had 64 loads)
 integer smk;
 always @(posedge stream_clk)begin stack_s<=id_stack;sm_s<=id_sm;for(smk=0;smk<4;smk=smk+1)sm_k[smk]<=id_sm;end
 always @(posedge hbm_clk)stack_h<=id_stack;
 // descriptor word {pcs20,row_base15,base32,total12,bank LB,epoch16}
 localparam integer T0=16+LB,A0=28+LB,S0=58+LB,R0=60+LB,P0=75+LB,DW=95+LB,IW=283+LB;
 wire [19:0] reserve_pcs={sm_k[3],2'd3,sm_k[2],2'd2,sm_k[1],2'd1,sm_k[0],2'd0}; // = the four PCs 4k..4k+3 of SM k
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
 // HBMc/TILES 10-22 (native census: the constant-input AND is transparent, and the 19 slices' identical both_reset ANDs
 // were merged into one 80-pin driver): per-group KEPT reset leaves (ot_rst_fanout, release +1 edge, boot only) give
 // each group of <= 4 slices its own distinct both_reset.
 localparam integer DRG=5;
 wire [DRG-1:0] dwr_leaf,drd_leaf;
 ot_rst_fanout #(.N(DRG)) u_dwr_leaf(.clk(stream_clk),.rst_n_in(s_rst[2]),.rst_n(dwr_leaf));
 ot_rst_fanout #(.N(DRG)) u_drd_leaf(.clk(hbm_clk),.rst_n_in(h_rst[1]),.rst_n(drd_leaf));
 assign desc_wr_reset=dwr_leaf[0];assign desc_rd_reset=drd_leaf[0];
 assign reserve_ready=sc[0]&&!allocated[reserve_bank]&&desc_wr_ready&&!fault;
 wire reserve_fire=reserve_v&&reserve_ready&&descriptor_ok;
 // HBMc/TILES 10-22: two kept copies of reserve_fire for the descriptor FIFO slices (one drove 34 loads)
 wire rf_ok=reserve_ready&&descriptor_ok;wire [1:0] rf_k;
 ot_hbm_svc_local_and2 u_rf0(.a(reserve_v),.b(rf_ok),.y(rf_k[0]));
 ot_hbm_svc_local_and2 u_rf1(.a(reserve_v),.b(rf_ok),.y(rf_k[1]));
 // HBM-COLLECT11 2026-10-21 (rel8e, COORDINATOR DECISION 2): the descriptor FIFO is DSN BIT-SLICED instances of the
 // reviewed ot_hbm_svc_async_fifo (byte-identical module, only WIDTH differs; each <= DSW = 5 bits so a slot-select
 // decode stays bounded (WIDTH5 DEPTH4 mapped max16); DW97 = 19 x 5 + 2).  Own pointers / synchronisers / reset syncs per instance.
 // LOCKSTEP as the landing banks: desc_wr_ready = &wr_ready (in reserve_ready, so reserve_fire offers to all only when
 // all are ready), desc_rd_valid = &rd_valid (pop only when all are valid), so every instance fires on the same edges
 // and all heads are the same descriptor while desc_rd_valid; per-instance push/pop enables carry KEPT qualifier flops.
 localparam integer DSW=5,DSN=(DW+DSW-1)/DSW;
 // second level: one KEPT reset leaf per descriptor slice (distinct both_reset per slice; see the landing bank)
 wire [DSN-1:0] dws_rst,drs_rst;
 for(genvar sg=0;sg<DRG;sg=sg+1)begin:g_dslice_leaf
  localparam integer NS=(DSN-4*sg<4)?DSN-4*sg:4;
  ot_rst_fanout #(.N(NS)) u_ws(.clk(stream_clk),.rst_n_in(dwr_leaf[sg]),.rst_n(dws_rst[4*sg+:NS]));
  ot_rst_fanout #(.N(NS)) u_rs(.clk(hbm_clk),.rst_n_in(drd_leaf[sg]),.rst_n(drs_rst[4*sg+:NS]));
 end
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
   .wr_clk(stream_clk),.wr_rst_n(dws_rst[ds]),.wr_valid(rf_k[ds%2]&&dwq_k[ds]),.wr_ready(ds_wr_ready[ds]),
   .wr_data(desc_wd[ds*DSW+:W]),.wr_overflow(ds_ov[ds]),
   .rd_clk(hbm_clk),.rd_rst_n(drs_rst[ds]),.rd_valid(ds_rd_valid[ds]),.rd_ready(desc_rd_ready&&drq_k[ds]),
   .rd_data(desc_data[ds*DSW+:W]),.rd_underflow(ds_un[ds]));
 end endgenerate
 assign fault=stream_fault||hbf2||desc_ov||(|bank_fault);
 assign block_ready=ready_q;
 // ---------------- hbm side: block registers (load while no block is issuing), owners, skids, landing FIFO feed
 reg h_active;reg h_fresh;
 // HBMc/TILES 10-22 (native census: constant-input AND "buffers" are transparent): KEPT same-edge copies replace them --
 // h_fresh per owner (k: 118 loads through four u_startbuf), the row-low capture per owner (33).
 (* keep="true",dont_touch="true" *) reg [31:0] hfresh_k;   // [8*pc]: owner, [8*pc+1+r]: table region r, [8*pc+5]: cursor, [8*pc+6/7]: t / tu
 (* keep="true",dont_touch="true" *) reg [1:0] rowlow_k[0:3];
 (* keep="true",dont_touch="true" *) reg [11:0] tot_k[0:3];   // per-owner block_total copies (h_total had 128 loads)
 (* keep="true",dont_touch="true" *) reg [11:0] totb_k[0:3];  // second per-owner copy: the words range compare
 wire [3:0] hcapt,hcaptb;
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
 for(genvar ct=0;ct<4;ct=ct+1)begin:cap_total
  ot_hbm_svc_local_and2 u_gate(.a(hidle_k[3]),.b(desc_rd_valid),.y(hcapt[ct]));
  ot_hbm_svc_local_and2 u_gate_b(.a(hidle_k[2]),.b(desc_rd_valid),.y(hcaptb[ct]));
 end
 always @(posedge hbm_clk)begin
  if(hcap[0])h_pcs[9:0]<=desc_data[P0+:10];
  if(hcap[1])h_pcs[19:10]<=desc_data[P0+10+:10];
  if(hcap[2])h_base[9:0]<=desc_data[A0+:10];
  if(hcap[3])h_base[19:10]<=desc_data[A0+10+:10];
  if(hcap[4])h_base[29:20]<=desc_data[A0+20+:10];
  if(hcap[5])h_row_base[9:0]<=desc_data[R0+:10];
  for(rb=0;rb<4;rb=rb+1)if(hcap[5])rowlow_k[rb]<=desc_data[R0+:2];
  for(rb=0;rb<4;rb=rb+1)if(hcapt[rb])tot_k[rb]<=desc_data[T0+:12];
  for(rb=0;rb<4;rb=rb+1)if(hcaptb[rb])totb_k[rb]<=desc_data[T0+:12];
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
  wire[5:0]pr;
  wire local_start,local_active;
  wire[1:0] local_row_low;
  assign local_row_low=rowlow_k[pc];
  assign local_start=hfresh_k[8*pc];
  ot_hbm_svc_local_and2 u_activebuf(.a(h_active),.b(1'b1),.y(local_active));
  ot_hbm_svc_local_and2 u_stopbuf(.a(hbm_fault),.b(1'b1),.y(owner_stop[pc]));
  // ri_r computed by four separate kept leaves (one per consumer family), same function
  wire ri_ready=fifo_wr_ready[{response_ordinal[pc][2],2'(pc)}];
  ot_hbm_svc_and3_leaf u_ownbuf(.a(response_ok[pc]),.b(!lane_bad[pc]),.c(ri_ready),.y(ri_owner[pc]));
  ot_hbm_svc_and3_leaf u_popbuf(.a(response_ok[pc]),.b(!lane_bad[pc]),.c(ri_ready),.y(ri_pop[pc]));
  ot_hbm_svc_and3_leaf u_feedbuf(.a(response_ok[pc]),.b(!lane_bad[pc]),.c(ri_ready),.y(ri_feed[pc]));
  ot_hbm_svc_and3_leaf u_countbuf(.a(response_ok[pc]),.b(!lane_bad[pc]),.c(ri_ready),.y(ri_count[pc]));
  ot_rst_fanout #(.N(6)) u_pr(.clk(hbm_clk),.rst_n_in(h_rst[2+pc]),.rst_n(pr));
  ot_hbm_svc_prefetch_owner_rel_h #(.OWNER_AW(OWNER_AW),.LB(LB)) u_owner(
   .pc_id({id_sm,2'(pc)}),.clk(hbm_clk),.rst_n(pr[4:0]),.blk_start(local_start),.blk_start_k(hfresh_k[8*pc+1+:4]),.blk_start_c(hfresh_k[8*pc+5]),.blk_start_t(hfresh_k[8*pc+6]),.blk_start_u(hfresh_k[8*pc+7]),.block_total_b(totb_k[pc]),
   .block_active(local_active),.block_base(h_base),.block_pcs(h_pcs),.block_row_base({h_row_base[14:2],local_row_low}),.block_total(tot_k[pc]),
   .block_bank(h_bank),.block_epoch(h_epoch),.stop(owner_stop[pc]),
   .k_ready(ko_r[pc]),.kr_v(ri_v[pc]),.kr_tag(ri_tag[17*pc+:17]),
   .kr_beat(ri_beat[4*pc+:4]),.response_take(ri_owner[pc]),
   .k_v(ko_v[pc]),.k_addr(ko_addr[30*pc+:30]),.k_len(ko_len[4*pc+:4]),.k_tag(ko_tag[17*pc+:17]),
   .response_ok(response_ok[pc]),.response_ordinal(response_ordinal[pc]),
   .response_epoch(response_epoch[pc]),.response_bank(response_bank[pc]),.fault(pc_fault[pc]),.issue_done(issue_done[pc]));
  ot_hbm_svc_pin_skid2_r32 #(.WIDTH(51)) u_kq(.clk(hbm_clk),.rst_n(pr[5]),.in_v(ko_v[pc]),.in_r(ko_r[pc]),
   .in_data({ko_tag[17*pc+:17],ko_len[4*pc+:4],ko_addr[30*pc+:30]}),.out_v(k_v[pc]),.out_r(k_rdy[pc]),
   .out_data({k_tag[17*pc+:17],k_len[4*pc+:4],k_addr[30*pc+:30]}));
  ot_hbm_svc_pin_skid2_r32 #(.WIDTH(277)) u_kr(.clk(hbm_clk),.rst_n(pr[5]),.in_v(kr_v[pc]),.in_r(kr_rdy[pc]),
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
 // two kept ANDs (descriptor_fire && desc_good), 16 copies each (one AND drove 35-43 loads)
 wire dfg_a,dfg_b;
 ot_hbm_svc_local_and2 u_dfg_a(.a(descriptor_fire),.b(desc_good),.y(dfg_a));
 ot_hbm_svc_local_and2 u_dfg_b(.a(descriptor_fire),.b(desc_good),.y(dfg_b));
 always @(posedge hbm_clk or negedge hc[3])if(!hc[3])hfresh_k<=0;else hfresh_k<={{16{dfg_b}},{16{dfg_a}}};
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
  wire capture;
  ot_hbm_svc_local_and2 u_capture(.a(descriptor_fire),.b(desc_data[T0-1:16]==g),.y(capture));
  always @(posedge hbm_clk or negedge hc[1+g/2])
   if(!hc[1+g/2])q<=0;
   else q<=((capture)?desc_data[T0+11:T0]:q)-12'(h_take_b[g]);
 end endgenerate
 // ---------------- stream side: registered per-bank reserve copies, landing banks, drain
 // HBMc/TILES 10-22: KEPT (yosys had merged the 8 identical per-bank copies: one decode drove 64 ren_k flops)
 (* keep="true",dont_touch="true" *) reg [7:0] rsv_v_k;
 (* keep="true",dont_touch="true" *) reg [LB-1:0] rsv_bank_k[0:7];
 (* keep="true",dont_touch="true" *) reg [15:0] rsv_epoch_k[0:7];
 (* keep="true",dont_touch="true" *) reg [11:0] rsv_total_k[0:7];
 integer ri;
 always @(posedge stream_clk or negedge s_rst[1])if(!s_rst[1])rsv_v_k<=0;else rsv_v_k<={8{reserve_fire}};
 always @(posedge stream_clk)for(ri=0;ri<8;ri=ri+1)begin rsv_bank_k[ri]<=reserve_bank;rsv_epoch_k[ri]<=reserve_epoch;rsv_total_k[ri]<=reserve_total;end
 reg draining;reg [LB-1:0] drain_bank;reg [10:0] drain_ordinal;reg [2:0] drain_phase;
 wire [2:0] drain_count=drain_phase==4?3'd1:3'd4;
 wire [255:0] macro_data[0:7];
 // HBMc/TILES 10-22 (native census: drain_bank 113 / drain_ordinal 70 loads): KEPT copies loaded with the registers' next
 // values (same reset, same edge).  bank k: 0 total / allocation, 1 output fields, 2 / 3 landing reads 0-3 / 4-7;
 // ordinal k: 0-3 output-lane selects, 4 / 5 landing candidates 0-3 / 4-7, 6 output / total compare.
 wire start_acc;wire drain_last;
 wire [LB-1:0] sbk0=start_bank_k[0+:LB],sbk1=start_bank_k[LB+:LB],sbk2=start_bank_k[2*LB+:LB];
 wire [LB-1:0] drain_bank_n=start_acc?sbk2:drain_bank;
 wire [10:0] drain_ordinal_n=(draining&&!fault&&!drain_last)?drain_ordinal+drain_count:(start_acc?11'd0:drain_ordinal);
 (* keep="true",dont_touch="true" *) reg [12*LB-1:0] dbank_v;   // k4 allocation clear, k5 out epoch hi, k6 out bank, k7..k10 bank-read totals lo/hi, k11 drain total hi     // flat vectors: no memory inference under the async reset
 (* keep="true",dont_touch="true" *) reg [7*11-1:0] dord_v;
 always @(posedge stream_clk or negedge sc[2])
  if(!sc[2])dbank_v<=0;else dbank_v<={12{drain_bank_n}};
 for(genvar dg=0;dg<7;dg=dg+1)begin:g_dord_rst
  always @(posedge stream_clk or negedge sc[3+dg/2])
   if(!sc[3+dg/2])dord_v[dg*11+:11]<=0;else dord_v[dg*11+:11]<=drain_ordinal_n;
 end
 wire [LB-1:0] dbank_k[0:11];wire [10:0] dord_k[0:6];
 for(genvar dk=0;dk<12;dk=dk+1)begin:g_dbank assign dbank_k[dk]=dbank_v[dk*LB+:LB]; end
 for(genvar dk=0;dk<7;dk=dk+1)begin:g_dord assign dord_k[dk]=dord_v[dk*11+:11]; end
 wire [11:0] drain_total={bank_total[dbank_k[11]][11:6],bank_total[dbank_k[0]][5:0]};
 wire [11:0] drain_total_r[0:1];   // per landing-bank half (same value; drain_total had 35 loads)
 assign drain_total_r[0]={bank_total[dbank_k[9]][11:6],bank_total[dbank_k[7]][5:0]};
 assign drain_total_r[1]={bank_total[dbank_k[10]][11:6],bank_total[dbank_k[8]][5:0]};
 assign drain_last=dord_k[6]+drain_count>=drain_total;
 generate for(g=0;g<8;g=g+1)begin:ordinal_bank
  wire [10:0] dord_g=dord_k[4+g/4];
  wire [11:0] candidate={3'b0,dord_g[8:3],3'(g)}+((g<dord_g[2:0])?12'd8:12'd0);
  ot_hbm_svc_sm8_landing_bank_h #(.BANK(g),.RESPONSE_DEPTH(RESPONSE_DEPTH),.LBANKS(LBANKS)) u_bank(
   .hbm_clk(hbm_clk),.hbm_rst_n(h_rst[6+g]),.stream_clk(stream_clk),.stream_rst_n(s_rst[4+g]),
   .in_v(fifo_wr_valid[g]),.in_ready(fifo_wr_ready[g]),.in_data(fifo_wr_data[g]),.overflow(fifo_ov[g]),
   .reserve_v(rsv_v_k[g]),.reserve_bank(rsv_bank_k[g]),.reserve_epoch(rsv_epoch_k[g]),.reserve_total(rsv_total_k[g]),.stop(fault),
   .complete_v(bank_complete[g]),.complete_bank(bank_complete_bank[g]),.fault(bank_fault[g]),
   .read_v(draining&&candidate<dord_g+drain_count&&candidate<drain_total_r[g/4]),.read_bank(dbank_k[2+g/4]),.read_row(candidate[8:3]),.read_data(macro_data[g]));
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
 wire[2:0] select_ordinal[0:3];
 for(genvar so=0;so<4;so=so+1)begin:g_select_ordinal
  assign select_ordinal[so]=dord_k[so][2:0];
 end
 integer ol,os,ok;
 always @(posedge stream_clk)for(ol=0;ol<4;ol=ol+1)for(os=0;os<8;os=os+1)for(ok=0;ok<8;ok=ok+1)
  osel_k[(ol*8+os)*8+ok]<=((select_ordinal[ol]+3'(ol)+((HM==2)?3'd1:3'd0))==3'(ok));
 generate for(g=0;g<4;g=g+1)begin:out_lane
  for(genvar s=0;s<8;s=s+1)begin:sl
   reg[31:0]o;integer k;
   always @*begin o=0;for(k=0;k<8;k=k+1)if(osel_k[(g*8+s)*8+k])o=o|macro_data[k][s*32+:32];end
   assign out_data[256*g+s*32+:32]=o;
  end
 end endgenerate
 // stream datapath: bank fields load while the landing block is unallocated (read only while allocated)
 // allocation: KEPT copies per consumer family loaded with allocated's next value (k: allocated 61 loads)
 wire[LBANKS-1:0] alloc_epoch,alloc_total,alloc_done;
 reg [LBANKS-1:0] allocated_n;
 always @*begin
  allocated_n=allocated;
  if(reserve_fire)allocated_n[reserve_bank]=1;
  if(draining&&!fault&&drain_last)allocated_n[dbank_k[4]]=0;
 end
 (* keep="true",dont_touch="true" *) reg [LBANKS-1:0] alloc_e_k,alloc_eh_k,alloc_t_k,alloc_d_k;
 assign alloc_epoch=alloc_e_k;assign alloc_total=alloc_t_k;assign alloc_done=alloc_d_k;
 wire out_epoch_capture,out_ordinal_capture,out_bank_capture;
 ot_hbm_svc_local_and2 u_oec(.a(draining),.b(!fault),.y(out_epoch_capture));
 ot_hbm_svc_local_and2 u_ooc(.a(draining),.b(!fault),.y(out_ordinal_capture));
 ot_hbm_svc_local_and2 u_obc(.a(draining),.b(!fault),.y(out_bank_capture));
 integer si,sb;
 always @(posedge stream_clk)begin
  for(sb=0;sb<LBANKS;sb=sb+1)begin
   if(!alloc_epoch[sb])bank_epoch[sb][7:0]<=reserve_epoch[7:0];
   if(!alloc_eh_k[sb])bank_epoch[sb][15:8]<=reserve_epoch[15:8];
   if(!alloc_total[sb])bank_total[sb]<=reserve_total;
  end
  if(out_bank_capture)out_bank<=dbank_k[6];
  if(out_epoch_capture)out_epoch<={bank_epoch[dbank_k[5]][15:8],bank_epoch[dbank_k[1]][7:0]};
  if(out_ordinal_capture)out_ordinal<=dord_k[6];
 end
 // Each completion-mask reset branch drives eight state flops.
 genvar cm;
 generate for(cm=0;cm<LBANKS;cm=cm+1)begin:g_completion_mask
  wire reset_n;
  ot_hbm_svc_local_and2 u_reset(.a(sc[1]),.b(1'b1),.y(reset_n));
  integer bit_index;
  always @(posedge stream_clk or negedge reset_n)begin
   if(!reset_n)completed_q[cm]<=0;
   else if(!alloc_done[cm])for(bit_index=0;bit_index<8;bit_index=bit_index+1)completed_q[cm][bit_index]<=reserve_total<=bit_index;
   else if(|complete_event[cm])completed_q[cm]<=completed_q[cm]|complete_event[cm];
  end
 end endgenerate
 // Allocation state uses a real separate reset branch, with identical release edge.
 wire allocated_reset_n;
 assign allocated_reset_n=sc[7];
 always @(posedge stream_clk or negedge allocated_reset_n)begin
  if(!allocated_reset_n)begin allocated<=0;alloc_e_k<=0;alloc_eh_k<=0;alloc_t_k<=0;alloc_d_k<=0;end
  else begin allocated<=allocated_n;alloc_e_k<=allocated_n;alloc_eh_k<=allocated_n;alloc_t_k<=allocated_n;alloc_d_k<=allocated_n;end
 end
 wire [15:0] start_epoch_ref={bank_epoch[sbk1][15:8],bank_epoch[sbk0][7:0]};
 assign start_acc=start_v&&!(draining||!ready_q[sbk2]||start_epoch!=start_epoch_ref||fault);
 // sc[0]: remaining stream controls
 always @(posedge stream_clk or negedge sc[0])begin
  if(!sc[0])begin
   ready_q<=0;stream_fault<=0;
   draining<=0;drain_bank<=0;drain_ordinal<=0;drain_phase<=0;
   out_v<=0;out_mask<=0;out_last<=0;
  end else begin
   out_v<=0;out_last<=0;out_mask<=0;
   if(reserve_v)begin
    if(!reserve_ready||!descriptor_ok)stream_fault<=1;
    else begin ready_q[reserve_bank]<=0;end
   end
   for(sb=0;sb<LBANKS;sb=sb+1)if(|complete_event[sb])begin
    if(&(completed_q[sb]|complete_event[sb]))ready_q[sb]<=1;
   end
   if(start_v)begin
    if(!start_acc)stream_fault<=1;
    else begin draining<=1;drain_bank<=sbk2;drain_ordinal<=0;drain_phase<=0;ready_q[sbk2]<=0;end
   end
   if(draining&&!fault)begin
    out_v<=1;drain_phase<=drain_phase==4?0:drain_phase+1'b1;
    for(si=0;si<4;si=si+1)if(si<drain_count&&dord_k[6]+si<drain_total)out_mask[si]<=1;
    if(drain_last)begin
     out_last<=1;draining<=0;
    end else drain_ordinal<=drain_ordinal+drain_count;
   end
  end
 end
endmodule
// HBMc/TILES 10-22: kept 3-input AND leaf: one instance per consumer family gives a distinct driver of the same function.
(* keep_hierarchy=1 *) module ot_hbm_svc_and3_leaf(input wire a,b,c,output wire y);
 assign y=a&&b&&c;
endmodule
`default_nettype wire
