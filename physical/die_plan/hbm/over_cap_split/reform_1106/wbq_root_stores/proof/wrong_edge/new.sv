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
 reg copy_q;// Per-lane row/read/FIFO state lives in the store children.
 wire [7:0] fifo_empty,fifo_re;
 wire [287:0] fifo_head[0:7];
 genvar g;
 generate for(g=0;g<8;g=g+1)begin:g_lane
`ifdef OT_WBQ_ROOT_STORE_FACES
  ot_wbq_root_store_face #(.LANE(g)) u_store(
`else
  ot_wbq_root_store #(.LANE(g)) u_store(
`endif
   .fifo_clk(fifo_clk),.hbm_clk(hbm_clk),.srst(srst),.hrst(hrst),
   .root_id(root_id),.base(base[copy_bank]),.total(total[fill_bank]),.committed(committed[copy_bank]),
   .filling(filling),.fill_bank(fill_bank),.ordinal(ordinal),.copy_q(copy_q),.copy_bank(copy_bank),
   .copy_start(copy_on&&!copy_q),.s_stop(s_stop),.wd(wd[g]),.wd_v(wd_v[g]),
   .fifo_re(fifo_re[g]),.fifo_head(fifo_head[g]),.fifo_empty(fifo_empty[g]));
 end endgenerate
 integer s;
 always @(posedge fifo_clk or negedge srst)begin
  if(!srst)begin
   filling<=0;fill_bank<=0;ordinal<=0;copy_q<=0;
   for(s=0;s<2;s=s+1)begin base[s]<=0;total[s]<=0;committed[s]<=0;end
  end else begin
   if(reserve_v)begin base[reserve_bank]<={2'b00,reserve_base};total[reserve_bank]<=reserve_total;committed[reserve_bank]<=0;end
   if(fill_start)begin filling<=1;fill_bank<=fill_start_bank;ordinal<=0;end
   if(filling&&!s_stop)begin
    if(ordinal+8>=total[fill_bank])begin filling<=0;committed[fill_bank]<=total[fill_bank];end
    else begin ordinal<=ordinal+8;committed[fill_bank]<=((ordinal+12'd8)>>5)<<5;end
   end
   copy_q<=copy_on;

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

// Zero-extra-edge internal store: original lane SRAM, CDC FIFO and row state.
// Native internal seams retain existing first captures; no face flops added.
module ot_wbq_root_store #(parameter integer LANE=0)(
 input wire fifo_clk,hbm_clk,srst,hrst,
 input wire [1:0]root_id,input wire [31:0]base,
 input wire [11:0]total,committed,ordinal,
 input wire filling,fill_bank,copy_q,copy_bank,copy_start,s_stop,
 input wire [255:0]wd,input wire wd_v,fifo_re,
 output wire [287:0]fifo_head,output wire fifo_empty
);
 reg [6:0]copy_row;reg [5:0]pending_row;reg read_pending;
 wire [4:0]lane={root_id,3'(LANE)};
 wire [31:0]sector=base+{pending_row,5'b0}+lane;
 wire fifo_full;
 wire fifo_we=copy_q&&read_pending&&!fifo_full&&!s_stop;
 wire mem_read=copy_q&&(!read_pending||fifo_we)&&copy_row*32+int'(lane)<committed&&!s_stop;
 wire [255:0]mem_data;
 ot_hbm_accel_cdc_fifo #(.W(288),.AW(2)) u_fifo(
  .wclk(fifo_clk),.wrst_n(srst),.we(fifo_we),.wdata({sector,mem_data}),.full(fifo_full),.rd_freed(),
  .rclk(hbm_clk),.rrst_n(hrst),.re(fifo_re),.rdata(fifo_head),.empty(fifo_empty));
 ot_sram_1r1w_128x256_m1_r2c2 u_payload(
  .clk(fifo_clk),.r_ce_in(mem_read),.r_addr_in({copy_bank,copy_row[5:0]}),.rd_out(mem_data),
  .w_ce_in(filling&&!s_stop&&ordinal+LANE<total&&ordinal[4:3]==root_id&&wd_v),
  .w_addr_in({fill_bank,ordinal[10:5]}),.wd_in(wd
`ifdef ROOT_STORE_MUT
 ^ 256'(1)
