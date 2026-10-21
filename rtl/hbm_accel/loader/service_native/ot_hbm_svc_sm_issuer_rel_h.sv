`timescale 1ns/1ps
`default_nettype none
// HBM-SVGREL8 2026-10-20: HARDENED copy of ot_hbm_svc_sm_issuer_rel at the GEN2e4 r11 die parameters (XSLOT 0, CTXW 46;
// that module stays byte-identical).  Same descriptor format, faults, reserve pipeline A -> P -> S, start / go queues,
// and the SAME cycle of every output (reserve_*, start_*, program_start_*, running, run_done, fault).  Structural changes
// (safe-design checklist, native census of the r11 mapped netlist: rd_q / a_go / s_go / queue-pointer nets of 116..430
// loads):
//   * reset only on control / valid state, from ot_rst_relay leaves (rst_n[4:0], each <= 32 flops); datapath unreset;
//   * the wide pipeline registers load whenever their stage is EMPTY (a while !a_v, p while !p_v, st/s_ent while !st_v)
//     instead of on the one-cycle advance strobe: a stage is only read while its valid is set, and the advance edge is
//     an empty-stage edge, so the held value is identical.  The empty flags are KEPT replicated copies (one per <= 32
//     data bits);
//   * the 4-deep start / go queues write the free tail slot every edge (slot enable = registered one-hot tail AND not
//     full, KEPT per <= 32-bit slice) and read the head through a registered one-hot (KEPT per slice) AND-OR: no
//     runtime binary mux / decode on 116-bit entries.  A queue push is only legal into a free slot (push while full is
//     unreachable: an sq entry holds an allocated landing bank, the feed refuses a reserve without a free bank; gq push =
//     start_v requires gq_n < QD), so the slot value at the push edge is what the original wrote;
//   * the descriptor macro read mux (rp_q[7], 256 b) uses KEPT replicated bank-select copies.
module ot_hbm_svc_sm_issuer_rel_h #(parameter integer LBANKS=4, parameter integer LB=(LBANKS>2)?2:1, parameter integer QD=4,
 parameter integer NID=6, parameter integer IDW=9, parameter integer PAW=11, parameter integer DD=256, parameter integer MUT=0,
 parameter integer DAW=(DD>128)?8:7, parameter integer ID_COHORT=0)(
 input wire clk,input wire[4:0]rst_n,
 input wire desc_we,input wire[DAW-1:0]desc_addr,input wire[255:0]desc_data,
 input wire run_v,input wire[DAW-1:0]run_base,input wire[DAW:0]run_count,input wire[7:0]run_layer,
 input wire ids_v,input wire[7:0]ids_layer,input wire[IDW*NID-1:0]ids,
 input wire[15:0]ids_cohort,
 output reg running,run_done,fault,
 output wire reserve_v,input wire reserve_ready,output wire[31:0]reserve_base,output wire[14:0]reserve_row_base,
 output wire[11:0]reserve_total,output wire[LB-1:0]reserve_bank,output wire[15:0]reserve_epoch,output wire[6:0]reserve_rows,
 output wire[9:0]reserve_tag_base,
 input wire[LBANKS-1:0]block_ready,input wire[1:0]cache_ready,cache_owned,
 output wire start_v,output wire[LB-1:0]start_bank,output wire[15:0]start_epoch,
 output wire program_start_v,output wire[PAW-1:0]program_start_base,output wire[PAW:0]program_start_limit,
 output wire[15:0]program_start_loops,
 output wire[45:0]program_start_ctx,   // {row_off12, tag_base10, epoch16, bank1, lstep4, fl1, mode2}
 input wire program_done
);
`ifdef SVGH_MUT
 localparam integer HM=`SVGH_MUT;     // HBM-SVGREL8 bench negative controls (see the kit README)
