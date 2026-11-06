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

module ot_wbq_root #(parameter integer CRED=4, parameter integer MUT=0, parameter integer STORE_GROUP4=0)(
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
 generate if(STORE_GROUP4!=0)begin:g_store_groups
  for(g=0;g<2;g=g+1)begin:g_group4
`ifdef OT_WBQ_ROOT_STORE_FACES
   localparam integer FACES=1;
`else
   localparam integer FACES=0;
`endif
   wire [1151:0] heads;
   ot_wbq_root_store_group4 #(.LANE_BASE(4*g),.FACES(FACES)) u_store_group(
    .fifo_clk(fifo_clk),.hbm_clk(hbm_clk),.srst(srst),.hrst(hrst),
    .root_id(root_id),.base(base[copy_bank]),.total(total[fill_bank]),.committed(committed[copy_bank]),
    .filling(filling),.fill_bank(fill_bank),.ordinal(ordinal),.copy_q(copy_q),.copy_bank(copy_bank),
    .copy_start(copy_on&&!copy_q),.s_stop(s_stop),.wd({wd[4*g+3],wd[4*g+2],wd[4*g+1],wd[4*g]}),
    .wd_v(wd_v[4*g+:4]),.fifo_re(fifo_re[4*g+:4]),.fifo_head(heads),.fifo_empty(fifo_empty[4*g+:4]));
   for(genvar j=0;j<4;j=j+1)begin:g_head
    assign fifo_head[4*g+j]=heads[288*j+:288];
   end
  end
 end else begin:g_native_stores
  for(g=0;g<8;g=g+1)begin:g_lane
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
  end
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
// Raw store implementation is in ot_wbq_root_store_leaf.sv.



// Existing WD input-face capture relocated from the old outer shell.
module ot_wbq_root_store_face #(parameter integer LANE=0)(
 input wire fifo_clk,hbm_clk,srst,hrst,
 input wire [1:0]root_id,input wire [31:0]base,
 input wire [11:0]total,committed,ordinal,
 input wire filling,fill_bank,copy_q,copy_bank,copy_start,s_stop,
 input wire [255:0]wd,input wire wd_v,fifo_re,
 output wire [287:0]fifo_head,output wire fifo_empty
);
reg[255:0]wd_q;always @(posedge fifo_clk)wd_q<=wd;
ot_wbq_root_store #(.LANE(LANE)) u_native(.fifo_clk(fifo_clk),.hbm_clk(hbm_clk),.srst(srst),.hrst(hrst),.root_id(root_id),.base(base),.total(total),.committed(committed),.ordinal(ordinal),.filling(filling),.fill_bank(fill_bank),.copy_q(copy_q),.copy_bank(copy_bank),.copy_start(copy_start),.s_stop(s_stop),.wd(wd_q),.wd_v(wd_v),.fifo_re(fifo_re),.fifo_head(fifo_head),.fifo_empty(fifo_empty));
endmodule

module ot_wbq_sw #(parameter integer WOPEN=0, parameter integer CRED=4, parameter [29:0] STACK_SECTORS=30'd703125000, parameter integer HREG=0, parameter integer GIN=0)(
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
 always @(posedge stream_clk or negedge stream_rst_n)
  if(!stream_rst_n)begin rv_q<=0;fs_q<=0;end else begin rv_q<=wb_reserve_v;fs_q<=wb_fill_start;end
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
 wire srst,hrst;wire roots_ready=&root_ready;
 ot_reset_sync u_stream_reset(.clk(stream_clk),.async_rst_n(reset_both),.sync_rst_n(srst));
 ot_reset_sync u_hbm_reset(.clk(hbm_clk),.async_rst_n(reset_both),.sync_rst_n(hrst));
 reg [1:0] allocated,started,staged;reg [15:0] epoch[0:1];reg [31:0] base[0:1];reg [11:0] total[0:1];reg [11:0] committed[0:1];
 reg filling,fill_bank,copy_active,copy_bank;reg [11:0] ordinal;
 reg stream_sticky,hbm_sticky;(* async_reg = "true" *) reg hf1,hf2,sf1,sf2;
 wire [28:0] meta_data,ack_data;wire meta_full,meta_empty,ack_full,ack_empty;wire meta_we,meta_re,ack_we,ack_re;
 reg meta_active,ack_pending;reg [28:0] meta_q;reg [11:0] ack_count;
 reg [15:0] req_valid;reg [6:0] outstanding[0:15];reg [2:0] req_g[0:15];
 reg [15:0] pick_v;reg [2:0] pick_g[0:15];reg [7:0] pop;reg [2:0] selected_g[0:15];
 integer pc,l,acks;wire hbm_fault=hbm_sticky||sf2||!hrst;
 // HREG>=2 (g_f2): registered, replicated copies of the fault / meta gates, exact on every edge while hrst is high. While hrst is low
 // every flop they gate is held in reset, so the !hrst term of hbm_fault is not needed there (h_stop keeps hbm_fault).
 wire fg_w;wire [15:0] mah_w,kg_w;wire ma0_w;wire [3:0] as0_w,as1_w;
 wire fault_g=(HREG>=2)?(fg_w||!hrst):hbm_fault;   // meta_re pops the FIFO, so it keeps the !hrst term
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
  .rclk(hbm_clk),.rrst_n(hrst),.re(meta_re),.rdata(meta_data),.empty(meta_empty));
 assign meta_re=!meta_active&&!meta_empty&&!fault_g;
 assign ack_we=ack_pending&&!ack_full&&!fault_g;
 assign ack_re=srst&&!ack_empty&&!blk_fault;
 ot_hbm_accel_cdc_fifo #(.W(29),.AW(2)) u_ack(.wclk(hbm_clk),.wrst_n(hrst),.we(ack_we),.wdata(meta_q),.full(ack_full),.rd_freed(),
  .rclk(stream_clk),.rrst_n(srst),.re(ack_re),.rdata(ack_data),.empty(ack_empty));
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
      if(!wc_l[33*s+32]||wc_l[33*s+:32]!=(base[fill_bank]+ordinal+s))stream_sticky<=1;
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
  always @(posedge hbm_clk)if(g_vq[g])qm[qw[g]]<=g_dq[286*g+:286];
  always @(posedge hbm_clk or negedge hrst)begin
   if(!hrst)begin qw[g]<=0;qr[g]<=0;qn[g]<=0;end
   else begin
    if(g_vq[g])qw[g]<=qw[g]+1'b1;
    if(pop_u[g])qr[g]<=qr[g]+1'b1;
    qn[g]<=qn[g]+3'(g_vq[g])-3'(pop_u[g]);
   end
  end
  if(HREG!=0)begin:g_hr
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
 generate if(HREG!=0)begin:g_k1
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
    an1[i]=k_wr_done_q[i]&&(outstanding[i]!=0||(kv1[i]&&k_rdy[i]));
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
   if(k_wr_done_q[pc]&&(outstanding[pc]!=0||(k_v[pc]&&k_rdy[pc])))ack_now[pc]=1;
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
 wire [11:0] ack_rem_n=(HREG>=2)?{ack_dif[6]?ack_hi_m1:ack_rem[11:5],ack_dif[4:0]}:(ack_rem-12'(acks_t));
 wire [15:0] mah_g=(HREG>=2)?mah_w:{16{meta_active&&!hbm_fault}};
 wire ma0_g=(HREG>=2)?ma0_w:(meta_active&&!hbm_fault);
 integer h;
 always @(posedge hbm_clk or negedge hrst)begin
  if(!hrst)begin
   sf1<=0;sf2<=0;hbm_sticky<=0;meta_active<=0;meta_q<=0;ack_pending<=0;ack_count<=0;ack_rem<=0;req_valid<=0;
   for(h=0;h<16;h=h+1)begin req_g[h]<=0;outstanding[h]<=0;end
  end else begin
   sf1<=stream_sticky;sf2<=sf1;
   if(meta_re)begin meta_active<=1;meta_q<=meta_data;ack_count<=0;ack_rem<=meta_data[11:0];ack_pending<=0;end
   for(h=0;h<16;h=h+1)if(mah_g[h])begin
     if(kv_u[h]&&!k_rdy[h])begin req_valid[h]<=1;req_g[h]<=selected_g[h];end
     if(kv_u[h]&&k_rdy[h])req_valid[h]<=0;
     case({kv_u[h]&&k_rdy[h],k_wr_done_q[h]})
      2'b10:outstanding[h]<=outstanding[h]+1'b1;
      2'b01:if(outstanding[h]!=0)outstanding[h]<=outstanding[h]-1'b1;
      default:begin end
     endcase
     if(k_wr_done_q[h]&&!(outstanding[h]!=0||(kv_u[h]&&k_rdy[h])))hbm_sticky<=1;
    end
   if(ma0_g)begin
    if(ack_any_g)begin
     ack_count<=ack_count+12'(acks);ack_rem<=ack_rem_n;
     if(ack_gt)hbm_sticky<=1;
     if(ack_eq)ack_pending<=1;
    end
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
  always @*begin setH=0;for(z=0;z<16;z=z+1)if(k_wr_done_q[z]&&!(outstanding[z]!=0||(kv_u[z]&&k_rdy[z])))setH=1;end
  wire setO=ma0_w?setH:(|k_wr_done_q);
  wire setA=ma0_w&&ack_any_g&&ack_gt;
  wire fo_n=hbm_sticky||setO||sf1;
  wire ma_n=(meta_active||meta_re)&&!ack_we&&!fo_n;
  wire ap_n=!ack_we&&!meta_re&&(ack_pending||(ma0_w&&ack_any_g&&ack_eq));
  wire kg_n=ma_n&&!ap_n;
  genvar c;
  for(c=0;c<16;c=c+1)begin:g_c
   (* keep = "true" *) reg ma_c;(* keep = "true" *) reg kg_c;(* keep = "true" *) reg sa_c;
   always @(posedge hbm_clk or negedge hrst)if(!hrst)begin ma_c<=0;kg_c<=0;sa_c<=0;end else begin ma_c<=ma_n;kg_c<=kg_n;sa_c<=setA;end
   assign mah_w[c]=ma_c&&!sa_c;assign kg_w[c]=kg_c&&!sa_c;
  end
  (* keep = "true" *) reg fo0_c;(* keep = "true" *) reg sa0_c;(* keep = "true" *) reg ma0_c;
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
 always @(posedge stream_clk or negedge stream_rst_n)
  if(!stream_rst_n)begin rv1<=0;rv2<=0;end else begin rv1<=rv_q&&reserve_ready;rv2<=rv1;end
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
 always @(posedge stream_clk or negedge stream_rst_n)begin
  if(!stream_rst_n)begin
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
 wire [15:0] k_rdy_w;assign k_rdy=k_rdy_w;
 generate for(p=0;p<16;p=p+1)begin:pc_pin
  // HREG>=2: the skid takes its own synchronised copy of hbm_rst_n (async assert, release 2 edges later). Same pins: in those
  // edges the skid is empty either way and in_v=0 (the core is still in reset: hrst releases no earlier than krst)
  wire krst;
  if(HREG>=2)begin:g_kr ot_reset_sync u_krst(.clk(hbm_clk),.async_rst_n(hbm_rst_n),.sync_rst_n(krst));end
  else begin:g_kr0 assign krst=hbm_rst_n;end
  ot_hbm_svc_pin_skid2 #(.WIDTH(286)) u_k(.clk(hbm_clk),.rst_n(krst),.in_v(kv_u[p]),.in_r(k_rdy_w[p]),
   .in_data({fold(ka_u[30*p+:29],q_h),kd_u[256*p+:256]}),.out_v(w_k_v[p]),.out_r(w_k_rdy[p]),
   .out_data({w_k_addr[30*p+:30],w_k_wdata[256*p+:256]}));
 end endgenerate
endmodule
`default_nettype wire

