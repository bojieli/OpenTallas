`timescale 1ns/1ps
`default_nettype none
// HBM-WBK2 2026-10-20: structural successor of ot_hbm_svc_wb_cutthrough_cdc for the d4g quadrant write-back port
// ot_hbm_svc_wb_kport_q (H.STA.BLK.5).  Route hbm_wbk_ql_1019-ql1 was cancelled: its mapped netlist had 1,411 drivers
// above 32 loads (max 1,696) and synthesis enumerated 5.7M CDC pairs, because every hbm-side K port selected from all 32
// cross-domain FIFO heads through a one-cycle, storage-dependent (fifo_pc from the head address) 32-way mux, the
// payload crossed in 288-b x 4 flop FIFOs (one read pointer bit -> 1,156 mux loads) and every control register fanned
// out to all 32 lanes.
//
// WHERE THE CLOCK CROSSING IS.  The reviewed CDC policy (tools/ref_tile/gray_fifo_cdc_constraints.py) admits only
// reviewed flop FIFOs and single-clock macros (a declared macro must have exactly ONE Liberty clock pin), so a
// dual-clock payload SRAM is not admissible today.  This core therefore keeps the payload SRAMs, the copy engine and the
// lane -> PC crossbar in the stream family and crosses only the per-PC output streams, each through nine reviewed
// ot_link_afifo FIFOs of <= 32 bits (8 x 32 data + 29-b ordinal) with kept read-pointer copies (RCOPY = 4: one copy
// per 8 data bits).  Each PC's nine slices are written on the same edge and popped on the same hbm edge (a pop needs
// all nine non-empty), so a sector is reassembled exactly.  The hbm side is per PC: FIFO heads -> a 32-b-sliced
// two-entry pin skid (the K pins) and the outstanding/ack accounting.
//
// STREAM SIDE (stream_clk family; payload SRAMs on stream_fifo_clk[c], per-PC FIFO write sides on stream_fifo_clk[k]).
//  Fill: as the master (reservation, fill start check, 8 sectors/edge, sector-id checks, complete-row watermark,
//   fill_done on the same edge as the master).  Lane l (block-relative ordinal mod 32) lives in SRAM column c = l[2:1]:
//   wd slot s writes only column s/2, so the DMA bits of a slot travel to one column only.  The fill FSM is held in
//   five KEPT copies (one per column + the control copy), each driven by its own kept fill_start pin copy.
//  Copy: per lane a row pointer rp and a registered head-PC one-hot hpc (computed from base + row*32 + lane, never
//   from storage) loaded with the SRAM read (the SRAM output register holds the head word).  Per PC a 32-way lowest-
//   lane arbiter over the registered hpc bits, gated by a credit counter of the PC's FIFO (count of granted, not yet
//   freed entries <= depth: the FIFO can never be full on a write).  The grant is REGISTERED as a one-hot lane select per
//   (PC, 32-b data slice) in kept arrays (32 loads each), together with the granted row/lane; the crossbar is
//   AND-OR(select, SRAM word) into a registered stage xr (the mid-tile relay of the lane -> PC wires), then the FIFO.
//   Address = (base - 32) + {granted rp, lane}.
// HBM SIDE: a PC pops its nine slices into its pin skid when the block's meta token is active, all nine are
//   non-empty, the skid has room and fewer than 64 writes are outstanding; completions are counted to the block total
//   from the meta FIFO and acknowledged through the ack FIFO (true completion, as the master).
// RESETS: reset_both -> one ot_reset_sync per clock root (reviewed) -> ot_wbk2_rst_tree: kept two-level relay (async
//   assert, release through two registered stages) with <= 16 loads per relay flop and one leaf per <= 32 reset pins.
// TIMING vs the master: identical on the DMA/stream pins (fill_done, done_v from the ack, reservation, ownership);
//   the copy path adds registered stages (start +2, head grant +1, select +1, relay +1 stream edges per sector) which
//   the bench measures as the block fence (lanes/HBM-WBK2.md).  Reservation epoch/base/total are stored one edge after
//   the reservation (kept write-enable copies); the DMA protocol starts a fill >= 10 edges after the reservation.
// MUT (bench only): 5 = data slice 3 of every PC selects lane l^1 (wrong word), 6 = lanes read rows up to the block
//   total instead of the committed watermark (cut-through race), 8 = arbiter ignores the FIFO credit (overflow fault).