`else
 localparam integer HM=0;
`endif
 initial if(NID<1||NID>15||IDW<1||IDW>9||(PAW!=10&&PAW!=11)||(DD!=128&&DD!=256)||QD!=4)$fatal(1,"issuer_rel_h parameters");
 // ---------------- descriptor table (DD/128 128x256 SRAMs, registered write port, written at install only)
 reg desc_we_q;reg[DAW-1:0]desc_addr_q;reg[255:0]desc_data_q;
 always @(posedge clk)begin desc_addr_q<=desc_addr;desc_data_q<=desc_data;end
 reg rd_q;reg[DAW-1:0]rp,rp_q;wire[255:0]rd;
 wire rd_go;
 localparam integer SS=12,NRS=(256+SS-1)/SS;                                  // rd mux bank-select copies (32 b each)
 (* keep="true",dont_touch="true" *) reg[NRS-1:0]rsel_k;    // = rp_q[7] (unreset, as rp_q)
 generate if(DD==128)begin:g_t1
  ot_sram_1r1w_128x256_m1_r2c2 u_desc(.clk(clk),.r_ce_in(rd_go),.r_addr_in(rp[6:0]),.rd_out(rd),
   .w_ce_in(desc_we_q&&!running),.w_addr_in(desc_addr_q[6:0]),.wd_in(desc_data_q),.w_mask_in({256{1'b1}}),
   .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 end else begin:g_t2
  wire[255:0]rd_lo,rd_hi;
  ot_sram_1r1w_128x256_m1_r2c2 u_desc_lo(.clk(clk),.r_ce_in(rd_go&&!rp[7]),.r_addr_in(rp[6:0]),.rd_out(rd_lo),
   .w_ce_in(desc_we_q&&!running&&!desc_addr_q[7]),.w_addr_in(desc_addr_q[6:0]),.wd_in(desc_data_q),.w_mask_in({256{1'b1}}),
   .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
  ot_sram_1r1w_128x256_m1_r2c2 u_desc_hi(.clk(clk),.r_ce_in(rd_go&&rp[7]),.r_addr_in(rp[6:0]),.rd_out(rd_hi),
   .w_ce_in(desc_we_q&&!running&&desc_addr_q[7]),.w_addr_in(desc_addr_q[6:0]),.wd_in(desc_data_q),.w_mask_in({256{1'b1}}),
   .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
  for(genvar s=0;s<NRS;s=s+1)begin:g_rs
   localparam integer B=(256-s*SS<SS)?256-s*SS:SS;
   assign rd[s*SS+:B]=rsel_k[s]?rd_hi[s*SS+:B]:rd_lo[s*SS+:B];
  end
 end endgenerate
 // ---------------- run / ids registers
 reg[7:0]layer_q,ids_layer_q;reg ids_ok_q;reg[IDW*NID-1:0]ids_q;
 reg[15:0]run_cohort_q;
 // ---------------- reserve pipeline A -> P -> S
 reg[DAW:0]n_rd,n_go;reg a_v,p_v,st_v;reg[199:0]a,p;reg[142:0]st;reg[23:0]p_lay,p_id;reg[23:0]rc;
 localparam integer QW=7+12+10+24+16+12+11+16+LB;
 localparam integer NS0=(143+SS-1)/SS;
 localparam integer NAK=(200+SS-1)/SS,NPK=NAK+4,NSK=NS0+(QW+SS-1)/SS;                      // empty-stage load-enable copies (<= 32 data bits each)
 (* keep="true",dont_touch="true" *) reg[NAK-1:0]av_k;      // = a_v
 (* keep="true",dont_touch="true" *) reg[NPK-1:0]pv_k;      // = p_v
 (* keep="true",dont_touch="true" *) reg[NSK-1:0]sv_k;      // = st_v
 wire[3:0]a_sel=a[176:173];
 wire a_ids=a_sel==0||(ids_ok_q&&ids_layer_q==layer_q);
 wire a_go=a_v&&!p_v&&a_ids;
 wire[IDW-1:0]a_id=(a_sel==0||MUT==2)?{IDW{1'b0}}:ids_q[(a_sel-4'd1)*IDW+:IDW];
 wire[25:0]s_blk={8'd0,p[46:32],p[9:7]}+{2'd0,p_lay}+{2'd0,p_id};
 wire s_go=p_v&&!st_v;
 assign rd_go=running&&n_rd!=0&&!a_v&&!rd_q;
 wire[6:0]st_rows=st[71:65];
 wire[12:0]st_total=(((st_rows*136)+127)>>7)<<2;
 assign reserve_v=st_v&&reserve_ready;
 assign reserve_base=st[31:0];assign reserve_row_base=st[46:32];assign reserve_total=st_total[11:0];
 assign reserve_bank=st[47+:LB];assign reserve_epoch=st[64:49];assign reserve_rows=st_rows;assign reserve_tag_base=st[81:72];
 // ---------------- start / go queues: {fl1, mode2, lstep4, row_off12, tag10, go_at24, loops16, limit12, base11, epoch16, landing LB}
 localparam integer NQS=(QW+SS-1)/SS;                         // 32-bit slices of a queue entry
 reg[QW-1:0]sq[0:QD-1],gq[0:QD-1];reg[2:0]sq_n,gq_n;reg[1:0]sq_r,sq_w,gq_r,gq_w;
 reg[QW-1:0]s_ent;
 (* keep="true",dont_touch="true" *) reg[QD*NQS-1:0]sqw_k,sqr_k,gqw_k,gqr_k;   // [k*NQS+s]: slot k, slice s
 reg[QW-1:0]sh,gh;integer qk,qs,qb;
 always @*begin
  sh=0;gh=0;
  for(qk=0;qk<QD;qk=qk+1)for(qb=0;qb<QW;qb=qb+1)begin
   if(sqr_k[qk*NQS+qb/SS])sh[qb]=sh[qb]|sq[qk][qb];
   if(gqr_k[qk*NQS+qb/SS])gh[qb]=gh[qb]|gq[qk][qb];
  end
 end
 wire[LB-1:0]sh_land=sh[LB-1:0];wire[LB-1:0]gh_land=gh[LB-1:0];
 assign start_v=sq_n!=0&&gq_n<QD&&block_ready[sh_land]&&!cache_owned[sh_land[0]];
 assign start_bank=sh_land;assign start_epoch=sh[LB+:16];
 reg go_busy;
 wire[23:0]gh_at=gh[LB+55+:24];
 assign program_start_v=gq_n!=0&&rc==gh_at;
 assign program_start_base=gh[LB+16+:PAW];assign program_start_limit=gh[LB+27+:PAW+1];assign program_start_loops=gh[LB+39+:16];
 wire[11:0]gh_roff=(MUT==3)?12'd0:gh[LB+89+:12];
 assign program_start_ctx={gh_roff,gh[LB+79+:10],gh[LB+:16],gh_land[0],gh[LB+101+:4],gh[LB+107],gh[LB+105+:2]};
 wire push_s=reserve_v,pop_s=start_v,push_g=start_v,pop_g=program_start_v;
 wire[DAW-1:0]rd_id=rd[232+:DAW];
 // ---------------- next state of the control registers (one copy, then registered + KEPT copies)
 reg running_n,run_done_n,fault_n,rd_q_n,a_v_n,p_v_n,st_v_n,go_busy_n,ids_ok_n;reg[15:0]cohort_n;
 reg[2:0]sq_n_n,gq_n_n;reg[1:0]sq_r_n,sq_w_n,gq_r_n,gq_w_n;
 always @*begin
  running_n=running;run_done_n=0;fault_n=fault;rd_q_n=rd_go;a_v_n=a_v;p_v_n=p_v;st_v_n=st_v;go_busy_n=go_busy;
  ids_ok_n=ids_ok_q;cohort_n=run_cohort_q;
  if(run_v)begin
   if(running||run_count==0||{1'b0,run_base}+run_count>(DD))fault_n=1;
   else begin running_n=1;if(ID_COHORT!=0)begin ids_ok_n=0;cohort_n=run_cohort_q+16'd1;end end
  end
  if(ids_v)begin
   if(ID_COHORT!=0&&(!running||run_v||ids_ok_q||ids_layer!=layer_q||ids_cohort!=run_cohort_q))fault_n=1;
   else ids_ok_n=1;
  end
  if(rd_q)begin
   a_v_n=1;
   if(rd[255:240]!=16'h5d15||rd_id!=rp_q||(DAW==7&&rd[239])||rd[231:200]!=0||rd[176:173]>NID)fault_n=1;
  end
  if(a_go)begin a_v_n=0;p_v_n=1;end
  if(ID_COHORT!=0&&a_v&&a_sel!=0&&!a_ids&&rc>=a[142:119])fault_n=1;
  if(s_go)begin p_v_n=0;st_v_n=1;if(s_blk>=26'd262144)fault_n=1;end
  if(reserve_v)st_v_n=0;
  sq_w_n=sq_w+(push_s?2'd1:2'd0);sq_r_n=sq_r+(pop_s?2'd1:2'd0);
  sq_n_n=sq_n+(push_s?3'd1:3'd0)-(pop_s?3'd1:3'd0);
  gq_w_n=gq_w+(push_g?2'd1:2'd0);gq_r_n=gq_r+(pop_g?2'd1:2'd0);
  gq_n_n=gq_n+(push_g?3'd1:3'd0)-(pop_g?3'd1:3'd0);
  if(push_s&&sq_n==QD&&!pop_s)fault_n=1;
  if(pop_g)go_busy_n=1;
  if(gq_n!=0&&(rc==gh_at&&(go_busy||!cache_ready[gh_land[0]])||rc>gh_at))fault_n=1;   // missed slot: never waits
  if(program_done)begin
   if(!go_busy)fault_n=1;
   go_busy_n=0;
   if(running&&n_go==1)begin running_n=0;run_done_n=1;end
  end
 end
 // rst_n[0]: the scalar control state (24 flops)
 always @(posedge clk or negedge rst_n[0])begin
  if(!rst_n[0])begin
   running<=0;run_done<=0;fault<=0;rd_q<=0;a_v<=0;p_v<=0;st_v<=0;go_busy<=0;ids_ok_q<=0;desc_we_q<=0;
   sq_n<=0;gq_n<=0;sq_r<=0;sq_w<=0;gq_r<=0;gq_w<=0;
  end else begin
   running<=running_n;run_done<=run_done_n;fault<=fault_n;rd_q<=rd_q_n;a_v<=a_v_n;p_v<=p_v_n;st_v<=st_v_n;
   go_busy<=go_busy_n;ids_ok_q<=ids_ok_n;desc_we_q<=desc_we;
   sq_n<=sq_n_n;gq_n<=gq_n_n;sq_r<=sq_r_n;sq_w<=sq_w_n;gq_r<=gq_r_n;gq_w<=gq_w_n;
  end
 end
 // Regional copy resets: <=22 control bits per leaf (queue slots20).
 // New reset landing adds one startup edge; descriptor/data transaction edges stay unchanged.
 wire [0:0] ar;
 wire [1:0] psr;
 wire [QD-1:0] sqr,gqr;
 ot_rst_fanout #(.N(1)) u_ar(.clk(clk),.rst_n_in(rst_n[1]),.rst_n(ar));
 ot_rst_fanout #(.N(2)) u_psr(.clk(clk),.rst_n_in(rst_n[2]),.rst_n(psr));
 ot_rst_fanout #(.N(QD)) u_sqr(.clk(clk),.rst_n_in(rst_n[3]),.rst_n(sqr));
 ot_rst_fanout #(.N(QD)) u_gqr(.clk(clk),.rst_n_in(rst_n[4]),.rst_n(gqr));
 always @(posedge clk or negedge rst_n[1])
  if(!rst_n[1])run_cohort_q<=0;else run_cohort_q<=cohort_n;
 always @(posedge clk or negedge ar[0])
  if(!ar[0])av_k<=0;else av_k<={NAK{a_v_n}};
 always @(posedge clk or negedge psr[0])
  if(!psr[0])pv_k<=0;else pv_k<={NPK{p_v_n}};
 always @(posedge clk or negedge psr[1])
  if(!psr[1])sv_k<=0;else sv_k<={NSK{st_v_n}};
 for(genvar wk=0;wk<QD;wk=wk+1)begin:g_qcopy
  always @(posedge clk or negedge sqr[wk])begin
   if(!sqr[wk])begin
    sqw_k[wk*NQS+:NQS]<={NQS{wk==0}};
    sqr_k[wk*NQS+:NQS]<={NQS{wk==0}};
   end else begin
    sqw_k[wk*NQS+:NQS]<={NQS{sq_w_n==wk&&sq_n_n<QD}};
    sqr_k[wk*NQS+:NQS]<={NQS{sq_r_n==wk}};
   end
  end
  always @(posedge clk or negedge gqr[wk])begin
   if(!gqr[wk])begin
    gqw_k[wk*NQS+:NQS]<={NQS{wk==0}};
    gqr_k[wk*NQS+:NQS]<={NQS{wk==0}};
   end else begin
    gqw_k[wk*NQS+:NQS]<={NQS{gq_w_n==wk&&gq_n_n<QD}};
    gqr_k[wk*NQS+:NQS]<={NQS{((HM==3)?gq_r:gq_r_n)==wk}};
   end
  end
 end
 // ---------------- datapath (no reset)
 wire run_ok=run_v&&!(running||run_count==0||{1'b0,run_base}+run_count>(DD));
 wire ids_ok=ids_v&&!(ID_COHORT!=0&&(!running||run_v||ids_ok_q||ids_layer!=layer_q||ids_cohort!=run_cohort_q));
 wire[23:0]p_lay_d=(MUT==1)?24'd0:24'(layer_q)*24'(a[157:143]);
 wire[23:0]p_id_d=24'(a_id)*24'(a[172:158]);
 wire[142:0]st_d={p[142:47],s_blk[17:3],p[31:10],s_blk[2:0],p[6:0]};
 wire[QW-1:0]s_ent_d={p[199],p[196:195],p[194:191],p[188:177],p[81:72],p[142:119],p[118:103],p[190],p[102:92],p[189],p[91:82],p[64:49],p[47+:LB]};
 integer ab;
 always @(posedge clk)begin
  // same statement order as ot_hbm_svc_sm_issuer_rel (last assignment wins)
  if(run_ok)begin rp<=run_base;n_rd<=run_count;n_go<=run_count;rc<=0;layer_q<=run_layer;end
  if(ids_ok)begin ids_layer_q<=ids_layer;ids_q<=ids;end
  rp_q<=rp;rsel_k<={NRS{rp[DAW-1]}};
  if(running&&!run_v)rc<=rc+24'd1;
  if(rd_go)begin rp<=rp+1'b1;n_rd<=n_rd-1'b1;end
  if(program_done)n_go<=n_go-1'b1;
  // stage registers: load while the stage is empty (the KEPT copy of its valid gates each <= 32-bit slice)
  for(ab=0;ab<200;ab=ab+1)begin
   if(!av_k[ab/SS])a[ab]<=rd[ab];
   if(!pv_k[ab/SS])p[ab]<=a[ab];
  end
  for(ab=0;ab<24;ab=ab+1)begin
   if(!pv_k[NAK+ab/SS])p_lay[ab]<=p_lay_d[ab];
   if(!pv_k[NAK+2+ab/SS])p_id[ab]<=p_id_d[ab];
  end
  for(ab=0;ab<143;ab=ab+1)if(!sv_k[ab/SS])st[ab]<=st_d[ab];
  for(ab=0;ab<QW;ab=ab+1)if(!sv_k[NS0+ab/SS])s_ent[ab]<=s_ent_d[ab];
  // queues: the free tail slot follows its producer every edge
  for(qk=0;qk<QD;qk=qk+1)for(qb=0;qb<QW;qb=qb+1)begin
   if(sqw_k[qk*NQS+qb/SS])sq[qk][qb]<=s_ent[qb];
   if(gqw_k[qk*NQS+qb/SS])gq[qk][qb]<=sh[qb];
  end
 end
endmodule
`default_nettype wire