`timescale 1ns/1ps
`default_nettype none
// Optional WBQ per-lane store; canonical source/recipes unchanged.
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
  .w_addr_in({fill_bank,ordinal[10:5]}),.wd_in(wd),.w_mask_in({256{1'b1}}),
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

// Optional four-lane hierarchy cut. No new state, reset, clock or edge.
// FACES=1 preserves each existing 256-bit fifo_clk WD capture exactly once.
// Packed lane j occupies [256*j+:256] and [288*j+:288]; LANE_BASE is 0 or 4.
// Every FIFO retains its own fifo_clk write side and hbm_clk read side.
module ot_wbq_root_store_group4 #(
 parameter integer LANE_BASE=0, parameter integer FACES=1
)(
 input wire fifo_clk,hbm_clk,srst,hrst,
 input wire [1:0]root_id,input wire [31:0]base,
 input wire [11:0]total,committed,ordinal,
 input wire filling,fill_bank,copy_q,copy_bank,copy_start,s_stop,
 input wire [1023:0]wd,input wire [3:0]wd_v,fifo_re,
 output wire [1151:0]fifo_head,output wire [3:0]fifo_empty
);
 genvar lane;
 generate for(lane=0;lane<4;lane=lane+1)begin:g_lane
  if(FACES!=0)begin:g_face
   ot_wbq_root_store_face #(.LANE(LANE_BASE+lane)) u_store(
    .fifo_clk(fifo_clk),.hbm_clk(hbm_clk),.srst(srst),.hrst(hrst),
    .root_id(root_id),.base(base),.total(total),.committed(committed),.ordinal(ordinal),
    .filling(filling),.fill_bank(fill_bank),.copy_q(copy_q),.copy_bank(copy_bank),
    .copy_start(copy_start),.s_stop(s_stop),.wd(wd[256*lane+:256]),.wd_v(wd_v[lane]),
    .fifo_re(fifo_re[lane]),.fifo_head(fifo_head[288*lane+:288]),.fifo_empty(fifo_empty[lane]));
  end else begin:g_raw
   ot_wbq_root_store #(.LANE(LANE_BASE+lane)) u_store(
    .fifo_clk(fifo_clk),.hbm_clk(hbm_clk),.srst(srst),.hrst(hrst),
    .root_id(root_id),.base(base),.total(total),.committed(committed),.ordinal(ordinal),
    .filling(filling),.fill_bank(fill_bank),.copy_q(copy_q),.copy_bank(copy_bank),
    .copy_start(copy_start),.s_stop(s_stop),.wd(wd[256*lane+:256]),.wd_v(wd_v[lane]),
    .fifo_re(fifo_re[lane]),.fifo_head(fifo_head[288*lane+:288]),.fifo_empty(fifo_empty[lane]));
  end
 end endgenerate
endmodule