// Kept two-level reset relay: rst_n_in (an ot_reset_sync output) clears N1 = ceil(N/16) level-1 flops, each of which
// clears <= 16 leaves.  Assertion is asynchronous through both levels; release takes two clk edges.
module ot_wbk2_rst_tree #(parameter integer N=1)(input wire clk,input wire rst_n_in,output wire [N-1:0] rst_n);
 localparam integer N1=(N+15)/16;
 (* keep="true",dont_touch="true" *) reg l1 [0:N1-1];
 (* keep="true",dont_touch="true" *) reg l2 [0:N-1];
 genvar i;
 generate for(i=0;i<N1;i=i+1)begin:g1
  always @(posedge clk or negedge rst_n_in) if(!rst_n_in) l1[i]<=1'b0; else l1[i]<=1'b1;
 end
 for(i=0;i<N;i=i+1)begin:g2
  always @(posedge clk or negedge l1[i/16]) if(!l1[i/16]) l2[i]<=1'b0; else l2[i]<=1'b1;
  assign rst_n[i]=l2[i];
 end endgenerate
endmodule

// Two-entry pin skid in 32-b slices (last slice LASTW bits), each slice with its own kept head/tail valid, so no
// control net drives more than one slice's 32 data muxes.  in_r = !tail; out_v = head valid; out_r may be a raw pin.
module ot_wbk2_skid #(parameter integer NS=9, parameter integer LASTW=30)(
 input wire clk,rst_n,input wire in_v,output wire in_r,input wire [32*(NS-1)+LASTW-1:0] in_data,
 output wire out_v,input wire out_r,output wire [32*(NS-1)+LASTW-1:0] out_data
);
 (* keep="true",dont_touch="true" *) reg hv [0:NS-1];
 (* keep="true",dont_touch="true" *) reg tv [0:NS-1];
 assign in_r=!tv[0];assign out_v=hv[0];
 genvar s;
 generate for(s=0;s<NS;s=s+1)begin:g_s
  localparam integer B=(s==NS-1)?LASTW:32;
  reg [B-1:0] h,t;
  wire push=in_v&&!tv[s],pop=hv[s]&&out_r;
  assign out_data[32*s+:B]=h;
  always @(posedge clk or negedge rst_n)
   if(!rst_n)begin hv[s]<=1'b0;tv[s]<=1'b0;end
   else case({push,pop})
    2'b10:if(!hv[s])hv[s]<=1'b1;else tv[s]<=1'b1;
    2'b01:begin hv[s]<=tv[s];tv[s]<=1'b0;end
    2'b11:begin hv[s]<=1'b1;tv[s]<=1'b0;end
    default:;
   endcase
  always @(posedge clk)begin
   if(push&&(!hv[s]||pop))h<=in_data[32*s+:B];
   else if(pop&&tv[s])h<=t;
   if(push&&hv[s]&&!pop)t<=in_data[32*s+:B];
  end
 end endgenerate
endmodule

