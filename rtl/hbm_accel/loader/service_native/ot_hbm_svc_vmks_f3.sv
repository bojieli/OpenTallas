// CODEX KSH F3: source-local, same-edge online/reset retention and 32-bit write slices.
// PIN CYCLES: zero added relative to F2. wr_pending is the existing pre-ready fs_v,
// while wr_valid stays fs_v&&f_r, preserving sticky-overflow behavior exactly.
// Mutation26 drops slice1 online permission; never enabled in production.
`timescale 1ns/1ps
`default_nettype none
// HBM-HARD-2-KSH 2026-11-07: form f2 of ot_hbm_svc_vm_kshare_splitstrap.  Same pins as the master and f1; uses from f1:
// ot_hbm_svc_pin_skid2_ptr and ot_hbm_svc_vmks_ctl (WCNT stage, GUARD).  Each change names the measured sign-off path it removes
// (kits v8e478a vK0, v700685 vK0, t0 TT census):
//   RST_TREE  hrst_q/srst_q -> one flop per lane + ctl -> one flop per lane block.  hrst_q -> u_c.rp -66 ps, reset_pipe merged over lanes -84 ps.
//             RESET +2 hbm/stream edges on release; assert stays asynchronous.  K traffic must start >= 3 edges after the pin release.
//   TAKE_REG  lanes take the window command from a per-lane flop, keep their own copy of the command and count, and the lane norm returns
//             through a per-lane flop.  st(lane a) -> j/st(lane b) -44 ps, s_norm -> j/cmd_q -28 ps.
//             PIN CYCLES: window start +1 hbm edge; a queued window waits +1 hbm edge more.  Fault +1 hbm edge.
//   SEL_REG   b_in_d select, vm_phase and w_more are flops loaded from the FSM next state, one select copy per 64 data bits.  Cycle exact.
//             st -> u_b.out_data -61 ps, wsent -> u_e/u_b -37 ps.
//   FIFO_SL   VM FIFO: one read and one write pointer copy per 64 data bits.  Cycle exact.  rd_bin -> fill_data -45 ps.
// PTR_SKID, FILL_STAGE and WCNT_STAGE stay on (f1 PIN CYCLES fill_* +1, wbw_* +1).
// Bench mutants added to the MUT list of forms.sv: 12 no window guard (forms.sv); 17 one select copy one edge late; 18 w_more from the old wsent;
//   19 one read pointer copy skips a pop; 20 one write pointer copy skips a push; 21 lane 2 misses a command copy load; 25 lane 3 misses a count copy load;
//   22 one lane block is out of the reset tree; 23 lane norm copy stuck high; 24 fault copy lost.
module ot_hbm_svc_async_fifo_local3 #(parameter integer WIDTH=32,DEPTH=8,SL=32,MUT=0)(
 input wire wr_clk,wr_rst_n,wr_valid,wr_pending,output wire wr_ready,
 input wire [WIDTH-1:0] wr_data,output reg wr_overflow,
 input wire rd_clk,rd_rst_n,output wire rd_valid,input wire rd_ready,
 output wire [WIDTH-1:0] rd_data,output reg rd_underflow
);
 localparam integer AW=$clog2(DEPTH),PW=AW+1,NS=(WIDTH+SL-1)/SL;
 wire both_reset=wr_rst_n&&rd_rst_n;wire wr_reset,rd_reset;
 ot_reset_sync u_wr_reset(.clk(wr_clk),.async_rst_n(both_reset),.sync_rst_n(wr_reset));
 ot_reset_sync u_rd_reset(.clk(rd_clk),.async_rst_n(both_reset),.sync_rst_n(rd_reset));
 reg [PW-1:0] wr_bin,wr_gray,rd_bin,rd_gray;
 (* async_reg="true" *)reg [PW-1:0] rd_gray_w1,rd_gray_w2,wr_gray_r1,wr_gray_r2;
 (* keep = "true" *) reg wr_online,rd_online;
 (* keep = "true", async_reg="true" *)reg rd_online_w1,rd_online_w2,wr_online_r1,wr_online_r2;
 wire full=wr_gray=={~rd_gray_w2[PW-1:PW-2],rd_gray_w2[PW-3:0]};
 wire empty=rd_gray==wr_gray_r2;
 assign wr_ready=wr_reset&&rd_online_w2&&!full;
 assign rd_valid=rd_reset&&wr_online_r2&&!empty;
 wire wr_fire=wr_valid&&wr_ready,rd_fire=rd_valid&&rd_ready;
 wire [PW-1:0] wr_next=wr_bin+wr_fire,rd_next=rd_bin+rd_fire;
 always @(posedge wr_clk or negedge wr_reset)begin
  if(!wr_reset)begin
   wr_bin<=0;wr_gray<=0;rd_gray_w1<=0;rd_gray_w2<=0;
   wr_online<=0;rd_online_w1<=0;rd_online_w2<=0;wr_overflow<=0;
  end else begin
   wr_online<=1;rd_online_w1<=rd_online;rd_online_w2<=rd_online_w1;
   rd_gray_w1<=rd_gray;rd_gray_w2<=rd_gray_w1;
   if(wr_valid&&!wr_ready)wr_overflow<=1;
   if(wr_fire)begin wr_bin<=wr_next;wr_gray<=(wr_next>>1)^wr_next;end
  end
 end
 always @(posedge rd_clk or negedge rd_reset)begin
  if(!rd_reset)begin
   rd_bin<=0;rd_gray<=0;wr_gray_r1<=0;wr_gray_r2<=0;
   rd_online<=0;wr_online_r1<=0;wr_online_r2<=0;rd_underflow<=0;
  end else begin
   rd_online<=1;wr_online_r1<=wr_online;wr_online_r2<=wr_online_r1;
   wr_gray_r1<=wr_gray;wr_gray_r2<=wr_gray_r1;
   if(rd_ready&&!rd_valid)rd_underflow<=1;
   if(rd_fire)begin rd_bin<=rd_next;rd_gray<=(rd_next>>1)^rd_next;end
  end
 end
 genvar s;
 generate for(s=0;s<NS;s=s+1)begin:g_sl
  localparam integer LO=s*SL;
  localparam integer W=(LO+SL>WIDTH)?(WIDTH-LO):SL;
  (* keep *) reg[AW-1:0]wp_k,rp_k;
  // Same edge/value as rd_online_w2; retained per slice to bound write-enable fanout.
  (* keep = "true", async_reg = "true" *) reg online_k;
  always @(posedge wr_clk or negedge wr_reset)
   if(!wr_reset) online_k<=0;
   else online_k <= (MUT==26 && s==1) ? 1'b0 : ((MUT==27 && s==1) ? rd_online_w2 : rd_online_w1);
  wire wr_fire_k = wr_pending && wr_reset && online_k && !full;
  reg[W-1:0]mem[0:DEPTH-1];
  always @(posedge wr_clk or negedge wr_reset)if(!wr_reset)wp_k<=0;else if(wr_fire_k&&!(MUT==20&&s==1&&wp_k==3))wp_k<=wp_k+1'b1;
  always @(posedge rd_clk or negedge rd_reset)if(!rd_reset)rp_k<=0;else if(rd_fire&&!(MUT==19&&s==1&&rp_k==3))rp_k<=rp_k+1'b1;
  always @(posedge wr_clk)if(wr_fire_k)mem[wp_k]<=wr_data[LO+:W];
  assign rd_data[LO+:W]=mem[rp_k];
 end endgenerate
