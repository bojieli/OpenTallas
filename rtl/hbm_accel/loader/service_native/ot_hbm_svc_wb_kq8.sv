`timescale 1ns/1ps
`default_nettype none
// HBM-WBK8 2026-10-20: census-safe successor of ot_hbm_svc_wb_kq2_core for ot_hbm_svc_wb_kport_q (H.STA.BLK.5).
// kq2's mapped netlist (CODEX-HBM preflight e8d69c19d) had 2,219 drivers above 32 loads (max 232): the hbm-side pop of a
// PC drove all nine 32-b crossing FIFOs plus the nine skid slices; every 32-b reviewed ot_link_afifo (AW 3, RCOPY 4) had
// read-pointer copies driving 65 mux loads, write-entry enables driving 56 and a read enable on 20 flops; w_k_rdy drove
// 39..49 loads; several bank selects fanned out to 30-bit muxes.  Rules used here (ASAP7 maps every enabled flop as an
// AO/OAI mux, i.e. ~1.75 loads per enabled bit):
//   * every crossing FIFO is a reviewed ot_link_afifo of <= 16 bits, AW = FAW (2: 4 entries), RCOPY 3 (<= 6 bits per
//     read-pointer copy, read enable on 12 flops);
//   * PP = 1: each 16-b slice crosses through TWO such FIFOs written / read alternately (ping-pong), so a PC still has
//     8 crossing entries (kq2 FAW=3 rate); PP = 0 is the single depth-4 FIFO (kq2 FAW=2 rate);
//   * the hbm side pops all 18 slices of a PC in LOCKSTEP from kept REGISTERED pop copies (one per slice), decided one
//     edge ahead from the FIFOs' empty flags (arrivals only add entries) -- no combinational pop fans out;
//   * the K pins come out of a 3-entry one-hot ring per slice; w_k_v is a flop; w_k_rdy drives one AND per slice;
//   * every select / write enable of a wide register is a kept copy serving <= 16 bits.
// FUNCTION, ORDER, PROTOCOL: unchanged vs kq2 (same reservation / fill / watermark / copy / per-PC order / true
// completion ack); the K pins are the same valid/ready single-beat writes.  Added edges (bench-priced): copy start +1
// stream edge (two-level start relay), hbm pop decision +1 hbm edge, per-PC enable +1 hbm edge at block start.
// MUT (bench only): 5 = data slice 3 of every PC selects lane l^1; 6 = lanes read up to the block total (watermark race);
//   8 = arbiter ignores the crossing credit (FIFO overflow -> fault); 9 = (PP=1) data slice 5 never toggles its read
//   FIFO (reads A twice: wrong / stale data); 10 = pops ignore the K ring room (ring overwrite under K back-pressure).

// Kept three-level reset relay (16-ary): async assert through every level, release through three clk edges.
module ot_wbk8_rst_tree #(parameter integer N=1)(input wire clk,input wire rst_n_in,output wire [N-1:0] rst_n);
 localparam integer N1=(N+15)/16, N0=(N1+15)/16;
 (* keep="true",dont_touch="true" *) reg l0 [0:N0-1];
 (* keep="true",dont_touch="true" *) reg l1 [0:N1-1];
 (* keep="true",dont_touch="true" *) reg l2 [0:N-1];
 genvar i;
 generate for(i=0;i<N0;i=i+1)begin:g0
  always @(posedge clk or negedge rst_n_in) if(!rst_n_in) l0[i]<=1'b0; else l0[i]<=1'b1;
 end
 for(i=0;i<N1;i=i+1)begin:g1
  always @(posedge clk or negedge l0[i/16]) if(!l0[i/16]) l1[i]<=1'b0; else l1[i]<=1'b1;
 end
 for(i=0;i<N;i=i+1)begin:g2
  always @(posedge clk or negedge l1[i/16]) if(!l1[i/16]) l2[i]<=1'b0; else l2[i]<=1'b1;
  assign rst_n[i]=l2[i];
 end endgenerate
endmodule

