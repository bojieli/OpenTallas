`timescale 1ns/1ps
`default_nettype none
// HBM-REFORM-B4 d44v part 25: ot_hbm_svc_wb_kport_q as 4 x root tile + 1 switch tile, registered faces, inside the kept 475.2 slot.
// Flat form was 374k cells, 32 macros, about 80% of the slot. Same pins, same stream-side behaviour, same set of K writes, later done.
//
// STRUCTURE
//  ot_wbq_root (8 lanes, 8 macros, 8 lane FIFOs, 2 lane groups): fill and copy state run locally. The fill control comes straight from the
//    parent pins, so the wd data needs no delay stages to line up with it: pin +1 face = the same cycle the flat block saw on +2 (wd_q).
//  ot_wbq_sw: reservation and copy control, the kport_q wrapper (receipts, wa, wb_ready, window command), K ports.
// LANE GROUPS: 4 consecutive ordinals share a PC, since PC = o[5:2]^o[9:6]^o[14:11] does not read o[1:0]. So a root offers 2 sectors per edge,
//    one per group (lowest non-empty lane), and the K switch is 16 x 8:1 instead of 16 x 32:1. Steady rate: a row of 32 lanes is 8 groups on
//    8 PCs, so on one row the flat block also drains 8 per edge. Across rows the flat block peaks at 16 per edge, this form stays at 8 per edge,
//    the fill rate of the stream, so a catch-up after a K stall is slower. Perf loss, listed for the token lane.
// SEAM root->sw is push + credit: each group has a CRED-entry queue in sw, the root sends only with a credit in hand.
// NOT edge-identical to the flat block: K order may differ, done moves later behind the variable HBM wait (bench reports the delta).
// All clock pins carry the one core clock (face_shell: "all clock ports carry the one core clock"); the two lane FIFO clock pins stay as they were.
// MUT (bench only, root): 1 = group 1 stops getting credits after 9 sends (hang), 2 = credit counter starts at CRED+1 (queue overflow).