module ot_hbm_svc_wb_kq2_core #(parameter integer FAW=3, parameter integer MUT=0)(
 input wire stream_clk,hbm_clk,input wire [3:0] stream_fifo_clk,
 input wire srst_in_n,hrst_in_n,                  // landed port resets (one per domain)
 output wire [1:0] kp_rst_n,                      // stream-family reset leaves for the wrapper's control registers
 // reservation / fill (stream_clk; the wrapper's pin flops; fill_start and fill_start_bank as kept pin copies)
 input wire reserve_v,output wire reserve_ready,input wire reserve_bank,
 input wire [15:0] reserve_epoch,input wire [31:0] reserve_base,input wire [11:0] reserve_total,
 input wire [6:0] fill_start_c,input wire [2:0] fill_bank_c,input wire [15:0] fill_start_epoch,input wire [2311:0] wd,
 output reg fill_done,done_v,done_bank,output reg [15:0] done_epoch,output reg [11:0] done_sectors,
 output wire [1:0] bank_owned,output wire fault,
 // K write ports (hbm_clk): single-beat full-strobe writes, real sector address fold(o, q_h)
 input wire q_h,
 output wire [15:0] w_k_v,input wire [15:0] w_k_rdy,output wire [479:0] w_k_addr,output wire [4095:0] w_k_wdata,
 input wire [15:0] w_k_wr_done
);
 localparam integer D=1<<FAW;
 localparam [32:0] SPACE_END=33'h020000000;          // quadrant ordinal space (2^29)
 localparam integer NS=25, NR=38, NH=165;
 // ------------------------------------------------------------------------------------------------ resets
 wire reset_both=srst_in_n&&hrst_in_n;
 wire srs,hrs;wire [3:0] rrs;
 ot_reset_sync u_stream_reset(.clk(stream_clk),.async_rst_n(reset_both),.sync_rst_n(srs));
 ot_reset_sync u_hbm_reset(.clk(hbm_clk),.async_rst_n(reset_both),.sync_rst_n(hrs));
 wire [NS-1:0] sl;wire [NH-1:0] hl;wire [NR-1:0] rl [0:3];
 ot_wbk2_rst_tree #(.N(NS)) u_srt(.clk(stream_clk),.rst_n_in(srs),.rst_n(sl));
 ot_wbk2_rst_tree #(.N(NH)) u_hrt(.clk(hbm_clk),.rst_n_in(hrs),.rst_n(hl));
 genvar gk;
 generate for(gk=0;gk<4;gk=gk+1)begin:g_rr
  ot_reset_sync u_root_reset(.clk(stream_fifo_clk[gk]),.async_rst_n(reset_both),.sync_rst_n(rrs[gk]));
  ot_wbk2_rst_tree #(.N(NR)) u_rrt(.clk(stream_fifo_clk[gk]),.rst_n_in(rrs[gk]),.rst_n(rl[gk]));
 end endgenerate
 assign kp_rst_n=sl[24:23];
 wire sl_ok=sl[22];                                   // stream side out of reset (a leaf flop)
 wire roots_ready=rl[0][37]&&rl[1][37]&&rl[2][37]&&rl[3][37];
 wire hl_ok=hl[164];
 // ------------------------------------------------------------------------------------------------ stream state
 reg [1:0] allocated,started,staged;reg [15:0] epoch[0:1];reg [29:0] base[0:1];reg [11:0] total[0:1];
 reg [11:0] committed[0:1];
 reg copy_active;(* keep="true",dont_touch="true" *) reg copy_bank_c [0:2];
 reg stream_sticky,hbm_sticky;(* async_reg = "true" *) reg hf1,hf2,sf1,sf2;
 assign fault=stream_sticky||hf2;assign bank_owned=allocated;
 // kept copies of the fault (1-edge lag) for the fill copies and the checker
 (* keep="true",dont_touch="true" *) reg flt_c [0:4];
 integer fi;always @(posedge stream_clk)for(fi=0;fi<5;fi=fi+1)flt_c[fi]<=fault;
 // fill FSM: kept copies k = 0..3 (SRAM column k) and 4 (control)
 (* keep="true",dont_touch="true" *) reg filling_c [0:4];
 (* keep="true",dont_touch="true" *) reg fbank_c [0:4];
 (* keep="true",dont_touch="true" *) reg [8:0] ord_c [0:4];   // ordinal[11:3]
 reg [29:0] exp_s;reg [11:0] rem;                    // expected sector of slot 0, remaining sectors of the fill
 wire last=rem<=12'd8;
 wire fsb0=fill_bank_c[0],fsb1=fill_bank_c[1],fsb2=fill_bank_c[2];
 wire ok_fill=sl_ok&&roots_ready&&!filling_c[4]&&allocated[fsb0]&&!started[fsb0]&&epoch[fsb0]==fill_start_epoch;
 wire [6:0] fill_go;
 genvar gi;
 generate for(gi=0;gi<7;gi=gi+1)begin:g_fg assign fill_go[gi]=fill_start_c[gi]&&ok_fill; end endgenerate
 integer k,s;
 always @(posedge stream_clk or negedge sl[0])
  if(!sl[0])for(k=0;k<5;k=k+1)filling_c[k]<=1'b0;
  else for(k=0;k<5;k=k+1)begin
   if(fill_go[k])filling_c[k]<=1'b1;
   else if(filling_c[k]&&!flt_c[k]&&last)filling_c[k]<=1'b0;
  end
 always @(posedge stream_clk)for(k=0;k<5;k=k+1)begin
  if(fill_go[k])begin fbank_c[k]<=fsb0;ord_c[k]<=9'd0;end
  else if(filling_c[k]&&!flt_c[k])ord_c[k]<=ord_c[k]+9'd1;
 end
 always @(posedge stream_clk)begin
  exp_s<=fill_go[5]?base[fsb1]:exp_s+30'd8;
  rem<=fill_go[6]?total[fsb2]:rem-12'd8;
 end
 // reservation data: stored one edge after the reservation under kept write-enable copies (epoch / base / total)
 reg [15:0] rsv_ep_q;reg [29:0] rsv_base_q;reg [11:0] rsv_tot_q;
 (* keep="true",dont_touch="true" *) reg [1:0] rsv_we [0:2];
 wire [32:0] reserve_end={3'b0,reserve_base[29:0]}+{21'd0,reserve_total};
 assign reserve_ready=sl_ok&&roots_ready&&!allocated[reserve_bank]&&!fault&&reserve_total!=0&&reserve_total<=12'd2048&&
  reserve_base[31:30]==2'b00&&reserve_end<=SPACE_END;
 wire res_acc=reserve_v&&reserve_ready;
 integer ri;
 always @(posedge stream_clk)begin
  rsv_ep_q<=reserve_epoch;rsv_base_q<=reserve_base[29:0];rsv_tot_q<=reserve_total;
  for(ri=0;ri<3;ri=ri+1)rsv_we[ri]<={res_acc&&reserve_bank,res_acc&&!reserve_bank};
  for(ri=0;ri<2;ri=ri+1)begin
   if(rsv_we[0][ri])epoch[ri]<=rsv_ep_q;
   if(rsv_we[1][ri])base[ri]<=rsv_base_q;
   if(rsv_we[2][ri])total[ri]<=rsv_tot_q;
  end
 end
 // copy control
 wire [1:0] copy_elig={staged[1]&&committed[1]!=0,staged[0]&&committed[0]!=0};
 wire meta_full,meta_empty,ack_full,ack_empty;wire [12:0] meta_rdata,ack_rdata;
 wire start_copy=sl_ok&&roots_ready&&!copy_active&&(|copy_elig)&&!meta_full&&!fault;
 wire choose_bank=!copy_elig[0];
 wire ack_re=sl_ok&&!ack_empty&&!fault;
 wire cb0=copy_bank_c[0],cb1=copy_bank_c[1],cb2=copy_bank_c[2];
 wire [7:0] wd_v;
 generate for(gi=0;gi<8;gi=gi+1)begin:g_wv assign wd_v[gi]=wd[289*gi+288]; end endgenerate
 wire [8:0] ord_n=ord_c[4]+9'd1;
 wire prog=filling_c[4]&&!flt_c[4];
 wire ovf_any;
 always @(posedge stream_clk or negedge sl[0])begin
  if(!sl[0])begin
   allocated<=0;started<=0;staged<=0;copy_active<=0;stream_sticky<=0;hf1<=0;hf2<=0;fill_done<=0;done_v<=0;
  end else begin
   hf1<=hbm_sticky;hf2<=hf1;fill_done<=1'b0;done_v<=1'b0;
   if(reserve_v)begin
    if(!reserve_ready)stream_sticky<=1'b1;
    else begin allocated[reserve_bank]<=1'b1;started[reserve_bank]<=1'b0;staged[reserve_bank]<=1'b0;end
   end
   if(fill_start_c[4])begin
    if(!ok_fill)stream_sticky<=1'b1;
    else begin started[fsb2]<=1'b1;staged[fsb2]<=1'b1;end
   end
   if(prog)begin
    for(s=0;s<8;s=s+1)begin
     if(rem>12'(s))begin
      if(!wd_v[s]||wd[289*s+256+:32]!={2'b00,exp_s+30'(s)})stream_sticky<=1'b1;
     end else if(wd_v[s])stream_sticky<=1'b1;
    end
    if(last)fill_done<=1'b1;
   end else if(!flt_c[4]&&(|wd_v))stream_sticky<=1'b1;
   if(ovf_any)stream_sticky<=1'b1;
   if(start_copy)begin copy_active<=1'b1;staged[choose_bank]<=1'b0;end
   if(ack_re)begin
    if(!copy_active||ack_rdata[12]!=cb2||ack_rdata[11:0]!=total[cb2])stream_sticky<=1'b1;
    else begin allocated[cb2]<=1'b0;copy_active<=1'b0;done_v<=1'b1;end
   end
  end
 end
 always @(posedge stream_clk)begin
  for(k=0;k<2;k=k+1)begin
   if(res_acc&&reserve_bank==k[0])committed[k]<=12'd0;
   else if(prog&&fbank_c[4]==k[0])committed[k]<=last?total[k]:{ord_n[8:2],5'd0};
  end
  if(start_copy)for(k=0;k<3;k=k+1)copy_bank_c[k]<=choose_bank;
  if(ack_re)begin done_bank<=cb2;done_epoch<=epoch[cb2];done_sectors<=ack_rdata[11:0];end
 end
 // per-column copy controls (kept, 1-edge lag)
 (* keep="true",dont_touch="true" *) reg st_r [0:7];         // copy start, two per column (lanes l[4] = 0 / 1)
 (* keep="true",dont_touch="true" *) reg cp_on [0:3];
 (* keep="true",dont_touch="true" *) reg cp_bank [0:3];
 (* keep="true",dont_touch="true" *) reg [11:0] cp_commit [0:3];
 (* keep="true",dont_touch="true" *) reg [14:0] cp_base_lo [0:3];
 (* keep="true",dont_touch="true" *) reg [28:0] cp_basem [0:3];   // base - 32, per PC group
 wire [11:0] commit_cb=(MUT==6)?total[cb0]:committed[cb0];
 wire [29:0] base_cb=base[cb1];
 wire [28:0] basem_cb=base_cb[28:0]-29'd32;
 always @(posedge stream_clk or negedge sl[1])
  if(!sl[1])for(k=0;k<8;k=k+1)begin st_r[k]<=1'b0;if(k<4)cp_on[k]<=1'b0;end
  else for(k=0;k<8;k=k+1)begin
   st_r[k]<=start_copy;
   if(k<4)cp_on[k]<=copy_active&&!start_copy&&!st_r[2*k]&&!fault;
  end
 always @(posedge stream_clk)for(k=0;k<4;k=k+1)begin
  cp_bank[k]<=cb0;cp_commit[k]<=commit_cb;cp_base_lo[k]<=base_cb[14:0];cp_basem[k]<=basem_cb;
 end
 // ------------------------------------------------------------------------------------------------ lanes
 wire [15:0] hpc_w [0:31];wire [6:0] rp_w [0:31];wire [255:0] rdl [0:31];
 wire [31:0] g_w [0:15];
 genvar gl,gp,gf;
 generate for(gl=0;gl<32;gl=gl+1)begin:g_lane
  localparam integer C=(gl>>1)&3;           // SRAM column: l[2:1]
  localparam integer SL=gl&7;               // DMA slot
  localparam integer PH=(gl>>3)&3;          // fill phase: ordinal[4:3]
  localparam integer LEAF=4+gl/2;
  reg [6:0] rp;reg [15:0] hpc;
  wire [15:0] gcol;
  for(gp=0;gp<16;gp=gp+1)begin:g_gc assign gcol[gp]=g_w[gp][gl]; end
  wire rd_ok={rp,5'(gl)}<cp_commit[C];
  wire r_ce=cp_on[C]&&(hpc==16'd0)&&rd_ok;
  wire [14:0] hs=cp_base_lo[C]+{3'b0,rp,5'(gl)};
  wire [3:0] pcn=hs[5:2]^hs[9:6]^hs[14:11];
  always @(posedge stream_clk)if(st_r[2*C+(gl>>4)])rp<=7'd0;else if(r_ce)rp<=rp+7'd1;
  always @(posedge stream_clk or negedge sl[LEAF])
   if(!sl[LEAF])hpc<=16'd0;
   else if(r_ce)hpc<=16'd1<<pcn;
   else hpc<=hpc&~gcol;
  assign hpc_w[gl]=hpc;assign rp_w[gl]=rp;
  wire fw=filling_c[C]&&!flt_c[C];
  ot_sram_1r1w_128x256_m1_r2c2 u_payload(
   .clk(stream_fifo_clk[C]),.r_ce_in(r_ce),.r_addr_in({cp_bank[C],rp[5:0]}),.rd_out(rdl[gl]),
   .w_ce_in(fw&&ord_c[C][1:0]==2'(PH)&&wd_v[SL]),.w_addr_in({fbank_c[C],ord_c[C][7:2]}),
   .wd_in(wd[SL*289+:256]),.w_mask_in({256{1'b1}}),
   .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 end endgenerate
 // ------------------------------------------------------------------------------------------------ arbiters, credit
 wire [FAW:0] wfreed [0:15];wire [143:0] ovf;
 assign ovf_any=|ovf;
 generate for(gp=0;gp<16;gp=gp+1)begin:g_arb
  wire [31:0] req;
  for(gl=0;gl<32;gl=gl+1)begin:g_rq assign req[gl]=hpc_w[gl][gp]; end
  reg [FAW:0] cnt;
  wire ok=(MUT==8)||(cnt<(FAW+1)'(D));
  assign g_w[gp]=ok?(req&(~req+32'd1)):32'd0;
  wire gany=ok&&(|req);
  always @(posedge stream_clk or negedge sl[2+gp/8])
   if(!sl[2+gp/8])cnt<=0;else cnt<=cnt+(FAW+1)'(gany)-wfreed[gp];
 end endgenerate
 // ------------------------------------------------------------------------------------------------ select, crossbar, FIFOs
 (* keep="true",dont_touch="true" *) reg [31:0] sel_q [0:127];     // [pc*8+slice] one-hot lane select
 wire [31:0] fifo_wd [0:143];wire [143:0] fifo_empty;wire [31:0] fifo_rd [0:143];
 wire [15:0] pop;
 generate for(gp=0;gp<16;gp=gp+1)begin:g_pc
  localparam integer K=gp/4;
  wire fclk=stream_fifo_clk[K];
  reg xv1,xv2;reg [6:0] selrp;reg [4:0] sellane;reg [28:0] xr_a;
  reg [6:0] rpm;reg [4:0] enc;integer j;
  always @*begin
   rpm=0;enc=0;
   for(j=0;j<32;j=j+1)begin
    if(g_w[gp][j])rpm=rpm|rp_w[j];
    if(g_w[gp][j])enc=enc|5'(j);
   end
  end
  always @(posedge fclk or negedge rl[K][36])if(!rl[K][36])begin xv1<=0;xv2<=0;end else begin xv1<=|g_w[gp];xv2<=xv1;end
  always @(posedge fclk)begin selrp<=rpm;sellane<=enc;xr_a<=cp_basem[K]+{17'd0,selrp,sellane};end
  for(gf=0;gf<8;gf=gf+1)begin:g_sl
   wire [31:0] gsrc;
   for(gl=0;gl<32;gl=gl+1)begin:g_m assign gsrc[gl]=(MUT==5&&gf==3)?g_w[gp][gl^1]:g_w[gp][gl]; end
   always @(posedge fclk)sel_q[gp*8+gf]<=gsrc;
   reg [31:0] xd,xr_d;integer m;
   always @*begin xd=0;for(m=0;m<32;m=m+1)if(sel_q[gp*8+gf][m])xd=xd|rdl[m][32*gf+:32];end
   always @(posedge fclk)xr_d<=xd;
   assign fifo_wd[gp*9+gf]=xr_d;
  end
  assign fifo_wd[gp*9+8]={3'b0,xr_a};
  for(gf=0;gf<9;gf=gf+1)begin:g_f
   localparam integer W=(gf==8)?29:32;
   wire [FAW:0] wf;wire [W-1:0] rdat;wire fe;
   ot_link_afifo #(.W(W),.AW(FAW),.SYNC(2),.RCOPY(4)) u_fifo(
    .wclk(fclk),.wrst_n(rl[K][(gp%4)*9+gf]),.wr(xv2),.wdata(fifo_wd[gp*9+gf][W-1:0]),.wfull(),.wfreed(wf),.ovf(ovf[gp*9+gf]),
    .rclk(hbm_clk),.rrst_n(hl[gp*9+gf]),.rd(pop[gp]),.rempty(fe),.rdata(rdat),.rcount());
   assign fifo_empty[gp*9+gf]=fe;assign fifo_rd[gp*9+gf]=32'(rdat);
   if(gf==0)begin:g_wf assign wfreed[gp]=wf; end
  end
 end endgenerate
 // ------------------------------------------------------------------------------------------------ meta / ack tokens
 wire meta_re,ack_we;reg meta_active,ack_pending;reg [12:0] meta_q;reg [11:0] ack_count;
 ot_link_afifo #(.W(13),.AW(2),.SYNC(2),.RCOPY(2)) u_meta(
  .wclk(stream_clk),.wrst_n(sl[20]),.wr(start_copy),.wdata({choose_bank,total[choose_bank]}),.wfull(meta_full),.wfreed(),.ovf(),
  .rclk(hbm_clk),.rrst_n(hl[160]),.rd(meta_re),.rempty(meta_empty),.rdata(meta_rdata),.rcount());
 ot_link_afifo #(.W(13),.AW(2),.SYNC(2),.RCOPY(2)) u_ack(
  .wclk(hbm_clk),.wrst_n(hl[161]),.wr(ack_we),.wdata(meta_q),.wfull(ack_full),.wfreed(),.ovf(),
  .rclk(stream_clk),.rrst_n(sl[21]),.rd(ack_re),.rempty(ack_empty),.rdata(ack_rdata),.rcount());
 // ------------------------------------------------------------------------------------------------ hbm side
 wire hbm_fault=hbm_sticky||sf2||!hl_ok;
 assign meta_re=!meta_active&&!meta_empty&&!hbm_fault;
 assign ack_we=ack_pending&&!ack_full&&!hbm_fault;
 reg [15:0] done_q;
 (* keep="true",dont_touch="true" *) reg mon_c [0:3];
 wire [15:0] spurious;
 always @(posedge hbm_clk or negedge hl[163])
  if(!hl[163])begin done_q<=0;for(k=0;k<4;k=k+1)mon_c[k]<=1'b0;end
  else begin done_q<=w_k_wr_done;for(k=0;k<4;k=k+1)mon_c[k]<=meta_active&&!ack_pending&&!hbm_fault;end
 generate for(gp=0;gp<16;gp=gp+1)begin:g_hk
  wire [8:0] fe=fifo_empty[gp*9+:9];
  wire ne_all=!(|fe);
  reg [6:0] cnt_h;reg pop_q;
  wire in_r;
  wire [6:0] cnt_n=cnt_h+7'(pop_q);
  assign pop[gp]=mon_c[gp/4]&&ne_all&&in_r&&(cnt_n<7'd64);
  wire [28:0] o=fifo_rd[gp*9+8][28:0];
  wire [285:0] sk_in;
  for(gf=0;gf<8;gf=gf+1)begin:g_d assign sk_in[32*gf+:32]=fifo_rd[gp*9+gf]; end
  assign sk_in[285:256]={o[28:6],q_h^o[10]^o[15],o[5:0]};
  wire [285:0] sk_out;
  ot_wbk2_skid #(.NS(9),.LASTW(30)) u_k(.clk(hbm_clk),.rst_n(hl[144+gp]),.in_v(pop[gp]),.in_r(in_r),.in_data(sk_in),
   .out_v(w_k_v[gp]),.out_r(w_k_rdy[gp]),.out_data(sk_out));
  assign w_k_wdata[256*gp+:256]=sk_out[255:0];assign w_k_addr[30*gp+:30]=sk_out[285:256];
  always @(posedge hbm_clk or negedge hl[144+gp])
   if(!hl[144+gp])begin cnt_h<=0;pop_q<=0;end
   else begin pop_q<=pop[gp];cnt_h<=cnt_n-7'(done_q[gp]);end
  assign spurious[gp]=done_q[gp]&&cnt_n==7'd0;
 end endgenerate
 reg [4:0] acks;integer a;
 always @*begin acks=0;for(a=0;a<16;a=a+1)acks=acks+5'(done_q[a]);end
 always @(posedge hbm_clk or negedge hl[162])begin
  if(!hl[162])begin
   sf1<=0;sf2<=0;hbm_sticky<=0;meta_active<=0;ack_pending<=0;ack_count<=0;
  end else begin
   sf1<=stream_sticky;sf2<=sf1;
   if(meta_re)begin meta_active<=1'b1;ack_count<=12'd0;ack_pending<=1'b0;end
   if(|spurious)hbm_sticky<=1'b1;
   if(meta_active&&!hbm_fault)begin
    if(acks!=0)begin
     ack_count<=ack_count+12'(acks);
     if(ack_count+12'(acks)>meta_q[11:0])hbm_sticky<=1'b1;
     if(ack_count+12'(acks)==meta_q[11:0])ack_pending<=1'b1;
    end
   end else if(|done_q)hbm_sticky<=1'b1;
   if(ack_we)begin ack_pending<=1'b0;meta_active<=1'b0;end
  end
 end
 always @(posedge hbm_clk)if(meta_re)meta_q<=meta_rdata;
endmodule
`default_nettype wire