`endif
 ),.w_mask_in({256{1'b1}}),
  .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 always @(posedge fifo_clk or negedge srst)begin
  if(!srst)begin copy_row<=0;pending_row<=0;read_pending<=0;end
  else if(copy_start)begin copy_row<=0;pending_row<=0;read_pending<=0;end
  else begin
   if(fifo_we)read_pending<=0;
   if(mem_read)begin read_pending<=1;pending_row<=copy_row[5:0];copy_row<=copy_row+1'b1;end
  end
 end
endmodule


// Existing WD input-face capture relocated from the old outer shell.
module ot_wbq_root_store_face #(parameter integer LANE=0)(
 input wire fifo_clk,hbm_clk,srst,hrst,
 input wire [1:0]root_id,input wire [31:0]base,
 input wire [11:0]total,committed,ordinal,
 input wire filling,fill_bank,copy_q,copy_bank,copy_start,s_stop,
 input wire [255:0]wd,input wire wd_v,fifo_re,
 output wire [287:0]fifo_head,output wire fifo_empty
);
wire[255:0]wd_q=wd; // MUTANT removes the existing WD capture edge
ot_wbq_root_store #(.LANE(LANE)) u_native(.fifo_clk(fifo_clk),.hbm_clk(hbm_clk),.srst(srst),.hrst(hrst),.root_id(root_id),.base(base),.total(total),.committed(committed),.ordinal(ordinal),.filling(filling),.fill_bank(fill_bank),.copy_q(copy_q),.copy_bank(copy_bank),.copy_start(copy_start),.s_stop(s_stop),.wd(wd_q),.wd_v(wd_v),.fifo_re(fifo_re),.fifo_head(fifo_head),.fifo_empty(fifo_empty));
endmodule


// GENERATED by face_shell.py (HBM-FACE): face-register shell of ot_wbq_root.  Every signal pin bit has its own
// flop at the face (+1 cycle in, +1 cycle out); clock / reset pins pass through; dropped unread input bits are
// driven 0 at the core port (never read by the core: yosys analysis, bench-verified).  Do not edit.
`default_nettype none
module ot_wbq_root_store_family (
    input wire hbm_clk,
    input wire fifo_clk,
    input wire stream_rst_n,
    input wire hbm_rst_n,
    input wire [1:0] root_id,
    input wire reserve_v,
    input wire reserve_bank,
    input wire [11:0] reserve_total,
    input wire [29:0] reserve_base,
    input wire fill_start,
    input wire fill_start_bank,
    input wire [255:0] wd0,
    input wire [255:0] wd1,
    input wire [255:0] wd2,
    input wire [255:0] wd3,
    input wire [255:0] wd4,
    input wire [255:0] wd5,
    input wire [255:0] wd6,
    input wire [255:0] wd7,
    input wire [7:0] wd_v,
    input wire copy_on,
    input wire copy_bank,
    input wire s_stop,
    input wire h_stop,
    input wire [1:0] g_credit,
    output wire root_ready,
    output wire [1:0] g_v,
    output wire [571:0] g_d
);
    wire [1:0] root_id__fq;
    (* keep *) ot_hbm_face_reg #(.W(2)) u_bin_root_id (.clk(fifo_clk), .d(root_id), .q(root_id__fq));
    wire [0:0] reserve_v__fq;
    (* keep *) ot_hbm_face_reg #(.W(1)) u_bin_reserve_v (.clk(fifo_clk), .d(reserve_v), .q(reserve_v__fq));
    wire [0:0] reserve_bank__fq;
    (* keep *) ot_hbm_face_reg #(.W(1)) u_bin_reserve_bank (.clk(fifo_clk), .d(reserve_bank), .q(reserve_bank__fq));
    wire [11:0] reserve_total__fq;
    (* keep *) ot_hbm_face_reg #(.W(12)) u_bin_reserve_total (.clk(fifo_clk), .d(reserve_total), .q(reserve_total__fq));
    wire [29:0] reserve_base__fq;
    (* keep *) ot_hbm_face_reg #(.W(30)) u_bin_reserve_base (.clk(fifo_clk), .d(reserve_base), .q(reserve_base__fq));
    wire [0:0] fill_start__fq;
    (* keep *) ot_hbm_face_reg #(.W(1)) u_bin_fill_start (.clk(fifo_clk), .d(fill_start), .q(fill_start__fq));
    wire [0:0] fill_start_bank__fq;
    (* keep *) ot_hbm_face_reg #(.W(1)) u_bin_fill_start_bank (.clk(fifo_clk), .d(fill_start_bank), .q(fill_start_bank__fq));
    wire [255:0] wd0__fq;
    assign wd0__fq = wd0; // WD input face resides in store child
    wire [255:0] wd1__fq;
    assign wd1__fq = wd1; // WD input face resides in store child
    wire [255:0] wd2__fq;
    assign wd2__fq = wd2; // WD input face resides in store child
    wire [255:0] wd3__fq;
    assign wd3__fq = wd3; // WD input face resides in store child
    wire [255:0] wd4__fq;
    assign wd4__fq = wd4; // WD input face resides in store child
    wire [255:0] wd5__fq;
    assign wd5__fq = wd5; // WD input face resides in store child
    wire [255:0] wd6__fq;
    assign wd6__fq = wd6; // WD input face resides in store child
    wire [255:0] wd7__fq;
    assign wd7__fq = wd7; // WD input face resides in store child
    wire [7:0] wd_v__fq;
    (* keep *) ot_hbm_face_reg #(.W(8)) u_bin_wd_v (.clk(fifo_clk), .d(wd_v), .q(wd_v__fq));
    wire [0:0] copy_on__fq;
    (* keep *) ot_hbm_face_reg #(.W(1)) u_bin_copy_on (.clk(fifo_clk), .d(copy_on), .q(copy_on__fq));
    wire [0:0] copy_bank__fq;
    (* keep *) ot_hbm_face_reg #(.W(1)) u_bin_copy_bank (.clk(fifo_clk), .d(copy_bank), .q(copy_bank__fq));
    wire [0:0] s_stop__fq;
    (* keep *) ot_hbm_face_reg #(.W(1)) u_bin_s_stop (.clk(fifo_clk), .d(s_stop), .q(s_stop__fq));
    wire [0:0] h_stop__fq;
    (* keep *) ot_hbm_face_reg #(.W(1)) u_bin_h_stop (.clk(fifo_clk), .d(h_stop), .q(h_stop__fq));
    wire [1:0] g_credit__fq;
    (* keep *) ot_hbm_face_reg #(.W(2)) u_bin_g_credit (.clk(fifo_clk), .d(g_credit), .q(g_credit__fq));
    wire [0:0] root_ready__fc;
    (* keep *) ot_hbm_face_reg #(.W(1)) u_bout_root_ready (.clk(fifo_clk), .d(root_ready__fc), .q(root_ready));
    wire [1:0] g_v__fc;
    (* keep *) ot_hbm_face_reg #(.W(2)) u_bout_g_v (.clk(fifo_clk), .d(g_v__fc), .q(g_v));
    wire [571:0] g_d__fc;
    (* keep *) ot_hbm_face_reg #(.W(572)) u_bout_g_d (.clk(fifo_clk), .d(g_d__fc), .q(g_d));
    ot_wbq_root u_fcore (
        .hbm_clk(hbm_clk),
        .fifo_clk(fifo_clk),
        .stream_rst_n(stream_rst_n),
        .hbm_rst_n(hbm_rst_n),
        .root_id(root_id__fq),
        .reserve_v(reserve_v__fq),
        .reserve_bank(reserve_bank__fq),
        .reserve_total(reserve_total__fq),
        .reserve_base(reserve_base__fq),
        .fill_start(fill_start__fq),
        .fill_start_bank(fill_start_bank__fq),
        .wd0(wd0__fq),
        .wd1(wd1__fq),
        .wd2(wd2__fq),
        .wd3(wd3__fq),
        .wd4(wd4__fq),
        .wd5(wd5__fq),
        .wd6(wd6__fq),
        .wd7(wd7__fq),
        .wd_v(wd_v__fq),
        .copy_on(copy_on__fq),
        .copy_bank(copy_bank__fq),
        .s_stop(s_stop__fq),
        .h_stop(h_stop__fq),
        .g_credit(g_credit__fq),
        .root_ready(root_ready__fc),
        .g_v(g_v__fc),
        .g_d(g_d__fc)
    );
endmodule
`default_nettype wire