module ot_wbq_root #(parameter integer CRED=4, parameter integer MUT=0)(
 input wire hbm_clk,fifo_clk,stream_rst_n,hbm_rst_n,
 input wire [1:0] root_id,                // from sw, static after reset
 input wire reserve_v,reserve_bank,input wire [11:0] reserve_total,input wire [29:0] reserve_base,
 input wire fill_start,fill_start_bank,
 input wire [255:0] wd0,wd1,wd2,wd3,wd4,wd5,wd6,wd7,input wire [7:0] wd_v,
 input wire copy_on,copy_bank,s_stop,h_stop,
 input wire [1:0] g_credit,
 output wire root_ready,
 output wire [1:0] g_v,output wire [571:0] g_d
);
 wire reset_both=stream_rst_n&&hbm_rst_n;
 wire srst,hrst;
 ot_reset_sync u_root_reset(.clk(fifo_clk),.async_rst_n(reset_both),.sync_rst_n(srst));
 ot_reset_sync u_hbm_reset(.clk(hbm_clk),.async_rst_n(reset_both),.sync_rst_n(hrst));
 assign root_ready=srst;
 wire [255:0] wd[0:7];
 assign wd[0]=wd0;assign wd[1]=wd1;assign wd[2]=wd2;assign wd[3]=wd3;assign wd[4]=wd4;assign wd[5]=wd5;assign wd[6]=wd6;assign wd[7]=wd7;
 reg [31:0] base[0:1];reg [11:0] total[0:1];reg [11:0] committed[0:1];
 reg filling,fill_bank;reg [11:0] ordinal;
 reg copy_q;reg [6:0] copy_row[0:7];reg [5:0] pending_row[0:7];reg [7:0] read_pending;
 wire [7:0] fifo_full,fifo_empty,fifo_we,fifo_re,mem_read;
 wire [287:0] fifo_head[0:7];wire [255:0] mem_data[0:7];
 genvar g;
 generate for(g=0;g<8;g=g+1)begin:g_lane
  wire [4:0] lane={root_id,3'(g)};
  wire [6:0] row=copy_row[g];
  wire [31:0] sector=base[copy_bank]+{pending_row[g],5'b0}+lane;
  assign fifo_we[g]=copy_q&&read_pending[g]&&!fifo_full[g]&&!s_stop;
  assign mem_read[g]=copy_q&&(!read_pending[g]||fifo_we[g])&&row*32+int'(lane)<committed[copy_bank]&&!s_stop;
  ot_hbm_accel_cdc_fifo #(.W(288),.AW(2)) u_fifo(
   .wclk(fifo_clk),.wrst_n(srst),.we(fifo_we[g]),.wdata({sector,mem_data[g]}),.full(fifo_full[g]),.rd_freed(),
   .rclk(hbm_clk),.rrst_n(hrst),.re(fifo_re[g]),.rdata(fifo_head[g]),.empty(fifo_empty[g]));
`ifdef OT_WBQ_N1M   // DIE-HBM-82-EP6 11-06 opt-in: same 128 x 256 payload in the one-mask-pin, no-repair master (530 pins, 91.8 x 27.576;
                     // the r2c2 form has 819 pins: a 256-bit mask tied to ones and repair ports tied 0). Same word, same contract.
  ot_sram_1r1w_128x256_m1_r0c0_g256 u_payload(
   .clk(fifo_clk),.r_ce_in(mem_read[g]),.r_addr_in({copy_bank,row[5:0]}),.rd_out(mem_data[g]),
   .w_ce_in(filling&&!s_stop&&ordinal+g<total[fill_bank]&&ordinal[4:3]==root_id&&wd_v[g]),
   .w_addr_in({fill_bank,ordinal[10:5]}),.wd_in(wd[g]),.w_mask_in(1'b1));
`else
  ot_sram_1r1w_128x256_m1_r2c2 u_payload(
   .clk(fifo_clk),.r_ce_in(mem_read[g]),.r_addr_in({copy_bank,row[5:0]}),.rd_out(mem_data[g]),
   .w_ce_in(filling&&!s_stop&&ordinal+g<total[fill_bank]&&ordinal[4:3]==root_id&&wd_v[g]),
   .w_addr_in({fill_bank,ordinal[10:5]}),.wd_in(wd[g]),.w_mask_in({256{1'b1}}),
   .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
`endif
 end endgenerate
 integer s;
 always @(posedge fifo_clk or negedge srst)begin
  if(!srst)begin
   filling<=0;fill_bank<=0;ordinal<=0;copy_q<=0;read_pending<=0;
   for(s=0;s<2;s=s+1)begin base[s]<=0;total[s]<=0;committed[s]<=0;end
   for(s=0;s<8;s=s+1)begin copy_row[s]<=0;pending_row[s]<=0;end
  end else begin
   if(reserve_v)begin base[reserve_bank]<={2'b00,reserve_base};total[reserve_bank]<=reserve_total;committed[reserve_bank]<=0;end
   if(fill_start)begin filling<=1;fill_bank<=fill_start_bank;ordinal<=0;end
   if(filling&&!s_stop)begin
    if(ordinal+8>=total[fill_bank])begin filling<=0;committed[fill_bank]<=total[fill_bank];end
    else begin ordinal<=ordinal+8;committed[fill_bank]<=((ordinal+12'd8)>>5)<<5;end
   end
   copy_q<=copy_on;
   if(copy_on&&!copy_q)begin
    read_pending<=0;
    for(s=0;s<8;s=s+1)begin copy_row[s]<=0;pending_row[s]<=0;end
   end else begin
    for(s=0;s<8;s=s+1)begin
     if(fifo_we[s])read_pending[s]<=0;
     if(mem_read[s])begin read_pending[s]<=1;pending_row[s]<=copy_row[s][5:0];copy_row[s]<=copy_row[s]+1'b1;end
    end
   end
  end
 end
 // lane groups: lowest non-empty lane, sent when a credit is held
 reg [2:0] credit[0:1];integer mc;
 generate for(g=0;g<2;g=g+1)begin:g_group
  wire [3:0] ne=~fifo_empty[4*g+:4];
  wire [1:0] sel=ne[0]?2'd0:ne[1]?2'd1:ne[2]?2'd2:2'd3;
  wire send=(|ne)&&credit[g]!=0&&!h_stop&&hrst;
  assign g_v[g]=send;
  assign g_d[286*g+:286]=fifo_head[4*g+sel][285:0];
  assign fifo_re[4*g+:4]=send?(4'b1<<sel):4'b0;
  always @(posedge hbm_clk or negedge hrst)begin
   if(!hrst)credit[g]<=(MUT==2)?3'(CRED+1):3'(CRED);
   else credit[g]<=credit[g]-3'(send)+3'(g_credit[g]&&!(MUT==1&&g==1&&mc>=9));
  end
 end endgenerate
 always @(posedge hbm_clk or negedge hrst)if(!hrst)mc<=0;else if(g_v[1])mc<=mc+1;
endmodule

// DIE-HBM-82-EP6 11-06 (DIE-HBM-82 ruling 19:1x, split on the natural boundary): ot_wbq_root_grp = one lane group G of
// ot_wbq_root (lanes 4G..4G+3, their fifos, the group pick and credit), with the fill/copy control replicated (every copy sees
// the same inputs, so every copy holds the same state). The two groups share no signal, so the split has no seam; the
// composition ot_wbq_root_g2 is cycle-exact against ot_wbq_root with OT_WBQ_N1M (payload master ot_sram_1r1w_128x256_m1_r0c0_g256).
module ot_wbq_root_grp #(parameter integer G=0, parameter integer CRED=4, parameter integer MUT=0)(
 input wire hbm_clk,fifo_clk,stream_rst_n,hbm_rst_n,
 input wire [1:0] root_id,
 input wire reserve_v,reserve_bank,input wire [11:0] reserve_total,input wire [29:0] reserve_base,
 input wire fill_start,fill_start_bank,
 input wire [255:0] wd0,wd1,wd2,wd3,input wire [3:0] wd_v,
 input wire copy_on,copy_bank,s_stop,h_stop,
 input wire g_credit,
 output wire root_ready,
 output wire g_v,output wire [285:0] g_d
);
 wire reset_both=stream_rst_n&&hbm_rst_n;
 wire srst,hrst;
 ot_reset_sync u_root_reset(.clk(fifo_clk),.async_rst_n(reset_both),.sync_rst_n(srst));
 ot_reset_sync u_hbm_reset(.clk(hbm_clk),.async_rst_n(reset_both),.sync_rst_n(hrst));
 assign root_ready=srst;
 wire [255:0] wd[0:3];
 assign wd[0]=wd0;assign wd[1]=wd1;assign wd[2]=wd2;assign wd[3]=wd3;
 reg [31:0] base[0:1];reg [11:0] total[0:1];reg [11:0] committed[0:1];
 reg filling,fill_bank;reg [11:0] ordinal;
 reg copy_q;reg [6:0] copy_row[0:3];reg [5:0] pending_row[0:3];reg [3:0] read_pending;
 wire [3:0] fifo_full,fifo_empty,fifo_we,fifo_re,mem_read;
 wire [287:0] fifo_head[0:3];wire [255:0] mem_data[0:3];
 genvar g;
 generate for(g=0;g<4;g=g+1)begin:g_lane
  localparam integer GL=4*G+g;
  wire [4:0] lane={root_id,3'(GL)};
  wire [6:0] row=copy_row[g];
  wire [31:0] sector=base[copy_bank]+{pending_row[g],5'b0}+lane;
  assign fifo_we[g]=copy_q&&read_pending[g]&&!fifo_full[g]&&!s_stop;
  assign mem_read[g]=copy_q&&(!read_pending[g]||fifo_we[g])&&row*32+int'(lane)<committed[copy_bank]&&!s_stop;
  ot_hbm_accel_cdc_fifo #(.W(288),.AW(2)) u_fifo(
   .wclk(fifo_clk),.wrst_n(srst),.we(fifo_we[g]),.wdata({sector,mem_data[g]}),.full(fifo_full[g]),.rd_freed(),
   .rclk(hbm_clk),.rrst_n(hrst),.re(fifo_re[g]),.rdata(fifo_head[g]),.empty(fifo_empty[g]));
  ot_sram_1r1w_128x256_m1_r0c0_g256 u_payload(
   .clk(fifo_clk),.r_ce_in(mem_read[g]),.r_addr_in({copy_bank,row[5:0]}),.rd_out(mem_data[g]),
   .w_ce_in(filling&&!s_stop&&ordinal+GL<total[fill_bank]&&ordinal[4:3]==root_id&&wd_v[g]),
   .w_addr_in({fill_bank,ordinal[10:5]}),.wd_in(wd[g]),.w_mask_in(1'b1));
 end endgenerate
 integer s;
 always @(posedge fifo_clk or negedge srst)begin
  if(!srst)begin
   filling<=0;fill_bank<=0;ordinal<=0;copy_q<=0;read_pending<=0;
   for(s=0;s<2;s=s+1)begin base[s]<=0;total[s]<=0;committed[s]<=0;end
   for(s=0;s<4;s=s+1)begin copy_row[s]<=0;pending_row[s]<=0;end
  end else begin
   if(reserve_v)begin base[reserve_bank]<={2'b00,reserve_base};total[reserve_bank]<=reserve_total;committed[reserve_bank]<=0;end
   if(fill_start)begin filling<=1;fill_bank<=fill_start_bank;ordinal<=0;end
   if(filling&&!s_stop)begin
    if(ordinal+8>=total[fill_bank])begin filling<=0;committed[fill_bank]<=total[fill_bank];end
    else begin ordinal<=ordinal+8;committed[fill_bank]<=((ordinal+12'd8)>>5)<<5;end
   end
   copy_q<=copy_on;
   if(copy_on&&!copy_q)begin
    read_pending<=0;
    for(s=0;s<4;s=s+1)begin copy_row[s]<=0;pending_row[s]<=0;end
   end else begin
    for(s=0;s<4;s=s+1)begin
     if(fifo_we[s])read_pending[s]<=0;
     if(mem_read[s])begin read_pending[s]<=1;pending_row[s]<=copy_row[s][5:0];copy_row[s]<=copy_row[s]+1'b1;end
    end
   end
  end
 end
 reg [2:0] credit;integer mc;
 wire [3:0] ne=~fifo_empty;
 wire [1:0] sel=ne[0]?2'd0:ne[1]?2'd1:ne[2]?2'd2:2'd3;
 wire send=(|ne)&&credit!=0&&!h_stop&&hrst;
 assign g_v=send;
 assign g_d=fifo_head[sel][285:0];
 assign fifo_re=send?(4'b1<<sel):4'b0;
 always @(posedge hbm_clk or negedge hrst)begin
  if(!hrst)credit<=(MUT==2)?3'(CRED+1):3'(CRED);
  else credit<=credit-3'(send)+3'(g_credit&&!(MUT==1&&G==1&&mc>=9));
 end
 always @(posedge hbm_clk or negedge hrst)if(!hrst)mc<=0;else if(G==1&&MUT==1&&g_v)mc<=mc+1;
endmodule

// the two hard-core masters of the split (d44v part 51): same pins, G fixed
module ot_wbq_root_g0 #(parameter integer CRED=4, parameter integer MUT=0)(
 input wire hbm_clk,fifo_clk,stream_rst_n,hbm_rst_n,
 input wire [1:0] root_id,
 input wire reserve_v,reserve_bank,input wire [11:0] reserve_total,input wire [29:0] reserve_base,
 input wire fill_start,fill_start_bank,
 input wire [255:0] wd0,wd1,wd2,wd3,input wire [3:0] wd_v,
 input wire copy_on,copy_bank,s_stop,h_stop,
 input wire g_credit,
 output wire root_ready,
 output wire g_v,output wire [285:0] g_d
);
 ot_wbq_root_grp #(.G(0),.CRED(CRED),.MUT(MUT)) u_grp(.*);
endmodule
module ot_wbq_root_g1 #(parameter integer CRED=4, parameter integer MUT=0)(
 input wire hbm_clk,fifo_clk,stream_rst_n,hbm_rst_n,
 input wire [1:0] root_id,
 input wire reserve_v,reserve_bank,input wire [11:0] reserve_total,input wire [29:0] reserve_base,
 input wire fill_start,fill_start_bank,
 input wire [255:0] wd0,wd1,wd2,wd3,input wire [3:0] wd_v,
 input wire copy_on,copy_bank,s_stop,h_stop,
 input wire g_credit,
 output wire root_ready,
 output wire g_v,output wire [285:0] g_d
);
 ot_wbq_root_grp #(.G(1),.CRED(CRED),.MUT(MUT)) u_grp(.*);
endmodule

// composition of the two groups = the plan glue of each ot_wbq_root slot (u_rK = ot_wbq_root_g2: u_g0 + u_g1), the pin list of
// ot_wbq_root ( root_ready from group 0, group 1
// computes the same synchronizer from the same inputs)
module ot_wbq_root_g2 #(parameter integer CRED=4, parameter integer MUT=0)(
 input wire hbm_clk,fifo_clk,stream_rst_n,hbm_rst_n,
 input wire [1:0] root_id,
 input wire reserve_v,reserve_bank,input wire [11:0] reserve_total,input wire [29:0] reserve_base,
 input wire fill_start,fill_start_bank,
 input wire [255:0] wd0,wd1,wd2,wd3,wd4,wd5,wd6,wd7,input wire [7:0] wd_v,
 input wire copy_on,copy_bank,s_stop,h_stop,
 input wire [1:0] g_credit,
 output wire root_ready,
 output wire [1:0] g_v,output wire [571:0] g_d
);
 wire rr1;
 ot_wbq_root_g0 #(.CRED(CRED),.MUT(MUT)) u_g0(.hbm_clk(hbm_clk),.fifo_clk(fifo_clk),.stream_rst_n(stream_rst_n),.hbm_rst_n(hbm_rst_n),
  .root_id(root_id),.reserve_v(reserve_v),.reserve_bank(reserve_bank),.reserve_total(reserve_total),.reserve_base(reserve_base),
  .fill_start(fill_start),.fill_start_bank(fill_start_bank),.wd0(wd0),.wd1(wd1),.wd2(wd2),.wd3(wd3),.wd_v(wd_v[3:0]),
  .copy_on(copy_on),.copy_bank(copy_bank),.s_stop(s_stop),.h_stop(h_stop),.g_credit(g_credit[0]),
  .root_ready(root_ready),.g_v(g_v[0]),.g_d(g_d[285:0]));
 ot_wbq_root_g1 #(.CRED(CRED),.MUT(MUT)) u_g1(.hbm_clk(hbm_clk),.fifo_clk(fifo_clk),.stream_rst_n(stream_rst_n),.hbm_rst_n(hbm_rst_n),
  .root_id(root_id),.reserve_v(reserve_v),.reserve_bank(reserve_bank),.reserve_total(reserve_total),.reserve_base(reserve_base),
  .fill_start(fill_start),.fill_start_bank(fill_start_bank),.wd0(wd4),.wd1(wd5),.wd2(wd6),.wd3(wd7),.wd_v(wd_v[7:4]),
  .copy_on(copy_on),.copy_bank(copy_bank),.s_stop(s_stop),.h_stop(h_stop),.g_credit(g_credit[1]),
  .root_ready(rr1),.g_v(g_v[1]),.g_d(g_d[571:286]));
endmodule

// HREG=3 per-PC K store: grant at t, in_data at t+1, write edge at the end of t+1. 2 entries, written and read through per-slice pointer flops.
// room(t) = (held(t) + inflight(t) <= 1); held and inflight count only flops, so a grant never needs out_r in its cone.
module ot_wbq_kstore #(parameter integer WIDTH=286,parameter integer KMUT=0,parameter integer ASPLIT=0)(
 input wire clk,rst_n,grant,output wire room,
 input wire [WIDTH-1:0] in_data,output wire out_v,input wire out_r,output wire [WIDTH-1:0] out_data);
 reg inflight;reg [1:0] held;reg room_r;reg wp,rp;reg v_r;
 wire push=inflight;wire pop=v_r&&out_r;
 wire [1:0] held_n=held+2'(push)-2'(pop);
 wire wp_n=wp^push;wire rp_n=rp^pop;
 assign room=room_r;assign out_v=v_r;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin inflight<=0;held<=0;room_r<=1;wp<=0;rp<=0;v_r<=0;end
  else begin
   inflight<=grant;held<=held_n;wp<=wp_n;rp<=rp_n;v_r<=held_n!=0;
   room_r<=(KMUT==1)?(held_n<=2'd1):(held_n+2'(grant)<=2'd1);
  end
 end
 genvar s;
 // ASPLIT=1 (HREG>=4): the address bits (W-256..) get their own slice and pointer copies; the data bits of the old slice 5 keep theirs.
 generate for(s=0;s<(ASPLIT!=0?7:6);s=s+1)begin:g_s
  localparam integer LO=(ASPLIT!=0&&s==6)?256:48*s,W=(ASPLIT!=0)?((s==6)?WIDTH-256:(s==5)?16:48):((s==5)?WIDTH-240:48);
  (* keep = "true" *) reg [1:0] we_c;(* keep = "true" *) reg [1:0] rd_c;
  reg [W-1:0] e0,e1;
  always @(posedge clk or negedge rst_n)begin
   if(!rst_n)begin we_c<=0;rd_c<=2'b01;end
   else begin we_c<=grant?(wp_n?2'b10:2'b01):2'b00;rd_c<=(KMUT==6&&s==6)?(rp?2'b10:2'b01):(rp_n?2'b10:2'b01);end
  end
  always @(posedge clk)begin if(we_c[0])e0<=in_data[LO+:W];if(we_c[1])e1<=in_data[LO+:W];end
  assign out_data[LO+:W]=({W{rd_c[0]}}&e0)|({W{rd_c[1]}}&e1);
 end endgenerate
endmodule

// HREG (sw only, default 0 = the form above unchanged). HREG=1 is a cycle-exact restructure of the K-port cone (HBM-GAPS-3, 11-05):
//  - each group keeps its queue head and the head's PC (one-hot) in flops, loaded with the exact next state qm'[qr'] (write-into-empty,
//    pop, write behind a pop), so the pick starts from flops, not from qr -> qm read -> sector_pc;
//  - pick, held request and select are one-hot per PC; the pick is registered (computed from the next-state heads, so it is the pick of
//    the current heads on every edge); the 16 x 8:1 x 286 K switch is an AND-OR of head flops selected by flops (k data is not gated by
//    k_v, the pin skid only captures on push);
//  - the ack popcount is a balanced tree, and the ack bound is checked against a remaining-count flop (meta_q - ack_count) instead of an
//    add-then-compare. Same pins, same edge for every K write, ack and fault.
// HREG=2 = HREG=1 plus (still cycle-exact): the fault / meta_active gates are registered copies (replicated per PC), loaded with
// their next state; the ack count comes as two registered half popcounts and is checked with one 7-bit difference (g_f2).
// HREG=3 (HBM-HARD-1 11-07, opt-in; PIN CYCLES +2 g_d/g_v -> w_k_*, +1 w_k_wr_done -> wa/done; K handshake contract at the pins unchanged; NOT edge-identical):
//  K data runs one edge behind K control, and control sees a new word one edge after it is stored.
//  Control: per-PC grant = pick_r gated by flops only (fault gate, outstanding, a room flop), so a grant always completes: no held request, no k_rdy in
//  the pick, pop comes from a few local gates. Per-entry PC flops in the group queue, so no g_d -> pick path and no read of the 286-bit store.
//  Data: head_d(t+1) = store(t)[qr(t)], reloaded every edge from one-hot read pointer copies, so pop does not fan out to 286 load enables; sel_q(t+1) =
//  grant(t), replicated per slice, selects the K switch at t+1; its output is written into a 2-entry per-PC store through per-slice write enables and
//  read through per-slice read pointers, so out_r does not fan out either. Ack bound/equal results are registered before they gate kg/sa copies.
//  Measured problem (vAR census, 4710 TT ends): req_valid -> sel -> 286-bit fanout across the strip -> out_data/tail_data 3104 ends, -300.6;
//  pick_r -> head_r -158.9; g_d -> pick_r -147.5; as0 -> kg_c -112.1; g_v -> qm -43.7.
//  Rate: at most 2 grants per 3 edges per PC with K always ready (the old skid: 1 per edge). The stream fill rate is 8 sectors per edge over 16 PCs.
// HREG=4 (HBM-HARD-2-WSW 11-07, opt-in; PIN CYCLES +1 root_ready, nothing else moves: every K write, grant, credit edge as HREG=3):
//  vH3b measured: 37 of 39 TT ends root_ready -> epoch; pop -> qn adder -> pick_r -0.2; slice 5 mixed 16 data bits (W face) and 30 addr bits (N face) under one pointer copy, 308 um.
//  root_ready gets one stage; hvn drops the 3-bit add; slice 5 is split so addr and data pointers/selects sit at their own face, in the K store, K switch and group store.
//  KMUT 5 = hvn ignores pop, 6 = addr slice read pointer one edge late, 7 = addr sel_q of PC 5 one edge late, 8 = root_ready never seen.
// KMUT (bench only, HREG=3): 1 = room ignores the in-flight word (store overflow), 2 = sel_q slice 2 of PC 5 takes the grant one edge late,
//  3 = head_d read pointer copy slice 1 stays one edge late, 4 = control sees the word on the edge it is stored (stale entry PC).
module ot_wbq_sw #(parameter integer KMUT=0, parameter integer WOPEN=0, parameter integer CRED=4, parameter [29:0] STACK_SECTORS=30'd703125000, parameter integer HREG=0, parameter integer GIN=0, parameter integer SEL16=0, parameter integer RSYNC=0, parameter integer SCOPY=0, parameter integer MREG=0, parameter integer DCHK=0)(
 input wire stream_clk,stream_rst_n,hbm_clk,hbm_rst_n,
 input wire [1:0] stk,input wire quad,
 input wire wb_reserve_v,wb_reserve_bank,wb_fill_bank,
 input wire [15:0] wb_reserve_epoch,wb_fill_epoch,
 input wire [11:0] wb_reserve_sectors,input wire [31:0] wb_reserve_base,
 input wire wb_fill_start,
 input wire [263:0] wd_c,                // per sector {valid, sector[31:0]}
 output reg wb_ready,output reg [11:0] wa,
 output reg wbw_v,output reg [29:0] wbw_base,output reg [11:0] wbw_total,
 output wire [15:0] w_k_v,input wire [15:0] w_k_rdy,output wire [479:0] w_k_addr,output wire [4095:0] w_k_wdata,
 input wire [15:0] w_k_wr_done,
 output reg fault,
 // seam to the roots
 input wire [3:0] root_ready,
 input wire [7:0] g_v,input wire [2287:0] g_d,
 output wire [7:0] g_credit,
 output reg [7:0] root_id,
 output wire copy_on,copy_sel,s_stop,h_stop
);
 function automatic [29:0] fold(input [28:0] o,input q);
  fold={o[28:6],q^o[10]^o[15],o[5:0]};
 endfunction
 function automatic [4:0] sector_pc(input [29:0] sector);
  sector_pc={1'b0,sector[5:2]^sector[9:6]^sector[14:11]};
 endfunction
 always @(posedge stream_clk)root_id<=8'b11_10_01_00;
 // ---- stream pins, as ot_hbm_svc_wb_kport_q
 reg rv_q,rb_q,fb_q,fs_q;reg [15:0] re_q,fe_q;reg [11:0] rt_q;reg [31:0] rbase_q;reg [263:0] wc_q;reg [1:0] stk_q;reg q_s;
 always @(posedge stream_clk)begin
  rb_q<=wb_reserve_bank;fb_q<=wb_fill_bank;re_q<=wb_reserve_epoch;fe_q<=wb_fill_epoch;rt_q<=wb_reserve_sectors;
  rbase_q<=wb_reserve_base;wc_q<=wd_c;stk_q<=stk;q_s<=quad;
 end
 // RSYNC (HBM-HARD-3 11-07, default 0 = unchanged): the stream-side blocks that took the raw stream_rst_n port take a
 // synchronised copy (async assert, release 2 stream_clk edges later, as u_krst does for hbm_rst_n). vH4/vH5 placed: one
 // flop on the raw port net (wspan[1][9]) was pulled to the reset pin, 100 um from its 47 siblings: the -81 ps TT loop.
 wire srn;
 generate if(RSYNC!=0)begin:g_srn ot_reset_sync u_srn(.clk(stream_clk),.async_rst_n(stream_rst_n),.sync_rst_n(srn));end
 else begin:g_srn0 assign srn=stream_rst_n;end endgenerate
 always @(posedge stream_clk or negedge srn)
  if(!srn)begin rv_q<=0;fs_q<=0;end else begin rv_q<=wb_reserve_v;fs_q<=wb_fill_start;end
 reg [263:0] wc_l;reg wd_stk_bad;integer t;
 always @*begin
  wc_l=wc_q;wd_stk_bad=0;
  for(t=0;t<8;t=t+1)begin
   if(wc_q[33*t+32]&&wc_q[33*t+30+:2]!=stk_q)wd_stk_bad=1;
   wc_l[33*t+30+:2]=2'b00;
  end
 end
 wire rbase_stk_bad=rv_q&&rbase_q[31:30]!=stk_q;
 // ---- block control, as ot_hbm_svc_wb_cutthrough_cdc without the lanes
 localparam [32:0] SPACE_END=33'h020000000;
 wire reset_both=stream_rst_n&&hbm_rst_n;
 wire srst,hrst;wire roots_ready;
 // HREG>=4: PIN CYCLE +1 on root_ready. root_ready is the root's reset status; it only rises after reset, long before the first reserve. Vs vH3b: 37 of 39 TT ends, -28 ps, 200 um of wire.
 generate if(HREG>=4)begin:g_rr
  reg rr_q;always @(posedge stream_clk or negedge srst)if(!srst)rr_q<=1'b0;else rr_q<=(KMUT==8)?1'b0:&root_ready;
  assign roots_ready=rr_q;
 end else begin:g_rr0
  assign roots_ready=&root_ready;
 end endgenerate
 // HBM-CORES-B 11-09 H11 SCOPY (default 0 = unchanged): wsw ties stream_clk to hbm_clk, so synthesis merged this synchroniser
 // into the kept hrst_d_pipe and every stream-side async reset hung on hrst_d (H10 routed: hrst_d -> 32x BUFx2 fanout tree ->
 // epoch[*] RESETN, the second worst TT class).  SCOPY=1: the same regional kept copies as u_hbm_reset (32, 2-stage tree).
 // Every copy equals srst on every edge: same clk / async reset / D chain, same release cycle.  PIN CYCLES 0.
 generate if(SCOPY!=0)begin:g_scopy
  ot_reset_sync #(.OUTPUT_COPIES(32),.TREE(1)) u_stream_reset(.clk(stream_clk),.async_rst_n(reset_both),.sync_rst_n(srst));
 end else begin:g_scopy0
  ot_reset_sync u_stream_reset(.clk(stream_clk),.async_rst_n(reset_both),.sync_rst_n(srst));
 end endgenerate
 // HBM-CORES-B 11-09 H10 (H9 routed TT -47.22/79: worst = hrst recovery, one synchroniser flop -> 12 buffers, BUFx2 fanout
 // stages at 143-160 ps slew -> ~3400 async resets over 580 um). Regional reset copies: 32 KEPT identical copies (2-stage
 // tree, same clk / async reset / D chain as reset_pipe), loads spread over them in synthesis by ot_rst_copies
 // (OT_RST_COPIES_MAX). Every copy equals hrst on every edge: same function, same reset release cycle. PIN CYCLES 0.
 ot_reset_sync #(.OUTPUT_COPIES(32),.TREE(1)) u_hbm_reset(.clk(hbm_clk),.async_rst_n(reset_both),.sync_rst_n(hrst));
 // HBM-HARD-5 11-08 (H6 routed TT -77.80/33, every path from u_hbm_reset.reset_pipe[1]: hrst is the reset of ~3400 flops over
 // 580 um AND a data term of hbm_fault / fault_g): the data terms read their own 2-stage copy of the same synchroniser
 // (same clk, same async reset, same D), so they equal hrst on every edge and the reset tree no longer sits in the data path.
 (* keep = "true", async_reg = "true" *) reg [1:0] hrst_d_pipe;
 always @(posedge hbm_clk or negedge reset_both) if(!reset_both) hrst_d_pipe<=2'b00; else hrst_d_pipe<={hrst_d_pipe[0],1'b1};
 wire hrst_d=hrst_d_pipe[1];
 reg [1:0] allocated,started,staged;reg [15:0] epoch[0:1];reg [31:0] base[0:1];reg [11:0] total[0:1];reg [11:0] committed[0:1];
 reg filling,fill_bank,copy_active,copy_bank;reg [11:0] ordinal;
 reg stream_sticky,hbm_sticky;(* async_reg = "true" *) reg hf1,hf2,sf1,sf2;
 wire [28:0] meta_data,ack_data;wire meta_full,meta_empty,ack_full,ack_empty;wire meta_we,meta_re,ack_we,ack_re;
 reg meta_active,ack_pending;reg [28:0] meta_q;reg [11:0] ack_count;
 reg [15:0] req_valid;reg [6:0] outstanding[0:15];reg [2:0] req_g[0:15];
 reg [15:0] pick_v;reg [2:0] pick_g[0:15];reg [7:0] pop;reg [2:0] selected_g[0:15];
 integer pc,l,acks;wire hbm_fault=hbm_sticky||sf2||!hrst_d;
 // HREG>=2 (g_f2): registered, replicated copies of the fault / meta gates, exact on every edge while hrst is high. While hrst is low
 // every flop they gate is held in reset, so the !hrst term of hbm_fault is not needed there (h_stop keeps hbm_fault).
 wire fg_w;wire [15:0] mah_w,kg_w;wire ma0_w;wire [3:0] as0_w,as1_w;
 // HBM-HARD-6 11-08 H8 (H7 routed TT -22.99/27, 26 ends launch at hrst_d (100,338) -> meta_re at u_meta (y~70) -> g_f2 copies
 // (y~430)): reset is no longer a data term of fault_g. Exact on every edge: hrst_d==hrst (same synchroniser), and while hrst is
 // low the u_meta read side is in reset (empty=1, so meta_re=0) and ack_pending is in reset (so ack_we=0); h_stop keeps hbm_fault.
 wire fault_g=(HREG>=2)?fg_w:hbm_fault;
 wire blk_fault=stream_sticky||hf2;wire [1:0] owned=allocated;
 assign s_stop=blk_fault;assign h_stop=hbm_fault;assign copy_on=copy_active;assign copy_sel=copy_bank;
 wire [31:0] reserve_base={2'b00,rbase_q[29:0]};
 wire [32:0] reserve_end={3'b0,reserve_base[29:0]}+rt_q;
 wire reserve_ready=srst&&roots_ready&&!allocated[rb_q]&&!blk_fault&&rt_q!=0&&rt_q<=2048&&reserve_base[31:30]==2'd0&&reserve_end<=SPACE_END;
 wire [1:0] copy_eligible={staged[1]&&committed[1]!=0,staged[0]&&committed[0]!=0};
 wire start_copy=srst&&roots_ready&&!copy_active&&(|copy_eligible)&&!meta_full&&!blk_fault;
 wire choose_bank=!copy_eligible[0];
 assign meta_we=start_copy;
 ot_hbm_accel_cdc_fifo #(.W(29),.AW(2)) u_meta(.wclk(stream_clk),.wrst_n(srst),.we(meta_we),.wdata({choose_bank,epoch[choose_bank],total[choose_bank]}),.full(meta_full),.rd_freed(),
  .rclk(hbm_clk),.rrst_n(hrst),.re(meta_fre),.rdata(meta_fdata),.empty(meta_empty));
 // HBM-CORES-B 11-09 H11 MREG (default 0 = unchanged): H10 routed TT -157.61, worst = u_meta.rbin -> empty/rdata -> meta_re ->
 // ~600 ps of repeated wire -> ack_rem / meta_q (the read side of u_meta sits at the far end of the tile from the ack logic).
 // MREG=1: one staging register (st_v / st_d) between u_meta and its consumer.  u_meta pops into the stage when the stage is
 // empty; the consumer takes the stage when !meta_active.  The copy job header reaches meta_active ONE hbm_clk edge later
 // (internal latency +1 cycle on the stream->hbm copy handshake; one header per copy job).  Same order, same contents, same
 // fault gating (both moves are gated by !fault_g; the stage is reset by hrst like u_meta's read side).  Proved by bench.
 wire meta_fre;wire [28:0] meta_fdata;wire meta_st_v;
 generate if(MREG!=0)begin:g_mreg
  reg st_v;reg [28:0] st_d;
  assign meta_fre=!st_v&&!meta_empty&&!fault_g;
  always @(posedge hbm_clk or negedge hrst)
   if(!hrst)begin st_v<=1'b0;st_d<=29'b0;end
   else if(meta_fre)begin st_v<=1'b1;st_d<=meta_fdata;end
   else if(meta_re)st_v<=1'b0;
  assign meta_st_v=st_v;assign meta_data=st_d;
 end else begin:g_mreg0
  assign meta_fre=meta_re;assign meta_st_v=!meta_empty;assign meta_data=meta_fdata;
 end endgenerate
 assign meta_re=!meta_active&&meta_st_v&&!fault_g;
 assign ack_we=ack_pending&&!ack_full&&!fault_g;
 assign ack_re=srst&&!ack_empty&&!blk_fault;
 ot_hbm_accel_cdc_fifo_fq #(.W(29),.AW(2)) u_ack(.wclk(hbm_clk),.wrst_n(hrst),.we(ack_we),.wdata(meta_q),.full(ack_full),.rd_freed(),
  .rclk(stream_clk),.rrst_n(srst),.re(ack_re),.rdata(ack_data),.empty(ack_empty));
 // HBM-OPEN-B 11-08 H9 (H8+ECO routed TT -7.19/1 at stream_sticky: fill_bank -> base[] mux -> 32-bit add -> compare): the two per-bank
 // expected addresses are compared before the fill_bank select, so the bank mux is a late 2:1 on one bit. Same function, combinational.
 wire [7:0] wc_bad0,wc_bad1;genvar gws;
 generate for(gws=0;gws<8;gws=gws+1)begin:g_wc_cmp
  assign wc_bad0[gws]=wc_l[33*gws+:32]!=(base[0]+ordinal+gws);
  assign wc_bad1[gws]=wc_l[33*gws+:32]!=(base[1]+ordinal+gws);
 end endgenerate
 reg fill_done,done_v,done_bank;reg [15:0] done_epoch;reg [11:0] done_sectors;
 integer s;
 always @(posedge stream_clk or negedge srst)begin
  if(!srst)begin
   allocated<=0;started<=0;staged<=0;filling<=0;fill_bank<=0;ordinal<=0;copy_active<=0;copy_bank<=0;
   stream_sticky<=0;hf1<=0;hf2<=0;fill_done<=0;done_v<=0;done_bank<=0;done_epoch<=0;done_sectors<=0;
   for(s=0;s<2;s=s+1)begin epoch[s]<=0;base[s]<=0;total[s]<=0;committed[s]<=0;end
  end else begin
   hf1<=hbm_sticky;hf2<=hf1;fill_done<=0;done_v<=0;
   if(rv_q)begin
    if(!reserve_ready)stream_sticky<=1;
    else begin allocated[rb_q]<=1;started[rb_q]<=0;staged[rb_q]<=0;epoch[rb_q]<=re_q;base[rb_q]<=reserve_base;total[rb_q]<=rt_q;committed[rb_q]<=0;end
   end
   if(fs_q)begin
    if(!roots_ready||filling||!allocated[fb_q]||started[fb_q]||epoch[fb_q]!=fe_q)stream_sticky<=1;
    else begin filling<=1;fill_bank<=fb_q;ordinal<=0;started[fb_q]<=1;staged[fb_q]<=1;end
   end
   if(filling&&!blk_fault)begin
    for(s=0;s<8;s=s+1)begin
     if(ordinal+s<total[fill_bank])begin
      if(!wc_l[33*s+32]||(fill_bank?wc_bad1[s]:wc_bad0[s]))stream_sticky<=1;
     end else if(wc_l[33*s+32])stream_sticky<=1;
    end
    if(ordinal+8>=total[fill_bank])begin filling<=0;committed[fill_bank]<=total[fill_bank];fill_done<=1;end
    else begin ordinal<=ordinal+8;committed[fill_bank]<=((ordinal+12'd8)>>5)<<5;end
   end else if(!blk_fault&&|{wc_l[263],wc_l[230],wc_l[197],wc_l[164],wc_l[131],wc_l[98],wc_l[65],wc_l[32]})stream_sticky<=1;
   if(start_copy)begin copy_active<=1;copy_bank<=choose_bank;staged[choose_bank]<=0;end
   if(ack_re)begin
    if(!copy_active||ack_data[28]!=copy_bank||ack_data[27:12]!=epoch[copy_bank]||ack_data[11:0]!=total[copy_bank])stream_sticky<=1;
    else begin allocated[copy_bank]<=0;copy_active<=0;done_v<=1;done_bank<=copy_bank;done_epoch<=epoch[copy_bank];done_sectors<=ack_data[11:0];end
   end
  end
 end
 // ---- group queues (root sends only with a credit, so never full)
 reg [1:0] qw[0:7],qr[0:7];reg [2:0] qn[0:7];
 wire [7:0] head_v;wire [285:0] head[0:7];wire [4:0] head_pc[0:7];
 // *_u: the K-port signals in use (HREG=0: the always @* below; HREG=1: g_k1)
 wire [7:0] pop_u;wire [15:0] kv_u,an_u;wire [479:0] ka_u;wire [4095:0] kd_u;
 wire [8*286-1:0] hd_all;wire [8*16-1:0] hpc_all;   // HREG=1: head flops and head PC one-hot per group
 wire [8*16-1:0] hpcn_all;wire [7:0] hvn;           // HREG=1: their next state (head PC one-hot, head valid), for the registered pick
 function automatic [15:0] pc_oh(input [29:0] sector);
  pc_oh=16'd1<<sector_pc(sector);
 endfunction
 assign g_credit=pop_u;
 // GIN=1 (HBM-GAPS-5-WBQ 11-05, opt-in; default 0 = unchanged): one register stage on the seam data inputs g_v / g_d before the
 // group queues (PIN CYCLES +1 hbm_clk edge on g_v/g_d). Credit flow is unchanged: the root sends only on a held credit and the
 // credit (g_credit = pop) returns on pop, so at most CRED words are in the stage + queue together, as before.
 wire [7:0] g_vq;wire [2287:0] g_dq;
 generate if(GIN!=0)begin:g_gin
  reg [7:0] gv_r;reg [2287:0] gd_r;
  always @(posedge hbm_clk or negedge hrst)if(!hrst)gv_r<=8'b0;else gv_r<=g_v;
  always @(posedge hbm_clk)gd_r<=g_d;
  assign g_vq=gv_r;assign g_dq=gd_r;
 end else begin:g_gin0
  assign g_vq=g_v;assign g_dq=g_d;
 end endgenerate
 genvar g;
 generate for(g=0;g<8;g=g+1)begin:g_q
  reg [285:0] qm[0:CRED-1];
  assign head_v[g]=qn[g]!=0;assign head[g]=qm[qr[g]];assign head_pc[g]=sector_pc(head[g][285:256]);
  if(HREG<3)begin:g_qmw always @(posedge hbm_clk)if(g_vq[g])qm[qw[g]]<=g_dq[286*g+:286];end
  reg gv_c3;wire gv_ctl=(HREG>=3)?((KMUT==4)?g_vq[g]:gv_c3):g_vq[g];
  always @(posedge hbm_clk or negedge hrst)if(!hrst)gv_c3<=1'b0;else gv_c3<=g_vq[g];
  always @(posedge hbm_clk or negedge hrst)begin
   if(!hrst)begin qw[g]<=0;qr[g]<=0;qn[g]<=0;end
   else begin
    if(g_vq[g])qw[g]<=qw[g]+1'b1;
    if(pop_u[g])qr[g]<=qr[g]+1'b1;
    qn[g]<=qn[g]+3'(gv_ctl)-3'(pop_u[g]);
   end
  end
  if(HREG>=3)begin:g_hr3
   wire [285:0] gd=g_dq[286*g+:286];
   reg [3:0] qpc[0:3];reg [15:0] hpc_r;
   wire [1:0] qr_n=qr[g]+2'(pop_u[g]);wire [1:0] qw_n=qw[g]+2'(g_vq[g]);
   wire [3:0] pc_w=gd[261:258]^gd[265:262]^gd[270:267];
   always @(posedge hbm_clk)if(g_vq[g])qpc[qw[g]]<=pc_w;
   wire [15:0] hpc_n=16'd1<<qpc[qr_n];
   wire [2:0] qn_n=qn[g]+3'(gv_ctl)-3'(pop_u[g]);
   always @(posedge hbm_clk)hpc_r<=hpc_n;
   // HREG>=4: same value as qn_n!=0 (a pop implies qn>=1), no 3-bit add in the pop -> pick cone (vH3b -0.2 end, 91 ends under +120)
   wire hv_f=(KMUT==5)?(gv_ctl||(qn[g]!=0)):(gv_ctl||(pop_u[g]?(qn[g]>=3'd2):(qn[g]!=0)));
   assign hpc_all[16*g+:16]=hpc_r;assign hpcn_all[16*g+:16]=hpc_n;assign hvn[g]=(HREG>=4)?hv_f:(qn_n!=0);
   // store(t) holds every write up to t-1, so head_d(t+1)=store(t)[qr(t)] needs no bypass and no load enable
   genvar ds;
   for(ds=0;ds<((HREG>=4)?7:6);ds=ds+1)begin:g_d
    localparam integer LO=(HREG>=4&&ds==6)?256:48*ds,W=(HREG>=4)?((ds==6)?30:(ds==5)?16:48):((ds==5)?286-240:48);
    (* keep = "true" *) reg [3:0] rd_c;(* keep = "true" *) reg [3:0] wp_c;
    reg [W-1:0] m0,m1,m2,m3;reg [W-1:0] head_d;
    always @(posedge hbm_clk or negedge hrst)begin
     if(!hrst)begin rd_c<=4'b0001;wp_c<=4'b0001;end
     else begin rd_c<=(KMUT==3&&ds==1)?(4'd1<<qr[g]):(4'd1<<qr_n);wp_c<=4'd1<<qw_n;end
    end
    always @(posedge hbm_clk)begin
     if(g_vq[g]&&wp_c[0])m0<=gd[LO+:W];
     if(g_vq[g]&&wp_c[1])m1<=gd[LO+:W];
     if(g_vq[g]&&wp_c[2])m2<=gd[LO+:W];
     if(g_vq[g]&&wp_c[3])m3<=gd[LO+:W];
     head_d<=({W{rd_c[0]}}&m0)|({W{rd_c[1]}}&m1)|({W{rd_c[2]}}&m2)|({W{rd_c[3]}}&m3);
    end
    assign hd_all[286*g+LO+:W]=head_d;
   end
  end else if(HREG!=0)begin:g_hr
   // head_r = qm[qr] whenever qn!=0: next state is qm'[qr'] (pop -> entry qr+1, or the incoming word if it lands there; no pop -> the
   // incoming word if it lands on qr, i.e. write into empty; else hold)
   reg [285:0] head_r;reg [15:0] hpc_r;
   wire [285:0] gd=g_dq[286*g+:286];
   wire [1:0] qr1=qr[g]+2'd1;
   wire [285:0] nx;wire [3:0] wr0,wr1;   // per 72-bit slice (HREG>=2: own pointer copies; else one decode)
   if(HREG>=2)begin:g_p2
    // kept per-slice copies of onehot(qr+1), qw==qr, qw==qr+1, loaded with their next state (all reset with qr/qw = 0)
    wire [1:0] qr_n=qr[g]+2'(pop_u[g]);wire [1:0] qw_n=qw[g]+2'(g_vq[g]);wire [1:0] qr1_n=qr_n+2'd1;
    genvar sl;
    for(sl=0;sl<4;sl=sl+1)begin:g_s
     localparam integer LO=72*sl,W=(sl==3)?286-216:72;
     (* keep = "true" *) reg [3:0] rp_c;(* keep = "true" *) reg e0_c;(* keep = "true" *) reg e1_c;
     always @(posedge hbm_clk or negedge hrst)begin
      if(!hrst)begin rp_c<=4'b0010;e0_c<=1'b1;e1_c<=1'b0;end
      else begin rp_c<=4'd1<<qr1_n;e0_c<=qw_n==qr_n;e1_c<=qw_n==qr1_n;end
     end
     assign nx[LO+:W]=({W{rp_c[0]}}&qm[0][LO+:W])|({W{rp_c[1]}}&qm[1][LO+:W])|({W{rp_c[2]}}&qm[2][LO+:W])|({W{rp_c[3]}}&qm[3][LO+:W]);
     assign wr0[sl]=g_vq[g]&&e0_c;assign wr1[sl]=g_vq[g]&&e1_c;
`ifndef SYNTHESIS
     always @(posedge hbm_clk)if(hrst&&(rp_c!==4'd1<<qr1||e0_c!==(qw[g]==qr[g])||e1_c!==(qw[g]==qr1)))$display("HREG2_COPY_MISMATCH ptr t=%0t",$time);
`endif
    end
   end else begin:g_p1
    assign nx=qm[qr1];assign wr0={4{g_vq[g]&&qw[g]==qr[g]}};assign wr1={4{g_vq[g]&&qw[g]==qr1}};
   end
   wire [15:0] hpc_n=pop_u[g]?(wr1[3]?pc_oh(gd[285:256]):pc_oh(nx[285:256])):(wr0[3]?pc_oh(gd[285:256]):hpc_r);
   wire [2:0] qn_n=qn[g]+3'(g_vq[g])-3'(pop_u[g]);
   genvar hs;
   for(hs=0;hs<4;hs=hs+1)begin:g_hs
    localparam integer LO=72*hs,W=(hs==3)?286-216:72;
    always @(posedge hbm_clk)if(pop_u[g])head_r[LO+:W]<=wr1[hs]?gd[LO+:W]:nx[LO+:W];else if(wr0[hs])head_r[LO+:W]<=gd[LO+:W];
   end
   always @(posedge hbm_clk)hpc_r<=hpc_n;
   assign hd_all[286*g+:286]=head_r;assign hpc_all[16*g+:16]=hpc_r;assign hpcn_all[16*g+:16]=hpc_n;assign hvn[g]=qn_n!=0;
  end else begin:g_hr0
   assign hd_all[286*g+:286]=286'b0;assign hpc_all[16*g+:16]=16'b0;assign hpcn_all[16*g+:16]=16'b0;assign hvn[g]=1'b0;
  end
 end endgenerate
 // ---- K ports, as the flat block with groups in place of lanes
 reg [15:0] k_v;reg [479:0] k_addr;reg [4095:0] k_wdata;wire [15:0] k_rdy;reg [15:0] ack_now,ack_q;integer ack_i;
 wire [15:0] k_wr_done_q;
 wire [15:0] k3_room;
 generate if(HREG>=3)begin:g_k3
  // control at t: grant from flops only. data at t+1: sel_q (per slice) selects head_d into the store, see pc_pin.
  reg [7:0] pick_r[0:15];reg [7:0] pick_n[0:15];reg [7:0] m;reg seen;
  reg [15:0] kv1,an1;reg [7:0] pop1;integer i,j;
  always @*begin
   for(i=0;i<16;i=i+1)begin
    seen=0;
    for(j=0;j<8;j=j+1)begin m[j]=hvn[j]&&hpcn_all[16*j+i];pick_n[i][j]=m[j]&&!seen;seen=seen||m[j];end
   end
  end
  always @*begin
   pop1=0;kv1=0;an1=0;
   for(i=0;i<16;i=i+1)begin
    kv1[i]=kg_w[i]&&k3_room[i]&&(|pick_r[i])&&(outstanding[i]<64||k_wr_done_q[i]);
    for(j=0;j<8;j=j+1)if(kv1[i]&&pick_r[i][j])pop1[j]=1;
    an1[i]=k_wr_done_q[i]&&(outstanding[i]!=0||kv1[i]);
   end
  end
  integer r;
  always @(posedge hbm_clk or negedge hrst)begin
   if(!hrst)begin for(r=0;r<16;r=r+1)pick_r[r]<=0;end
   else for(r=0;r<16;r=r+1)pick_r[r]<=pick_n[r];
  end
  // per-PC select, one flop set per 48-bit slice of the 286-bit word
  genvar pi,ps;
  for(pi=0;pi<16;pi=pi+1)begin:g_pc
   wire [7:0] grant={8{kv1[pi]}}&pick_r[pi];
   wire [285:0] kw;
   // SEL16 (HBM-HARD-3 11-07, default 0 = unchanged): one sel_q set per 16-bit slice, so each select flop drives
   // at most 16 AND legs (vH4 routed: 54 slew nets, all one sel_q bit through one buffer to 48 legs). Same cycle.
   for(ps=0;ps<((SEL16!=0)?18:(HREG>=4)?7:6);ps=ps+1)begin:g_s
    localparam integer LO=(SEL16!=0)?16*ps:(HREG>=4&&ps==6)?256:48*ps,
                       W=(SEL16!=0)?((ps==17)?14:16):(HREG>=4)?((ps==6)?30:(ps==5)?16:48):((ps==5)?286-240:48);
    (* keep = "true" *) reg [7:0] sel_q;
    reg [7:0] sel_q2;
    always @(posedge hbm_clk or negedge hrst)if(!hrst)begin sel_q<=0;sel_q2<=0;end else begin sel_q2<=grant;sel_q<=((KMUT==2&&pi==5&&ps==2)||(KMUT==7&&pi==5&&ps==6)||(KMUT==9&&pi==5&&ps==11))?sel_q2:grant;end
    wire [W-1:0] o=({W{sel_q[0]}}&hd_all[286*0+LO+:W])|({W{sel_q[1]}}&hd_all[286*1+LO+:W])|({W{sel_q[2]}}&hd_all[286*2+LO+:W])|({W{sel_q[3]}}&hd_all[286*3+LO+:W])
                  |({W{sel_q[4]}}&hd_all[286*4+LO+:W])|({W{sel_q[5]}}&hd_all[286*5+LO+:W])|({W{sel_q[6]}}&hd_all[286*6+LO+:W])|({W{sel_q[7]}}&hd_all[286*7+LO+:W]);
    assign kw[LO+:W]=o;
   end
   assign ka_u[30*pi+:30]=kw[285:256];assign kd_u[256*pi+:256]=kw[255:0];
  end
  assign pop_u=pop1;assign kv_u=kv1;assign an_u=an1;
 end else if(HREG!=0)begin:g_k1
  // one-hot pick (lowest group whose head is on this PC), held request one-hot, AND-OR switch from the head flops.
  // pick_r is the pick of this edge, registered: loaded with the pick of the next-state heads (hvn, hpcn_all), so
  // pick_r == pick(head_v, hpc_r) on every edge (both 0 out of reset, qn=0). The wide switch and pop start from flops.
  reg [7:0] req_oh[0:15];reg [7:0] sel[0:15];reg [7:0] pick_r[0:15];reg [7:0] pick_n[0:15];reg [7:0] m;reg seen;
  reg [15:0] kv1,an1;reg [7:0] pop1;reg [479:0] ka1;reg [4095:0] kd1;integer i,j;
  always @*begin
   for(i=0;i<16;i=i+1)begin
    seen=0;
    for(j=0;j<8;j=j+1)begin m[j]=hvn[j]&&hpcn_all[16*j+i];pick_n[i][j]=m[j]&&!seen;seen=seen||m[j];end
   end
  end
  always @*begin
   pop1=0;kv1=0;an1=0;ka1=0;kd1=0;
   for(i=0;i<16;i=i+1)begin
    sel[i]=req_valid[i]?req_oh[i]:pick_r[i];
    kv1[i]=((HREG>=2)?kg_w[i]:(meta_active&&!ack_pending&&!hbm_fault))&&(req_valid[i]||(|pick_r[i]))&&(outstanding[i]<64||k_wr_done_q[i]);
    for(j=0;j<8;j=j+1)begin
     ka1[30*i+:30]=ka1[30*i+:30]|({30{sel[i][j]}}&hd_all[286*j+256+:30]);
     kd1[256*i+:256]=kd1[256*i+:256]|({256{sel[i][j]}}&hd_all[286*j+:256]);
     if(kv1[i]&&k_rdy[i]&&sel[i][j])pop1[j]=1;
    end
    an1[i]=k_wr_done_q[i]&&(outstanding[i]!=0||(DCHK!=1&&kv1[i]&&k_rdy[i]));
   end
  end
  integer r;
  always @(posedge hbm_clk or negedge hrst)begin
   if(!hrst)begin for(r=0;r<16;r=r+1)begin req_oh[r]<=0;pick_r[r]<=0;end end
   else begin
    for(r=0;r<16;r=r+1)pick_r[r]<=pick_n[r];
    for(r=0;r<16;r=r+1)if(((HREG>=2)?mah_w[r]:(meta_active&&!hbm_fault))&&kv1[r]&&!k_rdy[r])req_oh[r]<=sel[r];
   end
  end
  assign pop_u=pop1;assign kv_u=kv1;assign an_u=an1;assign ka_u=ka1;assign kd_u=kd1;
 end else begin:g_k0
  assign pop_u=pop;assign kv_u=k_v;assign an_u=ack_now;assign ka_u=k_addr;assign kd_u=k_wdata;
 end endgenerate
 always @*begin
  pick_v=0;pop=0;k_v=0;k_addr=0;k_wdata=0;ack_now=0;
  for(pc=0;pc<16;pc=pc+1)begin
   pick_g[pc]=0;
   for(l=0;l<8;l=l+1)if(!pick_v[pc]&&head_v[l]&&head_pc[l]==pc)begin pick_v[pc]=1;pick_g[pc]=3'(l);end
   selected_g[pc]=req_valid[pc]?req_g[pc]:pick_g[pc];
   if(meta_active&&(req_valid[pc]||pick_v[pc])&&!ack_pending&&(outstanding[pc]<64||k_wr_done_q[pc])&&!hbm_fault)begin
    k_v[pc]=1;k_addr[30*pc+:30]=head[selected_g[pc]][285:256];k_wdata[256*pc+:256]=head[selected_g[pc]][255:0];
    if(k_rdy[pc])pop[selected_g[pc]]=1;
   end
   if(k_wr_done_q[pc]&&(outstanding[pc]!=0||(DCHK!=1&&k_v[pc]&&k_rdy[pc])))ack_now[pc]=1;
  end
 end
 always @(posedge hbm_clk or negedge hrst)if(!hrst)ack_q<=0;else ack_q<=(meta_active&&!hbm_fault)?an_u:16'b0;
 always @*begin acks=0;for(ack_i=0;ack_i<16;ack_i=ack_i+1)if(ack_q[ack_i])acks=acks+1;end
 // HREG=1: balanced popcount tree; ack bound against ack_rem = meta_q[11:0]-ack_count (exact while ack_count<=meta_q[11:0], which holds
 // whenever it is read: the first overshoot sets hbm_sticky, and hbm_fault then blocks this branch and meta_re until reset)
 wire [1:0] ap0=ack_q[0]+ack_q[1],ap1=ack_q[2]+ack_q[3],ap2=ack_q[4]+ack_q[5],ap3=ack_q[6]+ack_q[7],
  ap4=ack_q[8]+ack_q[9],ap5=ack_q[10]+ack_q[11],ap6=ack_q[12]+ack_q[13],ap7=ack_q[14]+ack_q[15];
 wire [2:0] aq0=ap0+ap1,aq1=ap2+ap3,aq2=ap4+ap5,aq3=ap6+ap7;
 wire [3:0] ar0=aq0+aq1,ar1=aq2+aq3;
 wire [4:0] acks_t=ar0+ar1;
 reg [11:0] ack_rem;
 wire ack_any=|ack_q;
 // HREG>=2: the ack count arrives as two registered half popcounts (as0/as1 = popcount of ack_q[7:0] / [15:8], g_f2); one 7-bit
 // difference lo - as0 - as1 gives the bound checks and the low bits, the high bits take a parallel decrement on borrow
 wire [6:0] ack_dif={2'b0,ack_rem[4:0]}-{3'b0,as0_w}-{3'b0,as1_w};
 wire [6:0] ack_hi_m1=ack_rem[11:5]-7'd1;
 wire ack_hi0=ack_rem[11:5]==7'd0;
 wire ack_any_g=(HREG>=2)?(|{as0_w,as1_w}):(HREG!=0)?ack_any:(acks!=0);
 wire ack_gt=(HREG>=2)?(ack_hi0&&ack_dif[6]):(HREG!=0)?(ack_rem[11:5]==7'd0&&acks_t>ack_rem[4:0]):(13'(ack_count)+13'(acks)>13'(meta_q[11:0]));
 wire ack_eq=(HREG>=2)?(ack_hi0&&ack_dif==7'd0):(HREG!=0)?(ack_rem[11:5]==7'd0&&acks_t==ack_rem[4:0]):(13'(ack_count)+13'(acks)==13'(meta_q[11:0]));
 reg ack_gt_q,ack_eq_q;
 wire ack_gt_s=(HREG>=3)?ack_gt_q:(ack_any_g&&ack_gt);
 wire ack_eq_s=(HREG>=3)?ack_eq_q:(ack_any_g&&ack_eq);
 wire [11:0] ack_rem_n=(HREG>=2)?{ack_dif[6]?ack_hi_m1:ack_rem[11:5],ack_dif[4:0]}:(ack_rem-12'(acks_t));
 wire [15:0] mah_g=(HREG>=2)?mah_w:{16{meta_active&&!hbm_fault}};
 wire ma0_g=(HREG>=2)?ma0_w:(meta_active&&!hbm_fault);
 integer h;
 always @(posedge hbm_clk or negedge hrst)begin
  if(!hrst)begin
   ack_gt_q<=0;ack_eq_q<=0;sf1<=0;sf2<=0;hbm_sticky<=0;meta_active<=0;meta_q<=0;ack_pending<=0;ack_count<=0;ack_rem<=0;req_valid<=0;
   for(h=0;h<16;h=h+1)begin req_g[h]<=0;outstanding[h]<=0;end
  end else begin
   sf1<=stream_sticky;sf2<=sf1;
   ack_gt_q<=ma0_g&&ack_any_g&&ack_gt;ack_eq_q<=ma0_g&&ack_any_g&&ack_eq;
   if(meta_re)begin meta_active<=1;meta_q<=meta_data;ack_count<=0;ack_rem<=meta_data[11:0];ack_pending<=0;end
   for(h=0;h<16;h=h+1)if(mah_g[h])begin
     if(kv_u[h]&&!k_rdy[h])begin req_valid[h]<=1;req_g[h]<=selected_g[h];end
     if(kv_u[h]&&k_rdy[h])req_valid[h]<=0;
     case({kv_u[h]&&k_rdy[h],k_wr_done_q[h]})
      2'b10:outstanding[h]<=outstanding[h]+1'b1;
      2'b01:if(outstanding[h]!=0)outstanding[h]<=outstanding[h]-1'b1;
      default:begin end
     endcase
     if(DCHK!=2&&k_wr_done_q[h]&&!(outstanding[h]!=0||(DCHK!=1&&kv_u[h]&&k_rdy[h])))hbm_sticky<=1;
    end
   if(ma0_g)begin
    if(ack_any_g)begin
     ack_count<=ack_count+12'(acks);ack_rem<=ack_rem_n;
    end
    if(ack_gt_s)hbm_sticky<=1;
    if(ack_eq_s)ack_pending<=1;
   end else if(|k_wr_done_q)hbm_sticky<=1;
   if(ack_we)begin ack_pending<=0;meta_active<=0;end
  end
 end
 // ---- HREG>=2: registered gates. Identities (all while hrst; all 0 in reset, as the values they copy):
 //   hbm_sticky||sf2 = fo_c||sa_c, fo_c <= hbm_sticky||setO||sf1 (setO: the non-ack sticky sets), sa_c <= setA (ack overshoot set);
 //   meta_active&&!(hbm_sticky||sf2) = ma_c&&!sa_c, ma_c <= meta_active_next&&!(hbm_sticky||setO||sf1);
 //   ... &&!ack_pending = kg_c&&!sa_c, kg_c <= ma_c next&&!ack_pending_next;
 //   as0+as1 = popcount(ack_q): as <= MA ? popcount(an half) : 0, as ack_q <= MA ? an : 0.
 // Kept copies: one central set (fo0/sa0/ma0: FIFO strobes, sticky, ack count) and one set per PC (ma/kg/sa: the K port of that PC),
 // so no single flop drives the strip.
 function automatic [3:0] pc8(input [7:0] v);
  reg [1:0] a0,a1,a2,a3;reg [2:0] b0,b1;
  begin a0=v[0]+v[1];a1=v[2]+v[3];a2=v[4]+v[5];a3=v[6]+v[7];b0=a0+a1;b1=a2+a3;pc8=b0+b1;end
 endfunction
 generate if(HREG>=2)begin:g_f2
  reg setH;integer z;
  always @*begin setH=0;for(z=0;z<16;z=z+1)if(DCHK!=2&&k_wr_done_q[z]&&!(outstanding[z]!=0||(DCHK!=1&&kv_u[z]&&k_rdy[z])))setH=1;end
  wire setO=ma0_w?setH:(|k_wr_done_q);
  wire setA=ma0_w&&ack_gt_s;
  wire fo_n=hbm_sticky||setO||sf1;
  wire ma_n=(meta_active||meta_re)&&!ack_we&&!fo_n;
  wire ap_n=!ack_we&&!meta_re&&(ack_pending||(ma0_w&&ack_eq_s));
  wire kg_n=ma_n&&!ap_n;
  (* keep = "true" *) reg fo0_c;(* keep = "true" *) reg sa0_c;(* keep = "true" *) reg ma0_c;
  genvar c;
  // HBM-CORES-B 11-09 H13 (MREG>=1 forms only; cycle-exact): H12 routed TT -20.38 / 15, all sa0_c -> g_c[*].kg_c: the ONE shared
  // ma_n/kg_n cone (ma0_w -> setO/fo_n, ap_n) ended in an AOI211x1 whose net fans out to the 16 per-PC kg_c/ma_c copies along
  // the strip (slew 174 ps, then BUFx3 fo18, OA21 fo16).  MREG>=1: each PC computes its own copy of the cone from the central
  // flops in a keep_hierarchy leaf (ot_wbq_kg_leaf), so the fanout moves to the flop outputs and each kg_c D is a local gate.
  // Same function per edge: the leaf evaluates the identical expressions (fo_n, ma_n, ap_n, kg_n, setA) on the same inputs.
  for(c=0;c<16;c=c+1)begin:g_c
   if(MREG>=1)begin:g_l
    ot_wbq_kg_leaf u_kg(.hbm_clk(hbm_clk),.hrst(hrst),.ma0_c(ma0_c),.sa0_c(sa0_c),.setH(setH),.kwd_any(|k_wr_done_q),
     .hbm_sticky(hbm_sticky),.sf1(sf1),.meta_active(meta_active),.meta_re(meta_re),.ack_we(ack_we),.ack_pending(ack_pending),
     .ack_eq_s(ack_eq_s),.ack_gt_s(ack_gt_s),.mah(mah_w[c]),.kg(kg_w[c]));
   end else begin:g_r
   (* keep = "true" *) reg ma_c;(* keep = "true" *) reg kg_c;(* keep = "true" *) reg sa_c;
   always @(posedge hbm_clk or negedge hrst)if(!hrst)begin ma_c<=0;kg_c<=0;sa_c<=0;end else begin ma_c<=ma_n;kg_c<=kg_n;sa_c<=setA;end
   assign mah_w[c]=ma_c&&!sa_c;assign kg_w[c]=kg_c&&!sa_c;
   end
  end
  reg [3:0] as0_r,as1_r;
  always @(posedge hbm_clk or negedge hrst)begin
   if(!hrst)begin fo0_c<=0;sa0_c<=0;ma0_c<=0;as0_r<=0;as1_r<=0;end
   else begin fo0_c<=fo_n;sa0_c<=setA;ma0_c<=ma_n;as0_r<=ma0_w?pc8(an_u[7:0]):4'd0;as1_r<=ma0_w?pc8(an_u[15:8]):4'd0;end
  end
  assign ma0_w=ma0_c&&!sa0_c;assign fg_w=fo0_c||sa0_c;assign as0_w=as0_r;assign as1_w=as1_r;
`ifndef SYNTHESIS
  // bench check: every copy equals the value it stands for, on every edge with hrst high
  integer cmis=0;
  always @(posedge hbm_clk)if(hrst)begin
   if(fg_w!==(hbm_sticky||sf2)||ma0_w!==(meta_active&&!hbm_fault)||mah_w!=={16{meta_active&&!hbm_fault}}||
      kg_w!=={16{meta_active&&!hbm_fault&&!ack_pending}}||(5'(as0_r)+5'(as1_r))!==5'(acks))begin
    if(cmis==0)$display("HREG2_COPY_MISMATCH t=%0t",$time);cmis=cmis+1;end
  end
`endif
 end else begin:g_f0
  assign fg_w=1'b0;assign mah_w=16'b0;assign kg_w=16'b0;assign ma0_w=1'b0;assign as0_w=4'b0;assign as1_w=4'b0;
 end endgenerate
 // ---- real window of a reservation, receipts, wb_ready, wa, window command: as ot_hbm_svc_wb_kport_q
 reg rv1,rb1,rv2,rb2;reg [28:0] ob1,oe1;reg [29:0] sb2,se2;reg rq1;
 always @(posedge stream_clk or negedge srn)
  if(!srn)begin rv1<=0;rv2<=0;end else begin rv1<=rv_q&&reserve_ready;rv2<=rv1;end
 always @(posedge stream_clk)begin
  rb1<=rb_q;ob1<=rbase_q[28:0];oe1<=rbase_q[28:0]+29'(rt_q)-29'd1;rq1<=q_s;
  rb2<=rb1;sb2<=fold(ob1,rq1);se2<=fold(oe1,rq1);
 end
 wire [30:0] span2={1'b0,se2}-{1'b0,sb2}+31'd1;
 wire span_bad=rv2&&(span2>31'd4095||{1'b0,se2}>={1'b0,STACK_SECTORS});
 reg [1:0] accepted;reg [15:0] aepoch[0:1];reg [11:0] atotal[0:1];reg [29:0] wbase[0:1];reg [11:0] wspan[0:1];reg rfault;reg fsb_q;
 wire block_ready=accepted[fb_q]&&aepoch[fb_q]==fe_q&&owned[fb_q];
 wire win_go=(WOPEN==0)?fs_q:fill_done;
 wire win_bank=(WOPEN==0)?fb_q:fsb_q;
 always @(posedge stream_clk or negedge srn)begin
  if(!srn)begin
   accepted<=0;rfault<=0;wb_ready<=0;wa<=0;wbw_v<=0;wbw_base<=0;wbw_total<=0;fault<=0;fsb_q<=0;
   aepoch[0]<=0;aepoch[1]<=0;atotal[0]<=0;atotal[1]<=0;wbase[0]<=0;wbase[1]<=0;wspan[0]<=0;wspan[1]<=0;
  end else begin
   if(rv_q)begin
    if(!reserve_ready)rfault<=1;
    else begin accepted[rb_q]<=1;aepoch[rb_q]<=re_q;atotal[rb_q]<=rt_q;end
   end
   if(rv2)begin wbase[rb2]<=sb2;wspan[rb2]<=span2[11:0];end
   if(done_v)begin
    if(!accepted[done_bank]||aepoch[done_bank]!=done_epoch||atotal[done_bank]!=done_sectors)rfault<=1;
    accepted[done_bank]<=0;
   end
   if(fs_q)fsb_q<=fb_q;
   if(rbase_stk_bad||wd_stk_bad||span_bad)rfault<=1;
   wb_ready<=block_ready;
   wa<=done_v?done_sectors:12'd0;
   wbw_v<=win_go;wbw_base<=wbase[win_bank];wbw_total<=wspan[win_bank];
   fault<=rfault||blk_fault;
  end
 end
 reg [15:0] wr_done_q;reg q_h;
 always @(posedge hbm_clk)q_h<=quad;
 always @(posedge hbm_clk or negedge hbm_rst_n)if(!hbm_rst_n)wr_done_q<=0;else wr_done_q<=w_k_wr_done;
 assign k_wr_done_q=wr_done_q;
 genvar p;
 wire [15:0] k_rdy_w;assign k_rdy=(HREG>=3)?16'hFFFF:k_rdy_w;
 generate for(p=0;p<16;p=p+1)begin:pc_pin
  // HREG>=2: the skid takes its own synchronised copy of hbm_rst_n (async assert, release 2 edges later). Same pins: in those
  // edges the skid is empty either way and in_v=0 (the core is still in reset: hrst releases no earlier than krst)
  wire krst;
  if(HREG>=2)begin:g_kr ot_reset_sync u_krst(.clk(hbm_clk),.async_rst_n(hbm_rst_n),.sync_rst_n(krst));end
  else begin:g_kr0 assign krst=hbm_rst_n;end
  if(HREG>=3)begin:g_s3
   assign k_rdy_w[p]=1'b1;
   ot_wbq_kstore #(.WIDTH(286),.KMUT(KMUT),.ASPLIT((HREG>=4)?1:0)) u_k(.clk(hbm_clk),.rst_n(krst),.grant(kv_u[p]),.room(k3_room[p]),
    .in_data({fold(ka_u[30*p+:29],q_h),kd_u[256*p+:256]}),.out_v(w_k_v[p]),.out_r(w_k_rdy[p]),
    .out_data({w_k_addr[30*p+:30],w_k_wdata[256*p+:256]}));
  end else begin:g_s0
   assign k3_room[p]=1'b0;
   ot_hbm_svc_pin_skid2 #(.WIDTH(286)) u_k(.clk(hbm_clk),.rst_n(krst),.in_v(kv_u[p]),.in_r(k_rdy_w[p]),
    .in_data({fold(ka_u[30*p+:29],q_h),kd_u[256*p+:256]}),.out_v(w_k_v[p]),.out_r(w_k_rdy[p]),
    .out_data({w_k_addr[30*p+:30],w_k_wdata[256*p+:256]}));
  end
 end endgenerate
endmodule
`default_nettype wire

// HBM-CORES-B 11-09 H12 (H11+ECO routed TT -76.82 / 119: u_ack wgray -> full compare -> 116 mem write enables, ~550 ps
// of wire): the same Gray FIFO as ot_hbm_accel_cdc_fifo, but full is a REGISTER loaded with next cycle's compare
// (gray(wbin_n) against rg_w1, which is next cycle's rg_w2). Cycle-exact: full_q == (wgray == {~rg_w2[AW:AW-1],
// rg_w2[AW-2:0]}) in every cycle (both are 0 out of reset), so ports, latency and contents are unchanged.
module ot_hbm_accel_cdc_fifo_fq #(parameter integer W = 32, parameter integer AW = 5) (
  input  wire          wclk, wrst_n, input wire we, input wire [W-1:0] wdata, output wire full,
  output wire [2:0]    rd_freed,
  input  wire          rclk, rrst_n, input wire re, output wire [W-1:0] rdata, output wire empty
);
  localparam integer D = 1 << AW;
  reg [W-1:0] mem [0:D-1];
  reg [AW:0] wbin, wgray, rbin, rgray;
  reg full_q;
  (* async_reg = "true" *) reg [AW:0] rg_w1, rg_w2;   // read pointer in the write domain
  (* async_reg = "true" *) reg [AW:0] wg_r1, wg_r2;   // write pointer in the read domain
  function automatic [AW:0] g2b(input [AW:0] g);
    for (integer i = AW; i >= 0; i = i - 1) g2b[i] = (i == AW) ? g[i] : g2b[i+1] ^ g[i];
  endfunction
  wire [AW:0] wbin_n = wbin + ((we && !full_q) ? 1'b1 : 1'b0);
  wire [AW:0] wgray_n = wbin_n ^ (wbin_n >> 1);
  wire [AW:0] rbin_n = rbin + ((re && !empty) ? 1'b1 : 1'b0);
  assign full  = full_q;
  assign empty = (rgray == wg_r2);
  assign rdata = mem[rbin[AW-1:0]];
  reg [AW:0] rsync_bin_q;
  wire [AW:0] rsync_bin = g2b(rg_w2);
  assign rd_freed = 3'(rsync_bin - rsync_bin_q);
  always @(posedge wclk or negedge wrst_n)
    if (!wrst_n) begin wbin <= 0; wgray <= 0; rg_w1 <= 0; rg_w2 <= 0; rsync_bin_q <= 0; full_q <= 1'b0; end
    else begin
      if (we && !full_q) mem[wbin[AW-1:0]] <= wdata;
      wbin <= wbin_n; wgray <= wgray_n;
      rg_w1 <= rgray; rg_w2 <= rg_w1; rsync_bin_q <= rsync_bin;
      full_q <= (wgray_n == {~rg_w1[AW:AW-1], rg_w1[AW-2:0]});
    end
  always @(posedge rclk or negedge rrst_n)
    if (!rrst_n) begin rbin <= 0; rgray <= 0; wg_r1 <= 0; wg_r2 <= 0; end
    else begin
      rbin <= rbin_n; rgray <= rbin_n ^ (rbin_n >> 1);
      wg_r1 <= wgray; wg_r2 <= wg_r1;
    end
endmodule

// HBM-CORES-B 11-09 H13: per-PC copy of the g_f2 K-gate cone + its three flops (ot_wbq_sw MREG>=1).  keep_hierarchy so
// synthesis cannot merge the 16 identical copies back into one cone (opt_merge folds identical logic, keep on wires does not stop it).
(* keep_hierarchy *)
module ot_wbq_kg_leaf(input wire hbm_clk,input wire hrst,input wire ma0_c,input wire sa0_c,input wire setH,input wire kwd_any,
 input wire hbm_sticky,input wire sf1,input wire meta_active,input wire meta_re,input wire ack_we,input wire ack_pending,
 input wire ack_eq_s,input wire ack_gt_s,output wire mah,output wire kg);
 wire ma0_w=ma0_c&&!sa0_c;
 wire setO=ma0_w?setH:kwd_any;
 wire setA=ma0_w&&ack_gt_s;
 wire fo_n=hbm_sticky||setO||sf1;
 wire ma_n=(meta_active||meta_re)&&!ack_we&&!fo_n;
 wire ap_n=!ack_we&&!meta_re&&(ack_pending||(ma0_w&&ack_eq_s));
 wire kg_n=ma_n&&!ap_n;
 reg ma_c,kg_c,sa_c;
 always @(posedge hbm_clk or negedge hrst)if(!hrst)begin ma_c<=0;kg_c<=0;sa_c<=0;end else begin ma_c<=ma_n;kg_c<=kg_n;sa_c<=setA;end
 assign mah=ma_c&&!sa_c;assign kg=kg_c&&!sa_c;
endmodule