module ot_hbm_svc_wb_kq8_core #(parameter integer FAW=2, parameter integer PP=1, parameter integer MUT=0)(
 input wire stream_clk,hbm_clk,input wire [3:0] stream_fifo_clk,
 input wire srst_in_n,hrst_in_n,                  // landed port resets (one per domain)
 output wire [1:0] kp_rst_n,                      // stream-family reset leaves for the wrapper's control registers
 input wire reserve_v,output wire reserve_ready,input wire reserve_bank,
 input wire [15:0] reserve_epoch,input wire [31:0] reserve_base,input wire [11:0] reserve_total,
 input wire [7:0] fill_start_c,input wire [9:0] fill_bank_c,input wire [15:0] fill_start_epoch,input wire [2311:0] wd,
 output reg fill_done,done_v,output wire [2:0] done_bank,output reg [15:0] done_epoch,output reg [11:0] done_sectors,
 output wire [1:0] bank_owned,output wire fault,
 input wire q_h,
 output wire [15:0] w_k_v,input wire [15:0] w_k_rdy,output wire [479:0] w_k_addr,output wire [4095:0] w_k_wdata,
 input wire [15:0] w_k_wr_done
);
 localparam integer NPP=(PP!=0)?2:1;
 localparam integer DEFF=NPP<<FAW;                   // crossing entries per PC slice
 localparam integer CW=FAW+2;                        // credit counter width (0..DEFF)
 localparam integer NDS=18, NSL=20;                  // 18 data slices (4 x 15 b + 14 x 14 b) + ordinal [14:0] + [28:15]
 // <= 15 b per slice: a reviewed FIFO entry enable / ring enable / toggle mux then drives <= 31 loads
 function automatic integer sw_f(input integer g); sw_f=(g<4)?15:(g<NDS)?14:(g==NDS)?15:14; endfunction
 function automatic integer so_f(input integer g); so_f=(g<4)?15*g:(g<NDS)?60+14*(g-4):(g==NDS)?0:15; endfunction
 localparam integer NFP=NSL*NPP;                     // crossing FIFOs per PC
 localparam [32:0] SPACE_END=33'h020000000;
 // reset leaf maps
 localparam integer NS=29;
 localparam integer XB=4*NFP, NR=XB+13;              // per root: 4 PCs x NFP FIFO write leaves, 4 x 3 slice leaves, ready
 localparam integer NRL=8, NF=16*NFP, HB=NF, HM=HB+16*NRL, NH=HM+7;
 // ------------------------------------------------------------------------------------------------ resets
 wire reset_both=srst_in_n&&hrst_in_n;
 wire srs,hrs;wire [3:0] rrs;
 ot_reset_sync u_stream_reset(.clk(stream_clk),.async_rst_n(reset_both),.sync_rst_n(srs));
 ot_reset_sync u_hbm_reset(.clk(hbm_clk),.async_rst_n(reset_both),.sync_rst_n(hrs));
 wire [NS-1:0] sl;wire [NH-1:0] hl;wire [NR-1:0] rl [0:3];
 ot_wbk8_rst_tree #(.N(NS)) u_srt(.clk(stream_clk),.rst_n_in(srs),.rst_n(sl));
 ot_wbk8_rst_tree #(.N(NH)) u_hrt(.clk(hbm_clk),.rst_n_in(hrs),.rst_n(hl));
 genvar gk;
 generate for(gk=0;gk<4;gk=gk+1)begin:g_rr
  ot_reset_sync u_root_reset(.clk(stream_fifo_clk[gk]),.async_rst_n(reset_both),.sync_rst_n(rrs[gk]));
  ot_wbk8_rst_tree #(.N(NR)) u_rrt(.clk(stream_fifo_clk[gk]),.rst_n_in(rrs[gk]),.rst_n(rl[gk]));
 end endgenerate
 assign kp_rst_n=sl[26:25];
 wire sl_ok=sl[24];
 wire roots_ready=rl[0][NR-1]&&rl[1][NR-1]&&rl[2][NR-1]&&rl[3][NR-1];
 wire hl_ok=hl[HM+4];
 // ------------------------------------------------------------------------------------------------ stream state
 reg [1:0] allocated,started,staged;reg [15:0] epoch[0:1];reg [29:0] base[0:1];reg [11:0] total[0:1];
 reg [11:0] committed[0:1];
 reg copy_active;(* keep="true",dont_touch="true" *) reg copy_bank_c [0:9];
 (* keep="true",dont_touch="true" *) reg dbk [0:2];   // done-bank copies (wrapper: accepted / aepoch / atotal)
 assign done_bank={dbk[2],dbk[1],dbk[0]};
 reg stream_sticky,hbm_sticky;(* async_reg = "true" *) reg hf1,hf2,sf1,sf2;
 assign fault=stream_sticky||hf2;assign bank_owned=allocated;
 (* keep="true",dont_touch="true" *) reg flt_c [0:4];
 integer fi;always @(posedge stream_clk)for(fi=0;fi<5;fi=fi+1)flt_c[fi]<=fault;
 // fill FSM: kept copies k = 0..3 (SRAM column k) and 4 (control)
 (* keep="true",dont_touch="true" *) reg filling_c [0:4];
 (* keep="true",dont_touch="true" *) reg fbank_c [0:4];
 (* keep="true",dont_touch="true" *) reg [8:0] ord_c [0:4];
 reg [14:0] exp_lo,exp_hi;reg [11:0] rem;          // expected sector of slot 0 (two halves), remaining sectors
 wire [29:0] exp_s={exp_hi,exp_lo};
 // last = (rem <= 8), held in kept registered copies computed from rem's next value (exact): 0 fill FSMs, 1 watermark
 (* keep="true",dont_touch="true" *) reg lastq [0:1];
 wire last=lastq[0];
 // fill-bank pin copies: 0 ownership check, 1 epoch check, 2/7 base [7:0]/[14:8], 3/8 base [22:15]/[29:23], 4 total,
 // 5 fill-copy bank, 6 state
 wire fsb0=fill_bank_c[0],fsb1=fill_bank_c[1],fsb2=fill_bank_c[2],fsb3=fill_bank_c[3],fsb4=fill_bank_c[4],
      fsb5=fill_bank_c[5],fsb6=fill_bank_c[6],fsb7=fill_bank_c[7],fsb8=fill_bank_c[8];
 wire ok_fill=sl_ok&&roots_ready&&!filling_c[4]&&allocated[fsb0]&&!started[fsb0]&&epoch[fsb1][7:0]==fill_start_epoch[7:0]&&epoch[fill_bank_c[9]][15:8]==fill_start_epoch[15:8];
 wire [7:0] fill_go;
 genvar gi;
 generate for(gi=0;gi<8;gi=gi+1)begin:g_fg assign fill_go[gi]=fill_start_c[gi]&&ok_fill; end endgenerate
 integer k,s;
 always @(posedge stream_clk or negedge sl[0])
  if(!sl[0])for(k=0;k<5;k=k+1)filling_c[k]<=1'b0;
  else for(k=0;k<5;k=k+1)begin
   if(fill_go[k])filling_c[k]<=1'b1;
   else if(filling_c[k]&&!flt_c[k]&&last)filling_c[k]<=1'b0;
  end
 always @(posedge stream_clk)for(k=0;k<5;k=k+1)begin
  if(fill_go[k])begin fbank_c[k]<=fsb5;ord_c[k]<=9'd0;end
  else if(filling_c[k]&&!flt_c[k])ord_c[k]<=ord_c[k]+9'd1;
 end
 wire [15:0] exp_lo_n={1'b0,exp_lo}+16'd8;
 wire [11:0] rem_n=fill_go[7]?total[fsb4]:rem-12'd8;
 always @(posedge stream_clk)begin
  exp_lo<=fill_go[5]?{base[fsb7][14:8],base[fsb2][7:0]}:exp_lo_n[14:0];
  exp_hi<=fill_go[6]?{base[fsb8][29:23],base[fsb3][22:15]}:exp_hi+15'(exp_lo_n[15]);
  rem<=rem_n;lastq[0]<=rem_n<=12'd8;lastq[1]<=rem_n<=12'd8;
 end
 // reservation data: stored one edge after the reservation under kept write-enable copies (epoch / base lo / hi / total)
 reg [15:0] rsv_ep_q;reg [29:0] rsv_base_q;reg [11:0] rsv_tot_q;
 (* keep="true",dont_touch="true" *) reg [1:0] rsv_we [0:3];
 wire [32:0] reserve_end={3'b0,reserve_base[29:0]}+{21'd0,reserve_total};
 assign reserve_ready=sl_ok&&roots_ready&&!allocated[reserve_bank]&&!fault&&reserve_total!=0&&reserve_total<=12'd2048&&
  reserve_base[31:30]==2'b00&&reserve_end<=SPACE_END;
 wire res_acc=reserve_v&&reserve_ready;
 integer ri;
 always @(posedge stream_clk)begin
  rsv_ep_q<=reserve_epoch;rsv_base_q<=reserve_base[29:0];rsv_tot_q<=reserve_total;
  for(ri=0;ri<4;ri=ri+1)rsv_we[ri]<={res_acc&&reserve_bank,res_acc&&!reserve_bank};
  for(ri=0;ri<2;ri=ri+1)begin
   if(rsv_we[0][ri])epoch[ri]<=rsv_ep_q;
   if(rsv_we[1][ri])base[ri][14:0]<=rsv_base_q[14:0];
   if(rsv_we[3][ri])base[ri][29:15]<=rsv_base_q[29:15];
   if(rsv_we[2][ri])total[ri]<=rsv_tot_q;
  end
 end
 // copy control
 wire [1:0] copy_elig={staged[1]&&committed[1]!=0,staged[0]&&committed[0]!=0};
 wire meta_full,meta_empty,ack_full,ack_empty;wire [12:0] meta_rdata,ack_rdata;
 wire start_copy=sl_ok&&roots_ready&&!copy_active&&(|copy_elig)&&!meta_full&&!fault;
 // meta FIFO write strobes from kept copy_active copies (each strobe feeds one reviewed FIFO's write side)
 (* keep="true",dont_touch="true" *) reg cac [0:1];
 wire start_copy_h=sl_ok&&roots_ready&&!cac[1]&&(|copy_elig)&&!meta_full&&!fault;
 wire start_copy_l=sl_ok&&roots_ready&&!cac[0]&&(|copy_elig)&&!meta_full&&!fault;
 wire choose_bank=!copy_elig[0];
 wire ack_re=sl_ok&&!ack_empty&&!fault;
 wire copy_active_n;
 // copy-bank copies: 0 watermark, 1 base lo, 2 ack check / ownership, 3 base hi, 4 epoch
 wire cb0=copy_bank_c[0],cb1=copy_bank_c[1],cb2=copy_bank_c[2],cb3=copy_bank_c[3],cb4=copy_bank_c[4];
 wire ack_ok=ack_rdata[12]==cb2&&ack_rdata[11:0]=={total[copy_bank_c[9]][11:6],total[cb2][5:0]};
 wire [7:0] wd_v;
 generate for(gi=0;gi<8;gi=gi+1)begin:g_wv assign wd_v[gi]=wd[289*gi+288]; end endgenerate
 wire [8:0] ord_n=ord_c[4]+9'd1;
 wire prog=filling_c[4]&&!flt_c[4];
 wire ovf_any;
 // sector-id check: slot s carries {2'b00, exp_s + s}  <=>  id_s - s == {2'b00, exp_s}
 wire [7:0] id_bad;
 generate for(gi=0;gi<8;gi=gi+1)begin:g_id
  wire [31:0] idm=wd[289*gi+256+:32]-32'(gi);
  assign id_bad[gi]=idm!={2'b00,exp_s};
 end endgenerate
 always @(posedge stream_clk or negedge sl[0])begin
  if(!sl[0])begin
   allocated<=0;started<=0;staged<=0;copy_active<=0;cac[0]<=0;cac[1]<=0;stream_sticky<=0;hf1<=0;hf2<=0;fill_done<=0;done_v<=0;
  end else begin
   hf1<=hbm_sticky;hf2<=hf1;fill_done<=1'b0;done_v<=1'b0;cac[0]<=copy_active_n;cac[1]<=copy_active_n;
   if(reserve_v)begin
    if(!reserve_ready)stream_sticky<=1'b1;
    else begin allocated[reserve_bank]<=1'b1;started[reserve_bank]<=1'b0;staged[reserve_bank]<=1'b0;end
   end
   if(fill_start_c[4])begin
    if(!ok_fill)stream_sticky<=1'b1;
    else begin started[fsb6]<=1'b1;staged[fsb6]<=1'b1;end
   end
   if(prog)begin
    for(s=0;s<8;s=s+1)begin
     if(rem>12'(s))begin
      if(!wd_v[s]||id_bad[s])stream_sticky<=1'b1;
     end else if(wd_v[s])stream_sticky<=1'b1;
    end
    if(last)fill_done<=1'b1;
   end else if(!flt_c[4]&&(|wd_v))stream_sticky<=1'b1;
   if(ovf_any)stream_sticky<=1'b1;
   if(start_copy)begin copy_active<=1'b1;staged[choose_bank]<=1'b0;end
   if(ack_re)begin
    if(!copy_active||!ack_ok)stream_sticky<=1'b1;
    else begin allocated[cb2]<=1'b0;copy_active<=1'b0;done_v<=1'b1;end
   end
  end
 end
 always @(posedge stream_clk)begin
  for(k=0;k<2;k=k+1)begin
   if(res_acc&&reserve_bank==k[0])committed[k]<=12'd0;
   else if(prog&&fbank_c[4]==k[0])committed[k]<=lastq[1]?total[k]:{ord_n[8:2],5'd0};
  end
  // copy-bank copies follow choose_bank while idle and hold while a copy is active (captured on the start edge)
  for(k=0;k<10;k=k+1)if(!cac[k/5])copy_bank_c[k]<=choose_bank;
  // done payload captured every edge: the wrapper reads it only with done_v (the edge after ack_re)
  for(k=0;k<3;k=k+1)dbk[k]<=copy_bank_c[5];done_epoch<={epoch[copy_bank_c[6]][15:8],epoch[cb4][7:0]};
  // done_sectors follows the ack FIFO head only while both ack FIFOs are non-empty (WBK10 gen3: reviewed_gray_fifos storage
  // miter refused the every-edge load; ack_re implies !ack_empty, so the captured value at ack_re is unchanged -- 0 cycles)
  if(!ack_empty)done_sectors<=ack_rdata[11:0];
 end
 // per-column copy controls (kept): two-level copy start relay (start_copy -> st1[c] -> st_r[2c+h])
 (* keep="true",dont_touch="true" *) reg st1 [0:3];
 (* keep="true",dont_touch="true" *) reg st_r [0:15];        // copy start per lane pair group (lanes c*2.. by l[4], l[0])
 (* keep="true",dont_touch="true" *) reg cp_on [0:3];
 (* keep="true",dont_touch="true" *) reg cp_bank [0:3];
 (* keep="true",dont_touch="true" *) reg [11:0] cp_commit [0:3];
 (* keep="true",dont_touch="true" *) reg [14:0] cp_base_lo [0:3];
 (* keep="true",dont_touch="true" *) reg [28:0] cp_basem [0:3];
 wire [11:0] commit_cb=(MUT==6)?total[cb0]:committed[cb0];
 wire [29:0] base_cb={base[copy_bank_c[8]][29:23],base[cb3][22:15],base[copy_bank_c[7]][14:8],base[cb1][7:0]};
 assign copy_active_n=start_copy?1'b1:(ack_re&&copy_active&&ack_ok)?1'b0:copy_active;
 wire [28:0] basem_cb=base_cb[28:0]-29'd32;
 always @(posedge stream_clk or negedge sl[1])
  if(!sl[1])for(k=0;k<16;k=k+1)begin st_r[k]<=1'b0;if(k<4)begin cp_on[k]<=1'b0;st1[k]<=1'b0;end end
  else for(k=0;k<16;k=k+1)begin
   st_r[k]<=st1[0];
   if(k<4)begin st1[k]<=(k==0)?start_copy:1'b0;cp_on[k]<=copy_active&&!start_copy&&!st1[0]&&!st_r[4*k]&&!fault; end
  end
 always @(posedge stream_clk)for(k=0;k<4;k=k+1)begin
  cp_bank[k]<=cb0;cp_commit[k]<=commit_cb;cp_base_lo[k]<=base_cb[14:0];cp_basem[k]<=basem_cb;
 end
 // ------------------------------------------------------------------------------------------------ lanes
 wire [15:0] hpc_w [0:31];wire [6:0] rp_w [0:31];wire [255:0] rdl [0:31];
 wire [31:0] g_w [0:15];
 genvar gl,gp,gf,gq;
 generate for(gl=0;gl<32;gl=gl+1)begin:g_lane
  localparam integer C=(gl>>1)&3;           // SRAM column: l[2:1]
  localparam integer SL=gl&7;               // DMA slot
  localparam integer PH=(gl>>3)&3;          // fill phase: ordinal[4:3]
  localparam integer LEAF=6+gl/2;
  reg [6:0] rp;reg [15:0] hpc;
  wire [15:0] gcol;
  for(gp=0;gp<16;gp=gp+1)begin:g_gc assign gcol[gp]=g_w[gp][gl]; end
  wire rd_ok={rp,5'(gl)}<cp_commit[C];
  wire r_ce=cp_on[C]&&(hpc==16'd0)&&rd_ok;
  wire [14:0] hs=cp_base_lo[C]+{3'b0,rp,5'(gl)};
  wire [3:0] pcn=hs[5:2]^hs[9:6]^hs[14:11];
  always @(posedge stream_clk)rp<=st_r[4*C+2*(gl>>4)+(gl&1)]?7'd0:rp+7'(r_ce);
  always @(posedge stream_clk or negedge sl[LEAF])
   if(!sl[LEAF])hpc<=16'd0;
   else hpc<=({16{r_ce}}&(16'd1<<pcn))|(hpc&~gcol);
  assign hpc_w[gl]=hpc;assign rp_w[gl]=rp;
  wire fw=filling_c[C]&&!flt_c[C];
  ot_sram_1r1w_128x256_m1_r2c2 u_payload(
   .clk(stream_fifo_clk[C]),.r_ce_in(r_ce),.r_addr_in({cp_bank[C],rp[5:0]}),.rd_out(rdl[gl]),
   .w_ce_in(fw&&ord_c[C][1:0]==2'(PH)&&wd_v[SL]),.w_addr_in({fbank_c[C],ord_c[C][7:2]}),
   .wd_in(wd[SL*289+:256]),.w_mask_in({256{1'b1}}),
   .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 end endgenerate
 // ------------------------------------------------------------------------------------------------ arbiters, credit
 // credit: entries granted and not yet freed in the PC's slice-0 crossing FIFO(s) (all slices pop in lockstep, so
 // every slice holds the same count); okc = registered (cnt < DEFF), computed from the counter's next value (exact).
 wire [CW-1:0] wfreed [0:15];wire [16*NFP-1:0] ovf;
 assign ovf_any=|ovf;
 (* keep="true",dont_touch="true" *) reg okc [0:47];
 generate for(gp=0;gp<16;gp=gp+1)begin:g_arb
  wire [31:0] req;
  for(gl=0;gl<32;gl=gl+1)begin:g_rq assign req[gl]=hpc_w[gl][gp]; end
  wire [31:0] low=req&(~req+32'd1);
  wire [15:0] glo=(okc[3*gp]||MUT==8)?low[15:0]:16'd0;
  wire [15:0] ghi=(okc[3*gp+1]||MUT==8)?low[31:16]:16'd0;
  assign g_w[gp]={ghi,glo};
  reg [CW-1:0] cnt;
  wire gany=(okc[3*gp+2]||MUT==8)&&(|req);
  wire [CW-1:0] cnt_n=cnt+CW'(gany)-wfreed[gp];
  always @(posedge stream_clk or negedge sl[2+gp/4])
   if(!sl[2+gp/4])begin cnt<=0;okc[3*gp]<=1'b0;okc[3*gp+1]<=1'b0;okc[3*gp+2]<=1'b0;end
   else begin cnt<=cnt_n;okc[3*gp]<=cnt_n<CW'(DEFF);okc[3*gp+1]<=cnt_n<CW'(DEFF);okc[3*gp+2]<=cnt_n<CW'(DEFF);end
 end endgenerate
 // ------------------------------------------------------------------------------------------------ select, crossbar, FIFOs
 (* keep="true",dont_touch="true" *) reg [31:0] sel_q [0:16*NDS-1]; // [pc*NDS+slice] one-hot lane select
 (* keep="true",dont_touch="true" *) reg [31:0] gqa [0:15];        // granted lane one-hot for the address
 (* keep="true",dont_touch="true" *) reg xv1c [0:16*NSL-1];
 (* keep="true",dont_touch="true" *) reg xv2c [0:16*NSL-1];
 (* keep="true",dont_touch="true" *) reg wtog [0:16*NSL-1];
 wire [15:0] fifo_rd [0:16*NFP-1];wire [16*NFP-1:0] fifo_empty;
 wire [FAW:0] fifo_wf [0:16*NFP-1];wire [FAW:0] fifo_rc [0:16*NFP-1];
 (* keep="true",dont_touch="true" *) reg popc [0:16*NSL-1];        // registered lockstep pop, one copy per slice
 (* keep="true",dont_touch="true" *) reg rtc [0:16*NSL-1];         // read toggle (which ping-pong FIFO is next)
 (* keep="true",dont_touch="true" *) reg rtd [0:16*NSL-1];         // read toggle copy for the data mux
 generate for(gp=0;gp<16;gp=gp+1)begin:g_pc
  localparam integer K=gp/4;
  wire fclk=stream_fifo_clk[K];
  wire gany_w=|g_w[gp];
  reg [28:0] xr_a;reg [6:0] arp;reg [4:0] aln;integer j;
  always @*begin
   arp=0;aln=0;
   for(j=0;j<32;j=j+1)begin
    if(gqa[gp][j])arp=arp|rp_w[j];
    if(gqa[gp][j])aln=aln|5'(j);
   end
  end
  always @(posedge fclk)begin gqa[gp]<=g_w[gp];xr_a<=cp_basem[K]+{17'd0,arp,aln};end
  // credit returns of slice 0 (both ping-pong FIFOs)
  if(NPP==2)begin:g_wf2 assign wfreed[gp]=CW'(fifo_wf[gp*NFP])+CW'(fifo_wf[gp*NFP+1]); end
  else begin:g_wf1 assign wfreed[gp]=CW'(fifo_wf[gp*NFP]); end
  for(gf=0;gf<NSL;gf=gf+1)begin:g_sl
   localparam integer SW=sw_f(gf), SO=so_f(gf);
   localparam integer IX=gp*NSL+gf;
   localparam integer WL=(gp%4)*NFP+gf*NPP;            // write-side reset leaf of FIFO 0 of this slice
   localparam integer XL=XB+(gp%4)*3+gf/7;
   wire [15:0] wdat;
   if(gf<NDS)begin:g_dat
    wire [31:0] gsrc;
    for(gl=0;gl<32;gl=gl+1)begin:g_m assign gsrc[gl]=(MUT==5&&gf==3)?g_w[gp][gl^1]:g_w[gp][gl]; end
    always @(posedge fclk)sel_q[gp*NDS+gf]<=gsrc;
    reg [SW-1:0] xd,xr_d;integer m;
    always @*begin xd=0;for(m=0;m<32;m=m+1)if(sel_q[gp*NDS+gf][m])xd=xd|rdl[m][SO+:SW];end
    always @(posedge fclk)xr_d<=xd;
    assign wdat=16'(xr_d);
   end else if(gf==NDS)begin:g_a0 assign wdat=16'(xr_a[14:0]);
   end else begin:g_a1 assign wdat=16'(xr_a[28:15]); end
   always @(posedge fclk or negedge rl[K][XL])
    if(!rl[K][XL])begin xv1c[IX]<=1'b0;xv2c[IX]<=1'b0;wtog[IX]<=1'b0;end
    else begin xv1c[IX]<=gany_w;xv2c[IX]<=xv1c[IX];if(xv2c[IX]&&NPP==2)wtog[IX]<=!wtog[IX];end
   for(gq=0;gq<NPP;gq=gq+1)begin:g_f
    localparam integer FX=gp*NFP+gf*NPP+gq;
    wire [CW-1:0] wf;wire [SW-1:0] rdat;wire fe;
    wire wr=xv2c[IX]&&((NPP==1)||(wtog[IX]==gq[0]));
    wire rd=popc[IX]&&((NPP==1)||(((MUT==9&&gf==5)?1'b0:rtc[IX])==gq[0]));
    ot_link_afifo #(.W(SW),.AW(FAW),.SYNC(2),.RCOPY(3)) u_fifo(
     .wclk(fclk),.wrst_n(rl[K][WL+gq]),.wr(wr),.wdata(wdat[SW-1:0]),.wfull(),.wfreed(wf[FAW:0]),.ovf(ovf[FX]),
     .rclk(hbm_clk),.rrst_n(hl[FX]),.rd(rd),.rempty(fe),.rdata(rdat),.rcount(fifo_rc[FX]));
    assign wf[CW-1:FAW+1]=0;
    assign fifo_empty[FX]=fe;assign fifo_rd[FX]=16'(rdat);assign fifo_wf[FX]=wf[FAW:0];
   end
  end
 end endgenerate
 // ------------------------------------------------------------------------------------------------ meta / ack tokens
 wire meta_re,ack_we;reg meta_active,ack_pending;wire meta_active_n;reg [12:0] meta_q;reg [11:0] ack_count;
 // meta / ack tokens cross as two <= 7-b reviewed FIFOs each (written and popped together: full / empty = either)
 wire [1:0] mf,me,af,ae;wire [12:0] mwd={choose_bank,total[choose_bank]};
 ot_link_afifo #(.W(7),.AW(2),.SYNC(2),.RCOPY(2)) u_meta_h(
  .wclk(stream_clk),.wrst_n(sl[22]),.wr(start_copy_h),.wdata(mwd[12:6]),.wfull(mf[1]),.wfreed(),.ovf(),
  .rclk(hbm_clk),.rrst_n(hl[HM]),.rd(meta_re),.rempty(me[1]),.rdata(meta_rdata[12:6]),.rcount());
 ot_link_afifo #(.W(6),.AW(2),.SYNC(2),.RCOPY(2)) u_meta_l(
  .wclk(stream_clk),.wrst_n(sl[27]),.wr(start_copy_l),.wdata(mwd[5:0]),.wfull(mf[0]),.wfreed(),.ovf(),
  .rclk(hbm_clk),.rrst_n(hl[HM+5]),.rd(meta_re),.rempty(me[0]),.rdata(meta_rdata[5:0]),.rcount());
 assign meta_full=|mf;assign meta_empty=|me;
 ot_link_afifo #(.W(7),.AW(2),.SYNC(2),.RCOPY(2)) u_ack_h(
  .wclk(hbm_clk),.wrst_n(hl[HM+1]),.wr(ack_we_h),.wdata(meta_q[12:6]),.wfull(af[1]),.wfreed(),.ovf(),
  .rclk(stream_clk),.rrst_n(sl[23]),.rd(ack_re),.rempty(ae[1]),.rdata(ack_rdata[12:6]),.rcount());
 ot_link_afifo #(.W(6),.AW(2),.SYNC(2),.RCOPY(2)) u_ack_l(
  .wclk(hbm_clk),.wrst_n(hl[HM+6]),.wr(ack_we_l),.wdata(meta_q[5:0]),.wfull(af[0]),.wfreed(),.ovf(),
  .rclk(stream_clk),.rrst_n(sl[28]),.rd(ack_re),.rempty(ae[0]),.rdata(ack_rdata[5:0]),.rcount());
 assign ack_full=|af;assign ack_empty=|ae;
 // ------------------------------------------------------------------------------------------------ hbm side
 wire hbm_fault=hbm_sticky||sf2||!hl_ok;
 assign meta_re=!meta_active&&!meta_empty&&!hbm_fault;
 assign ack_we=ack_pending&&!ack_full&&!hbm_fault;
 // per-FIFO ack write strobes from kept ack_pending copies (each strobe feeds one reviewed FIFO's write side)
 (* keep="true",dont_touch="true" *) reg apc [0:1];
 wire ack_we_h=apc[1]&&!ack_full&&!hbm_fault, ack_we_l=apc[0]&&!ack_full&&!hbm_fault;
 assign meta_active_n=meta_re?1'b1:ack_we?1'b0:meta_active;
 reg [15:0] done_q;
 always @(posedge hbm_clk or negedge hl[HM+3])
  if(!hl[HM+3])done_q<=0;else done_q<=w_k_wr_done;
 (* keep="true",dont_touch="true" *) reg allow1 [0:15];   // PC enable: block meta active (one edge late)
 (* keep="true",dont_touch="true" *) reg vqc [0:16*NSL-1]; // ring non-empty, one copy per slice
 (* keep="true",dont_touch="true" *) reg [2:0] wpo [0:16*NSL-1];
 (* keep="true",dont_touch="true" *) reg [2:0] rpo [0:16*NSL-1];
 wire [15:0] spurious;
 generate for(gp=0;gp<16;gp=gp+1)begin:g_hk
  localparam integer CL=HB+gp*NRL+NRL-1;
  reg [6:0] cnt_h;reg [1:0] occ;reg pop_ctl,vq_ctl,vq_pin;
  wire [NSL-1:0] avail;
  wire fire_ctl=vq_ctl&&w_k_rdy[gp];
  wire [1:0] occ_n=occ+2'(pop_ctl)-2'(fire_ctl);
  wire [6:0] cnt_n=cnt_h+7'(pop_ctl)-7'(done_q[gp]);
  // pop at t+1 when every slice's next FIFO holds a word, the ring has room without counting a fire, the block is
  // active and fewer than 64 writes are in the PC (popped, not completed) after the pop
  wire [2:0] occ_p={1'b0,occ}+3'(pop_ctl);
  wire pop_n=(&avail)&&(occ_p<=3'd2||MUT==10)&&allow1[gp]&&(cnt_n<7'd64);
  always @(posedge hbm_clk or negedge hl[CL])
   if(!hl[CL])begin cnt_h<=0;occ<=0;pop_ctl<=0;vq_ctl<=0;vq_pin<=0;allow1[gp]<=1'b0;end
   else begin
    cnt_h<=cnt_n;occ<=occ_n;pop_ctl<=pop_n;vq_ctl<=occ_n!=2'd0;vq_pin<=occ_n!=2'd0;
    allow1[gp]<=meta_active&&!ack_pending&&!hbm_fault;
   end
  assign w_k_v[gp]=vq_pin;
  assign spurious[gp]=done_q[gp]&&cnt_h==7'd0;
  wire [255:0] kd;wire [28:0] o;
  for(gf=0;gf<NSL;gf=gf+1)begin:g_s
   localparam integer SW=sw_f(gf), SO=so_f(gf);
   localparam integer IX=gp*NSL+gf;
   localparam integer RL=HB+gp*NRL+gf/3;
   localparam integer F0=gp*NFP+gf*NPP;
   wire e0=fifo_empty[F0];wire e1=(NPP==2)?fifo_empty[F0+NPP-1]:1'b1;
   wire [15:0] r0=fifo_rd[F0];wire [15:0] r1=fifo_rd[F0+NPP-1];
   // next FIFO read at t+1: toggle after a pop (PP), or the same FIFO with one more word (PP = 0)
   if(NPP==2)begin:g_av2
    wire nsel=rtc[IX]^popc[IX];
    assign avail[gf]=nsel?!e1:!e0;
   end else begin:g_av1
    wire [FAW:0] rc0=fifo_rc[F0];
    assign avail[gf]=popc[IX]?(rc0>=(FAW+1)'(2)):!e0;
   end
   wire [SW-1:0] din=(NPP==2&&rtd[IX])?r1[SW-1:0]:r0[SW-1:0];
   wire push=popc[IX];
   // ring load gated by the read FIFO's own !rempty (WBK10: reviewed_gray_fifos extension-mode storage miter refused the
   // popc-only enable; popc implies the read FIFO is non-empty, so the gate is functionally a no-op -- no cycle change)
   wire rv=(NPP==2&&rtd[IX])?!e1:!e0;
   wire fire=vqc[IX]&&w_k_rdy[gp];
   reg [SW-1:0] ent [0:2];
   integer e;
   always @(posedge hbm_clk)for(e=0;e<3;e=e+1)if(push&&rv&&wpo[IX][e])ent[e]<=din;
   always @(posedge hbm_clk or negedge hl[RL])
    if(!hl[RL])begin popc[IX]<=1'b0;rtc[IX]<=1'b0;rtd[IX]<=1'b0;vqc[IX]<=1'b0;wpo[IX]<=3'b001;rpo[IX]<=3'b001;end
    else begin
     popc[IX]<=pop_n;vqc[IX]<=occ_n!=2'd0;
     if(push&&NPP==2&&!(MUT==9&&gf==5))begin rtc[IX]<=!rtc[IX];rtd[IX]<=!rtd[IX];end
     if(push)wpo[IX]<={wpo[IX][1:0],wpo[IX][2]};
     if(fire)rpo[IX]<={rpo[IX][1:0],rpo[IX][2]};
    end
   wire [SW-1:0] dout=({SW{rpo[IX][0]}}&ent[0])|({SW{rpo[IX][1]}}&ent[1])|({SW{rpo[IX][2]}}&ent[2]);
   if(gf<NDS)begin:g_kd assign kd[SO+:SW]=dout; end
   else if(gf==NDS)begin:g_o0 assign o[14:0]=dout; end
   else begin:g_o1 assign o[28:15]=dout; end
  end
  assign w_k_wdata[256*gp+:256]=kd;
  assign w_k_addr[30*gp+:30]={o[28:6],q_h^o[10]^o[15],o[5:0]};
 end endgenerate
 reg [4:0] acks;integer a;
 always @*begin acks=0;for(a=0;a<16;a=a+1)acks=acks+5'(done_q[a]);end
 always @(posedge hbm_clk or negedge hl[HM+2])begin
  if(!hl[HM+2])begin
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
 // meta_q follows the head while no block is active and holds while active (a kept copy of meta_active selects)
 (* keep="true",dont_touch="true" *) reg mac;
 wire ack_pending_n=meta_re?1'b0:ack_we?1'b0:(meta_active&&!hbm_fault&&acks!=0&&ack_count+12'(acks)==meta_q[11:0])?1'b1:ack_pending;
 always @(posedge hbm_clk or negedge hl[HM+2])if(!hl[HM+2])begin mac<=1'b0;apc[0]<=1'b0;apc[1]<=1'b0;end
  else begin mac<=meta_active_n;apc[0]<=ack_pending_n;apc[1]<=ack_pending_n;end
 // meta_q loads the meta FIFO head only while both meta FIFOs are non-empty (WBK10: storage miter; meta_re implies !meta_empty -> 0 cycles)
 always @(posedge hbm_clk)if(!mac&&!meta_empty)meta_q<=meta_rdata;
endmodule
`default_nettype wire