endmodule

// reset leaf: async clear from the tree, release one edge later
module ot_hbm_svc_vmks_rstleaf3(input wire clk,input wire rst_in,output wire rst_q);
 (* keep = "true" *) reg local_rst_q;
 assign rst_q=local_rst_q;
 always @(posedge clk or negedge rst_in)if(!rst_in)local_rst_q<=1'b0;else local_rst_q<=1'b1;
endmodule

module ot_hbm_svc_vmks_lane_f3 #(parameter integer LANE=0,MUT=0,KRL1=1)(
 input wire hbm_clk,stream_clk,hrst_l,srst_l,input wire[2:0]sm_h,
 input wire take_cmd,take_wb,input wire[35:0]cmd_q,input wire[7:0]wn_in,input wire[29:0]wc_base_in,input wire[30:0]wend_in,
 input wire g_k_v,output wire g_k_rdy,input wire[29:0]g_k_addr,input wire[3:0]g_k_len,input wire[16:0]g_k_tag,
 input wire g_k_we,input wire[255:0]g_k_wdata,input wire[31:0]g_k_wstrb,output reg g_k_wr_done,
 output wire g_kr_v,input wire g_kr_rdy,output wire[16:0]g_kr_tag,output wire[3:0]g_kr_beat,output wire[255:0]g_kr_data,
 output wire c_k_v,input wire c_k_rdy,output wire[29:0]c_k_addr,output wire[3:0]c_k_len,output wire[16:0]c_k_tag,
 output wire c_k_we,output wire[255:0]c_k_wdata,output wire[31:0]c_k_wstrb,input wire c_k_wr_done,
 input wire c_kr_v,output wire c_kr_rdy,input wire[16:0]c_kr_tag,input wire[3:0]c_kr_beat,input wire[255:0]c_kr_data,
 input wire w_k_v,output wire w_k_rdy,input wire[29:0]w_k_addr,input wire[255:0]w_k_wdata,output reg w_k_wr_done,
 output reg fill_v,fill_bank,output reg[5:0]fill_slot,output reg[15:0]fill_epoch,output reg[255:0]fill_data,
 output wire norm,hfault
);
 localparam integer KW=1+30+4+17+32+256,RW=17+4+256,FW=1+16+6+256,NSEL=(KW+63)/64;
 localparam[2:0]NORM=0,PEND=1,ISSUE=2,WAIT=3,WPEND=4,WB=5;
 // reset leaves, one per lane block
 wire r_a,r_e,r_b,r_c,r_d,r_f,r_s,s_f;
 ot_hbm_svc_vmks_rstleaf3 u_ra(.clk(hbm_clk),.rst_in(hrst_l),.rst_q(r_a));
 ot_hbm_svc_vmks_rstleaf3 u_re(.clk(hbm_clk),.rst_in(hrst_l),.rst_q(r_e));
 wire r_b0;
 ot_hbm_svc_vmks_rstleaf3 u_rb(.clk(hbm_clk),.rst_in(hrst_l),.rst_q(r_b0));
 assign r_b=(MUT==22&&LANE==1)?1'b1:r_b0;
 ot_hbm_svc_vmks_rstleaf3 u_rc(.clk(hbm_clk),.rst_in(hrst_l),.rst_q(r_c));
 ot_hbm_svc_vmks_rstleaf3 u_rd(.clk(hbm_clk),.rst_in(hrst_l),.rst_q(r_d));
 ot_hbm_svc_vmks_rstleaf3 u_rf(.clk(hbm_clk),.rst_in(hrst_l),.rst_q(r_f));
 ot_hbm_svc_vmks_rstleaf3 u_rs(.clk(hbm_clk),.rst_in(hrst_l),.rst_q(r_s));
 ot_hbm_svc_vmks_rstleaf3 u_sf(.clk(stream_clk),.rst_in(srst_l),.rst_q(s_f));
 // local copies of the window command and the strap
 reg[35:0]cmd_l;reg[7:0]wn;reg[29:0]wc_base;reg[30:0]wend_q;reg[2:0]sm_l;
 always @(posedge hbm_clk)begin
  sm_l<=sm_h;
  if(take_cmd&&!(MUT==21&&LANE==2&&cmd_q[4]))cmd_l<=cmd_q;
  if(take_wb)begin if(!(MUT==25&&LANE==3&&wn_in[0]))wn<=wn_in;wc_base<=wc_base_in;wend_q<=wend_in;end
 end
 wire[35:0]cmd_u=cmd_l;
 wire cm_bank=cmd_u[35];wire[15:0]cm_epoch=cmd_u[34:19];wire[14:0]cm_row=cmd_u[18:4];wire[3:0]cm_col=cmd_u[3:0];
 wire[4:0]P={sm_l,2'(LANE)};
 wire a_v,a_r;wire[KW-1:0]a_d;
 wire e_v,e_r;wire[285:0]e_d;
 wire b_in_v,b_in_r,b_v;wire[KW-1:0]b_in_d,b_d;
 wire c_v,c_r;wire[RW-1:0]c_d;
 wire d_r;
 wire[KW-1:0]a_in={g_k_we,g_k_addr,g_k_len,g_k_tag,g_k_wstrb,g_k_wdata};
 wire[RW-1:0]d_out;
 assign {g_kr_tag,g_kr_beat,g_kr_data}=d_out;
 ot_hbm_svc_pin_skid2_ptr #(.WIDTH(KW),.MUT((MUT==10)?1:0)) u_a(.clk(hbm_clk),.rst_n(r_a),.in_v(g_k_v),.in_r(g_k_rdy),.in_data(a_in),.out_v(a_v),.out_r(a_r),.out_data(a_d));
 ot_hbm_svc_pin_skid2_ptr #(.WIDTH(286)) u_e(.clk(hbm_clk),.rst_n(r_e),.in_v(w_k_v),.in_r(w_k_rdy),.in_data({w_k_addr,w_k_wdata}),.out_v(e_v),.out_r(e_r),.out_data(e_d));
 ot_hbm_svc_pin_skid2_ptr #(.WIDTH(KW)) u_b(.clk(hbm_clk),.rst_n(r_b),.in_v(b_in_v),.in_r(b_in_r),.in_data(b_in_d),.out_v(b_v),.out_r(c_k_rdy),.out_data(b_d));
 reg vm_phase_q;
 ot_hbm_svc_pin_skid2_ptr #(.WIDTH(RW)) u_d(.clk(hbm_clk),.rst_n(r_d),.in_v(c_v&&!vm_phase_q),.in_r(d_r),.in_data(c_d),.out_v(g_kr_v),.out_r(g_kr_rdy),.out_data(d_out));
 reg[2:0]st,st_n;reg[3:0]j;reg[6:0]got;reg[7:0]g_rd_out;reg[5:0]g_wr_out;reg hf;reg[7:0]wsent,wsent_n,wdone;
 reg w_more_q;
 wire wb_st=st==WB;
 wire[29:0]e_a=e_d[285:256];
 wire[29:0]w_addr=(MUT==4)?(e_a^30'h4):e_a;
 wire e_bad=(e_a[6:2]^e_a[11:7]^e_a[16:12])!=P||e_a<wc_base||{1'b0,e_a}>=wend_q;
 wire[4:0]bhi5={cm_row[1:0],j[2:0]};wire[4:0]col={cm_col,j[3]};
 wire[4:0]pcf=(MUT==2)?(col^bhi5):(P^col^bhi5);
 wire[29:0]vm_addr={cm_row,j[2:0],col,pcf,2'b00};
 wire[16:0]vm_tag={cm_bank,cm_epoch[11:0],j};
 wire vm_req=st==ISSUE;
 assign b_in_v=vm_req?1'b1:wb_st?(e_v&&w_more_q):(st==NORM&&a_v);
 wire[KW-1:0]vm_d={1'b0,vm_addr,4'd4,vm_tag,32'd0,256'd0};
 wire[KW-1:0]wb_d={1'b1,w_addr,4'd1,{1'b1,8'd0,wsent},32'hffffffff,e_d[255:0]};
 genvar s;
 generate for(s=0;s<NSEL;s=s+1)begin:g_sel
  localparam integer LO=s*64;
  localparam integer W=(LO+64>KW)?(KW-LO):64;
  (* keep *) reg sel_vm,sel_wb;
  always @(posedge hbm_clk or negedge r_s)
   if(!r_s)begin sel_vm<=1'b0;sel_wb<=1'b0;end
   else if(MUT==17&&s==2)begin sel_vm<=st==ISSUE;sel_wb<=st==WB;end
   else begin sel_vm<=st_n==ISSUE;sel_wb<=st_n==WB;end
  assign b_in_d[LO+:W]=sel_vm?vm_d[LO+:W]:sel_wb?wb_d[LO+:W]:a_d[LO+:W];
 end endgenerate
 assign e_r=w_more_q&&b_in_r;
 wire w_push=wb_st&&b_in_v&&b_in_r;
 assign a_r=st==NORM&&b_in_r;
 assign c_k_v=b_v;
 assign {c_k_we,c_k_addr,c_k_len,c_k_tag,c_k_wstrb,c_k_wdata}=b_d;
 wire b_pop=b_v&&c_k_rdy;
 wire b_pop_grp=b_pop&&!(st==ISSUE||st==WAIT||st==WB);
 wire c_ring_fault;
 generate if(KRL1!=0)begin:g_c_rl1
  reg c_rdy_q,c_rdy_seen;wire[2:0]c_cnt,c_cnt_next;
  ot_hbm_svc_ring_h9b_ff #(.WIDTH(RW),.DEPTH((MUT==6)?2:3)) u_c(.clk(hbm_clk),.rst_n(r_c),.in_v(c_kr_v&&c_rdy_seen),
   .in_data({c_kr_tag,c_kr_beat,c_kr_data}),.out_v(c_v),.pop(c_v&&c_r),.out_data(c_d),
   .cnt(c_cnt),.cnt_next(c_cnt_next),.fault(c_ring_fault));
  always @(posedge hbm_clk)
   if(!r_c)begin c_rdy_q<=1'b0;c_rdy_seen<=1'b0;end
   else begin c_rdy_q<=c_cnt_next<=3'd1;c_rdy_seen<=c_rdy_q;end
  assign c_kr_rdy=c_rdy_q;
 end else begin:g_c_rl0
  assign c_ring_fault=1'b0;
  ot_hbm_svc_pin_skid2 #(.WIDTH(RW)) u_c(.clk(hbm_clk),.rst_n(r_c),.in_v(c_kr_v),.in_r(c_kr_rdy),
   .in_data({c_kr_tag,c_kr_beat,c_kr_data}),.out_v(c_v),.out_r(c_r),.out_data(c_d));
 end endgenerate
 wire fs_in_r,f_r;
 assign c_r=vm_phase_q?fs_in_r:d_r;
 wire c_pop_grp=c_v&&!vm_phase_q&&d_r;
 wire c_pop_vm=c_v&&vm_phase_q&&fs_in_r;
 wire[16:0]rt=c_d[RW-1-:17];wire[3:0]rb=c_d[259:256];
 wire tag_ok=rt=={cm_bank,cm_epoch[11:0],rt[3:0]}&&rb<4;
 wire[FW-1:0]f_d={cm_bank,cm_epoch,rt[3:0],rb[1:0],c_d[255:0]};
 wire f_ov,f_un,rf_valid;wire[FW-1:0]rf_data;
 // one register ahead of the FIFO write, never valid into a full FIFO (f1)
 reg fs_v;reg[FW-1:0]fs_d;
 assign fs_in_r=!fs_v||f_r;
 always @(posedge hbm_clk or negedge r_f)if(!r_f)fs_v<=1'b0;else if(fs_in_r)fs_v<=c_pop_vm;
 always @(posedge hbm_clk)if(c_pop_vm||(MUT==9&&c_v&&vm_phase_q))fs_d<=f_d;
 ot_hbm_svc_async_fifo_local3 #(.WIDTH(FW),.DEPTH(8),.MUT(MUT)) u_fill(
  .wr_clk(hbm_clk),.wr_rst_n(r_f),.wr_pending(fs_v),.wr_valid(fs_v&&f_r),.wr_ready(f_r),.wr_data(fs_d),.wr_overflow(f_ov),
  .rd_clk(stream_clk),.rd_rst_n(s_f),.rd_valid(rf_valid),.rd_ready(rf_valid),.rd_data(rf_data),.rd_underflow(f_un));
 wire[8:0]rd_beats=b_pop_grp&&!b_d[KW-1]?{5'd0,b_d[KW-1-30-1-:4]}:9'd0;
 wire drained=!b_v&&g_rd_out==0&&g_wr_out==0;
 wire wdrained=!b_v&&(g_wr_out==0||MUT==3);
 wire g_done=c_k_wr_done&&!wb_st;
 // FSM next state: the select, vm_phase and w_more flops load from it, so they equal the old decodes of st every edge
 always @*begin
  st_n=st;wsent_n=wsent;
  if(w_push)wsent_n=wsent+1'b1;
  case(st)
   NORM:if(take_cmd)st_n=PEND;
        else if(take_wb)begin st_n=WPEND;wsent_n=8'd0;end
   PEND:if(drained||MUT==1)st_n=ISSUE;
   ISSUE:if(b_in_r&&j==4'd15)st_n=WAIT;
   WPEND:if(wdrained)st_n=WB;
   WB:if(wsent==wn&&wdone==wn)st_n=NORM;
   default:;
  endcase
  if(c_pop_vm&&got==7'd63)st_n=NORM;
 end
 always @(posedge hbm_clk or negedge r_s)begin
  if(!r_s)begin st<=NORM;j<=0;got<=0;g_rd_out<=0;g_wr_out<=0;hf<=0;wsent<=0;wdone<=0;vm_phase_q<=1'b0;w_more_q<=1'b0;end
  else begin
   st<=st_n;wsent<=wsent_n;
   vm_phase_q<=(st_n==ISSUE||st_n==WAIT)^(MUT==1&&st_n==PEND);
   w_more_q<=st_n==WB&&((MUT==18)?wsent:wsent_n)!=wn;
   g_rd_out<=g_rd_out+rd_beats[7:0]-{7'd0,c_pop_grp};
   g_wr_out<=g_wr_out+{5'd0,b_pop_grp&&b_d[KW-1]}-{5'd0,g_done};
   if(g_done&&g_wr_out==0)hf<=1;
   if(w_push&&e_bad)hf<=1;
   if(c_k_wr_done&&wb_st)begin wdone<=wdone+1'b1;if(wdone==wsent)hf<=1;end
   if(c_pop_grp&&g_rd_out==0&&!(MUT==1))hf<=1;
   if(c_pop_vm&&!tag_ok)hf<=1;
   if(st==NORM&&take_cmd)begin j<=0;got<=0;end
   else if(st==NORM&&take_wb)wdone<=0;
   if(st==ISSUE&&b_in_r)j<=j+1'b1;
   if(c_pop_vm)got<=got+1'b1;
  end
 end
 always @(posedge hbm_clk or negedge r_s)
  if(!r_s)begin g_k_wr_done<=0;w_k_wr_done<=0;end
  else begin g_k_wr_done<=g_done;w_k_wr_done<=c_k_wr_done&&wb_st;end
 assign norm=st==NORM;assign hfault=hf||f_ov||c_ring_fault;
 always @(posedge stream_clk or negedge s_f)if(!s_f)fill_v<=0;else fill_v<=rf_valid;
 always @(posedge stream_clk){fill_bank,fill_epoch,fill_slot,fill_data}<=rf_data;
endmodule

// ONE TILE f2: same pin list as ot_hbm_svc_vm_kshare_splitstrap.
module ot_hbm_svc_vm_kshare_splitstrap_f3 #(parameter integer MUT=0,KRL1=1,GUARD=3) (
 input wire hbm_clk,hbm_rst_n,stream_clk,stream_rst_n,
 input wire[2:0]sm_stream,sm_hbm,
 input wire[3:0]g_k_v,output wire[3:0]g_k_rdy,input wire[119:0]g_k_addr,input wire[15:0]g_k_len,input wire[67:0]g_k_tag,
 input wire[3:0]g_k_we,input wire[1023:0]g_k_wdata,input wire[127:0]g_k_wstrb,output wire[3:0]g_k_wr_done,
 output wire[3:0]g_kr_v,input wire[3:0]g_kr_rdy,output wire[67:0]g_kr_tag,output wire[15:0]g_kr_beat,output wire[1023:0]g_kr_data,
 output wire[3:0]c_k_v,input wire[3:0]c_k_rdy,output wire[119:0]c_k_addr,output wire[15:0]c_k_len,output wire[67:0]c_k_tag,
 output wire[3:0]c_k_we,output wire[1023:0]c_k_wdata,output wire[127:0]c_k_wstrb,input wire[3:0]c_k_wr_done,
 input wire[3:0]c_kr_v,output wire[3:0]c_kr_rdy,input wire[67:0]c_kr_tag,input wire[15:0]c_kr_beat,input wire[1023:0]c_kr_data,
 input wire vm_v,vm_bank,input wire[15:0]vm_epoch,input wire[14:0]vm_row,input wire[3:0]vm_col,
 input wire wbw_v,input wire[29:0]wbw_base,input wire[11:0]wbw_total,
 input wire[3:0]w_k_v,output wire[3:0]w_k_rdy,input wire[119:0]w_k_addr,input wire[1023:0]w_k_wdata,output wire[3:0]w_k_wr_done,
 output wire[3:0]fill_v,output wire[3:0]fill_bank,output wire[23:0]fill_slot,output wire[63:0]fill_epoch,output wire[1023:0]fill_data,
 output wire fault
);
 reg srst_q,hrst_q;
 always @(posedge stream_clk or negedge stream_rst_n)if(!stream_rst_n)srst_q<=1'b0;else srst_q<=1'b1;
 always @(posedge hbm_clk or negedge hbm_rst_n)if(!hbm_rst_n)hrst_q<=1'b0;else hrst_q<=1'b1;
 wire hrst_c,srst_c,hrst_c0,srst_c0;
 ot_hbm_svc_vmks_rstleaf3 u_hc0(.clk(hbm_clk),.rst_in(hrst_q),.rst_q(hrst_c0));
 ot_hbm_svc_vmks_rstleaf3 u_hc1(.clk(hbm_clk),.rst_in(hrst_c0),.rst_q(hrst_c));
 ot_hbm_svc_vmks_rstleaf3 u_sc0(.clk(stream_clk),.rst_in(srst_q),.rst_q(srst_c0));
 ot_hbm_svc_vmks_rstleaf3 u_sc1(.clk(stream_clk),.rst_in(srst_c0),.rst_q(srst_c));
 reg[2:0]sm_s,sm_h;
 always @(posedge stream_clk)sm_s<=((MUT==5)||(MUT==8))?3'd0:sm_stream;
 always @(posedge hbm_clk)sm_h<=((MUT==5)||(MUT==7))?3'd0:sm_hbm;
 wire take_cmd,take_wb;wire[35:0]cmd_q;wire[31:0]wn;wire[29:0]wc_base;wire[30:0]wend_q;wire[3:0]norm_l,hfault_l;
 reg[3:0]norm_q,hf_q,take_c_q,take_w_q;
 ot_hbm_svc_vmks_ctl #(.MUT(MUT),.WCNT_STAGE(1),.GUARD(GUARD)) u_ctl(.hbm_clk(hbm_clk),.stream_clk(stream_clk),.hrst_q(hrst_c),.srst_q(srst_c),.sm_s(sm_s),
  .vm_v(vm_v),.vm_bank(vm_bank),.vm_epoch(vm_epoch),.vm_row(vm_row),.vm_col(vm_col),.wbw_v(wbw_v),.wbw_base(wbw_base),.wbw_total(wbw_total),
  .lanes_norm(&norm_q),.lanes_fault(|hf_q),.take_cmd(take_cmd),.take_wb(take_wb),.cmd_q(cmd_q),.wn(wn),.wc_base(wc_base),.wend_q(wend_q),.fault(fault));
 genvar l;
 generate for(l=0;l<4;l=l+1)begin:lane
  wire hrst_l,srst_l;
  ot_hbm_svc_vmks_rstleaf3 u_hl(.clk(hbm_clk),.rst_in(hrst_q),.rst_q(hrst_l));
  ot_hbm_svc_vmks_rstleaf3 u_sl(.clk(stream_clk),.rst_in(srst_q),.rst_q(srst_l));
  (* keep *) reg take_c_k,take_w_k,norm_k,hf_k;
  always @(posedge hbm_clk or negedge hrst_l)
   if(!hrst_l)begin take_c_k<=1'b0;take_w_k<=1'b0;norm_k<=1'b1;hf_k<=1'b0;end
   else begin
    take_c_k<=take_cmd;take_w_k<=take_wb;
    norm_k<=(MUT==23&&l==2)?1'b1:norm_l[l];
    hf_k<=(MUT==24&&l==3)?1'b0:hfault_l[l];
   end
  always @*begin norm_q[l]=norm_k;hf_q[l]=hf_k;take_c_q[l]=take_c_k;take_w_q[l]=take_w_k;end
  ot_hbm_svc_vmks_lane_f3 #(.LANE(l),.MUT(MUT),.KRL1(KRL1)) u_l(.hbm_clk(hbm_clk),.stream_clk(stream_clk),.hrst_l(hrst_l),.srst_l(srst_l),.sm_h(sm_h),
   .take_cmd(take_c_k),.take_wb(take_w_k),.cmd_q(cmd_q),.wn_in(wn[8*l+:8]),.wc_base_in(wc_base),.wend_in(wend_q),
   .g_k_v(g_k_v[l]),.g_k_rdy(g_k_rdy[l]),.g_k_addr(g_k_addr[30*l+:30]),.g_k_len(g_k_len[4*l+:4]),.g_k_tag(g_k_tag[17*l+:17]),
   .g_k_we(g_k_we[l]),.g_k_wdata(g_k_wdata[256*l+:256]),.g_k_wstrb(g_k_wstrb[32*l+:32]),.g_k_wr_done(g_k_wr_done[l]),
   .g_kr_v(g_kr_v[l]),.g_kr_rdy(g_kr_rdy[l]),.g_kr_tag(g_kr_tag[17*l+:17]),.g_kr_beat(g_kr_beat[4*l+:4]),.g_kr_data(g_kr_data[256*l+:256]),
   .c_k_v(c_k_v[l]),.c_k_rdy(c_k_rdy[l]),.c_k_addr(c_k_addr[30*l+:30]),.c_k_len(c_k_len[4*l+:4]),.c_k_tag(c_k_tag[17*l+:17]),
   .c_k_we(c_k_we[l]),.c_k_wdata(c_k_wdata[256*l+:256]),.c_k_wstrb(c_k_wstrb[32*l+:32]),.c_k_wr_done(c_k_wr_done[l]),
   .c_kr_v(c_kr_v[l]),.c_kr_rdy(c_kr_rdy[l]),.c_kr_tag(c_kr_tag[17*l+:17]),.c_kr_beat(c_kr_beat[4*l+:4]),.c_kr_data(c_kr_data[256*l+:256]),
   .w_k_v(w_k_v[l]),.w_k_rdy(w_k_rdy[l]),.w_k_addr(w_k_addr[30*l+:30]),.w_k_wdata(w_k_wdata[256*l+:256]),.w_k_wr_done(w_k_wr_done[l]),
   .fill_v(fill_v[l]),.fill_bank(fill_bank[l]),.fill_slot(fill_slot[6*l+:6]),.fill_epoch(fill_epoch[16*l+:16]),.fill_data(fill_data[256*l+:256]),
   .norm(norm_l[l]),.hfault(hfault_l[l]));
 end endgenerate
endmodule
`default_nettype wire
