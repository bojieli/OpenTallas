`timescale 1ns/1ps
`default_nettype none
// Native32 ROWS256 successor: safe128v8 architecture widened to exact8-bit cfg37 ISA; no edge changes.
module ot_hgi_coll_issuer_m256v8 (
 input wire clk_control,input wire rst_n,
 input wire [36:0] cfg,input wire start,input wire [7:0] start_pc,
 output wire busy,done,fault,uop_v,
 output wire [7:0] uop_pc,
 output reg [1535:0] uop_d1,
 output reg busy_d3,done_d3,start_d3,
 output reg busy_d2,start_d2,
 output wire [31:0] tap_iteration,
 output wire [87:0] tap_steps
);
 localparam integer NR=54;
 wire clk=clk_control;
 // ---------------- reset release copies (each = v7 rst_l) ----------------
 (* keep = "true" *) reg [NR-1:0] rcp;
 always @(posedge clk or negedge rst_n) if(!rst_n) rcp<={NR{1'b0}}; else rcp<={NR{1'b1}};
 // ---------------- helpers ----------------
 function automatic [7:0] f_next(input [63:0] x); f_next={x[54],x[51],x[5:0]}; endfunction
 function automatic [7:0] f_tgt(input [63:0] x); f_tgt={x[55],x[52],x[11:6]}; endfunction
 // record {next 7 [52:46], tgt 7 [45:39], lid 5 [38:34], halt [33], has [32], cnt 32 [31:0]}; cnt = RAW count field.
 // HBM-COLLECT10/ISS (10-21): the v8 record held count-1, so every metadata macro read (326 ps clk->q) fed a 32-bit
 // decrement borrow chain (~10 OR levels) into rt / rn / pr_* in the same edge (route r128v9b: TT -135 ps, 64 D pins,
 // class g_meta rd_out -> rt/rn/pr_*). The record now stores the raw count and the decrement is folded into the loop
 // decision (registered side): take = has && q < cnt-1 == has && q + ~cnt + 2 < 2^32 (carry-save, one adder).
 localparam integer RW=55;
 function automatic [RW-1:0] f_rec(input [63:0] x);
  f_rec={f_next(x),f_tgt(x),x[49:45],x[44],|x[43:12],x[43:12]};
 endfunction
 function automatic [7:0] r_next(input [RW-1:0] r); r_next=r[54:47]; endfunction
 function automatic [7:0] r_tgt(input [RW-1:0] r); r_tgt=r[46:39]; endfunction
 function automatic [4:0] r_lid(input [RW-1:0] r); r_lid=r[38:34]; endfunction
 function automatic r_has(input [RW-1:0] r); r_has=r[32]; endfunction
 function automatic [31:0] r_cnt(input [RW-1:0] r); r_cnt=r[31:0]; endfunction
 // loop decision, visits domain: take = has && (q < count-1)   (reload mutant: q <= count-1 = v7 lp1 <= count)
 // q < cnt-1 (cnt >= 1)  <=>  q + ~cnt + 2 < 2^32: carry-save q / ~cnt / 2, then one 32-bit carry-out (no decrement).
 // reload mutant q <= cnt-1 <=> q < cnt <=> q + ~cnt + 1 < 2^32.
 function automatic f_take(input has,input [31:0] qv,input [31:0] cnt);
  reg [31:0] b,c,sv,kv;reg [32:0] t;
  begin
   b=~cnt;
`ifdef OT_COLL_ISS8_MUT_RELOAD
   c=32'd1;
`else
   c=32'd2;
`endif
   sv=qv ^ b ^ c;kv=(qv & b) | (qv & c) | (b & c);
   t={1'b0,sv}+{1'b0,kv[30:0],1'b0};
   f_take=has && !(kv[31] || t[32]);
  end
 endfunction
 // explicit 2+3 predecoded 5->32 one-hot (with enable)
 function automatic [31:0] f_dec(input en,input [4:0] a);
  reg [3:0] pa;reg [7:0] pb;
  begin
   pa=en ? (4'd1<<a[4:3]) : 4'd0;pb=8'd1<<a[2:0];
   for(integer i=0;i<32;i=i+1)f_dec[i]=pa[i/8] & pb[i%8];
  end
 endfunction
 // ---------------- pin registers (as v7: cfg / start / start_pc registered, +1 issue edge) ----------------
 reg [35:0] cfg_q;reg [7:0] start_pc_q;reg cfgv_q,start_q;
 reg [3:0] md_q;                               // md_q[k] = cfg[36] && mode == k, registered beside cfg_q
 (* keep = "true" *) reg [3:0] mlo_c,mhi_c;    // metadata write masks per macro: lo = (mode == 2), hi = (mode != 2)
 (* keep = "true" *) reg wdl_c,wdh_c;          // metadata write data gates: lo = (mode == 2), hi = (mode != 2)
 always @(posedge clk)begin
  cfg_q<=cfg[35:0];start_pc_q<=start_pc;
  mlo_c<={4{cfg[35:32]==4'd2}};mhi_c<={4{cfg[35:32]!=4'd2}};
  wdl_c<=cfg[35:32]==4'd2;wdh_c<=cfg[35:32]!=4'd2;
 end
 // ---------------- state ----------------
 reg busy_r,done_r,fault_r,v1,uop_v_r,h0,h1,cfg_selected;
 reg [3:0] fragment;reg [2:0] write_v;reg [1:0] ph;
 (* keep = "true" *) reg [3:0] fch_c;          // fetching: [0] control, [1] it0 lo, [2] it0 hi, [3] fetch_pc
 (* keep = "true" *) reg [3:0] fv_c;           // fetch_v: [b] bank b read enable + its v1 mask copies, [3] v1
 (* keep = "true" *) reg [15:0] vm0,vm1,vm2;   // v1 copies: bank data mask (32 bits each)
 reg [7:0] uop_pc_r;reg [31:0] iteration;
 reg [7:0] cfg_row;reg [1:0] cfg_bank;reg [511:0] assemble;reg [7:0] write_row;
 reg [7:0] pc;(* keep = "true" *) reg [3:0] pcm[0:15];   // pc[3:0] copies, 16 rows each
 reg [7:0] fetch_pc,pc1;reg [31:0] it0,it1;reg [7:0] sp_q;
 reg [22:0] rc;                                // {next [20:14], tgt [13:7], lid [6:2], halt [1], has [0]} of C
 reg [RW-1:0] rt,rn,pr_c,pr_t,pr_n;
 reg [31:0] q;(* keep = "true" *) reg [31:0] qa,qb,qf;   // visits (= v7 lp1 - 1): state / L1 write lo rows / hi rows / fwd
 reg [31:0] L1q[0:31];reg [31:0] L1v,L1z;       // stored q+1, valid (cleared at start), zero (stored value is 0)
 // registered predicates (kept copies)
 // copy maps (<= 8-14 mux bits per copy: an enable / 2:1 mux maps to 2 load pins per bit)
 //  sacc_c / adv_c: [0] control, [1:2] C, [3:6] CT, [7:10] CN, [11:14] q, [15:18] L1 valid (sacc) / metadata address k (adv)
 //  tk_c: [0] control, [1:2] C, [3:10] CT word, [11:18] CN word, [19:22] q, [23:26] L1 zero flag, [27:30] forwarded q+1
 (* keep = "true" *) reg [18:0] sacc_c;        // start accepted this edge
 (* keep = "true" *) reg [18:0] adv_c;         // advance (fetching && !halt(C))
 (* keep = "true" *) reg [30:0] tk_c;          // loop decision
 (* keep = "true" *) reg [2:0] mw_c;           // metadata write this edge
 (* keep = "true" *) reg [3:0] pe1_c;          // prime C (phe == 1, no mw / advance)
 (* keep = "true" *) reg [7:0] pe2_c;          // prime CT / CN (phe == 2)
 (* keep = "true" *) reg [1:0] p0_c,p1_c,p2_c; // effective priming phase (macros 0-1 / 2-3)
 (* keep = "true" *) reg [3:0] fwt_c,fwn_c;    // counter forwarding into the CT / CN reads: 4 kept copies, 8 counter bits each (r128v11: census fwn_c[0] 34 loads)
 (* keep = "true" *) reg [31:0] stl,sth,snl,snh;   // one-hot lid(CT) / lid(CN) & valid & !zero, lo / hi bit copies
 (* keep = "true" *) reg [31:0] wac,wbc,wcc;   // L1 write one-hot (update && lid(C)): bits 9:0 + valid / zero, 20:10, 31:21
 (* keep = "true" *) reg [15:0] aen_a,aen_b,aen_c;   // assembly fragment enables: bits 10:0 / 21:11 / 31:22
 (* keep = "true" *) reg [31:0] rh_q0,rh_q1;reg [7:0] en_w0,en_w1,en_w2,en_ml,en_mh;   // registered row-valid set: one-hot row[4:0], group enables
 // ---------------- current-edge conditions ----------------
 wire sacc=sacc_c[0],adv=adv_c[0],take=tk_c[0],mw=mw_c[0];
 wire nbs=!(busy_r || start_q);
 wire c0=md_q[0] && nbs,c1=md_q[1] && nbs,c2=md_q[2] && nbs,c3=md_q[3] && nbs;
 wire cbad=cfgv_q && (busy_r || start_q || cfg_q[35:32]>4'd3);   // cfg word while busy / start, or an unknown mode
 wire m2_ok=cfg_selected && fragment==4'd0;
 wire m3_ok=cfg_selected && fragment==4'd0 && cfg_q[31:24]==8'd0 && !cfg_q[21] && !cfg_q[18];   // lid < 32
 wire m1ok=c1 && cfg_selected && cfg_bank!=2'd3;
 wire fw=m1ok && fragment==4'd15;                                    // a full programme word is written
 wire mism=start_pc_q!=sp_q;
 wire [1:0] phe=mism ? 2'd0 : ph;
 // ---------------- metadata macros ----------------
 wire [255:0] mo_all;
 wire [63:0] mo0=mo_all[0+:64],mo1=mo_all[64+:64],mo2=mo_all[128+:64],mo3=mo_all[192+:64];
 // CT / CN successor words: take picks the grand-successor pair of the chosen successor (16-bit take copies)
 wire [63:0] nt_w,nn_w;
 for(genvar k=0;k<4;k=k+1)begin:g_ntw
`ifdef OT_COLL_ISS8_MUT_SWAP
  assign nt_w[k*16+:16]={tk_c[4+2*k] ? mo2[k*16+8+:8] : mo0[k*16+8+:8],tk_c[3+2*k] ? mo2[k*16+:8] : mo0[k*16+:8]};
  assign nn_w[k*16+:16]={tk_c[12+2*k] ? mo3[k*16+8+:8] : mo1[k*16+8+:8],tk_c[11+2*k] ? mo3[k*16+:8] : mo1[k*16+:8]};
`else
  assign nt_w[k*16+:16]={tk_c[4+2*k] ? mo0[k*16+8+:8] : mo2[k*16+8+:8],tk_c[3+2*k] ? mo0[k*16+:8] : mo2[k*16+:8]};
  assign nn_w[k*16+:16]={tk_c[12+2*k] ? mo1[k*16+8+:8] : mo3[k*16+8+:8],tk_c[11+2*k] ? mo1[k*16+:8] : mo3[k*16+:8]};
`endif
 end
 wire [63:0] mw_d={{32{wdh_c}} & cfg_q[31:0],{32{wdl_c}} & cfg_q[31:0]};
 for(genvar k=0;k<4;k=k+1)begin:g_meta
  wire mwk=mw_c[1+k/2],advk=adv_c[15+k],p0k=p0_c[k/2],p1k=p1_c[k/2],p2k=p2_c[k/2];
  reg [7:0] a;reg rce;
  always @*begin
   if(mwk)begin a=cfg_row;rce=1'b1;end
   else if(advk)begin a=(k==0) ? f_tgt(nt_w) : (k==1) ? f_next(nt_w) : (k==2) ? f_tgt(nn_w) : f_next(nn_w);rce=1'b1;end
   else if(p0k)begin a=(k==0) ? start_pc_q : 8'd0;rce=(k==0);end
   else if(p1k)begin a=(k==0) ? f_tgt(mo0) : (k==1) ? f_next(mo0) : 8'd0;rce=(k<2);end
   else if(p2k)begin a=(k==0) ? f_tgt(mo0) : (k==1) ? f_next(mo0) : (k==2) ? f_tgt(mo1) : f_next(mo1);rce=1'b1;end
   else begin a=(k==0) ? r_tgt(pr_t) : (k==1) ? r_next(pr_t) : (k==2) ? r_tgt(pr_n) : r_next(pr_n);rce=1'b1;end
  end
  ot_sram_1rw_256x64_m4_r2c2 u_sram(.clk(clk),.ce_in(rce),.we_in(mwk),.addr_in(a),
   .wd_in(mw_d),.w_mask_in({{32{mhi_c[k]}},{32{mlo_c[k]}}}),.rd_out(mo_all[k*64+:64]),
   .rr_en(2'b0),.rr_addr(12'b0),.cr_en(2'b0),.cr_sel(12'b0));
 end
 // ---------------- programme banks (data <= v1 ? word : 0 = the v7 uop_v mask) ----------------
 wire [1535:0] uop;
 wire [15:0] vmb[0:2];assign vmb[0]=vm0;assign vmb[1]=vm1;assign vmb[2]=vm2;
 for(genvar b=0;b<3;b=b+1)begin:g_mem
  ot_hgi_coll_program_bank256m u_bank(.clk(clk),.read_v(fv_c[b]),.read_row(fetch_pc),.write_v(write_v[b]),
   .write_row(write_row),.write_data(assemble),.vm(vmb[b]),.data(uop[b*512+:512]));
 end
 // ---------------- loop counter reads ----------------
 wire [31:0] inca=qa+32'd1,incb=qb+32'd1,incf=qf+32'd1;
 reg [31:0] aot,aon;
 always @*begin
  aot=32'd0;aon=32'd0;
  for(integer i=0;i<32;i=i+1)begin
   aot=aot | ({{16{sth[i]}},{16{stl[i]}}} & L1q[i]);
   aon=aon | ({{16{snh[i]}},{16{snl[i]}}} & L1q[i]);
  end
 end
 wire [31:0] nft={{16{tk_c[27]}} & incf[31:16],{16{tk_c[28]}} & incf[15:0]};   // forwarded q+1 / 0 (CT read)
 wire [31:0] nfn={{16{tk_c[29]}} & incf[31:16],{16{tk_c[30]}} & incf[15:0]};   // (CN read)
`ifdef OT_COLL_ISS8_MUT_NOFWD
 wire [31:0] l_t=aot,l_n=aon;
`else
 wire [31:0] l_t={fwt_c[3] ? nft[31:24] : aot[31:24],fwt_c[2] ? nft[23:16] : aot[23:16],fwt_c[1] ? nft[15:8] : aot[15:8],fwt_c[0] ? nft[7:0] : aot[7:0]};
 wire [31:0] l_n={fwn_c[3] ? nfn[31:24] : aon[31:24],fwn_c[2] ? nfn[23:16] : aon[23:16],fwn_c[1] ? nfn[15:8] : aon[15:8],fwn_c[0] ? nfn[7:0] : aon[7:0]};
`endif
 wire tt=f_take(r_has(rt),l_t,r_cnt(rt)),tn=f_take(r_has(rn),l_n,r_cnt(rn));
 // ---------------- data next state (per-bit select copies) ----------------
 wire [RW-1:0] rec_nt=f_rec(nt_w),rec_nn=f_rec(nn_w),rec_m0=f_rec(mo0),rec_m1=f_rec(mo1);
 wire [22:0] rc_n;wire [RW-1:0] rt_n,rn_n;wire [31:0] q_n;
 for(genvar i=0;i<23;i=i+1)begin:g_rcn
  assign rc_n[i]=sacc_c[1+i/12] ? pr_c[32+i] : adv_c[1+i/12] ? (tk_c[1+i/12] ? rt[32+i] : rn[32+i]) : rc[i];
 end
 for(genvar i=0;i<RW;i=i+1)begin:g_rtn
  assign rt_n[i]=sacc_c[3+i/14] ? pr_t[i] : adv_c[3+i/14] ? rec_nt[i] : rt[i];
  assign rn_n[i]=sacc_c[7+i/14] ? pr_n[i] : adv_c[7+i/14] ? rec_nn[i] : rn[i];
 end
 for(genvar i=0;i<32;i=i+1)begin:g_qn
  assign q_n[i]=sacc_c[11+i/8] ? 1'b0 : adv_c[11+i/8] ? (tk_c[19+i/8] ? l_t[i] : l_n[i]) : q[i];
 end
 always @(posedge clk)begin
  rc<=rc_n;rt<=rt_n;rn<=rn_n;q<=q_n;qa<=q_n;qb<=q_n;qf<=q_n;sp_q<=start_pc_q;
 end
 for(genvar i=0;i<RW;i=i+1)begin:g_pr
  always @(posedge clk)begin
   if(pe1_c[i/14])pr_c[i]<=rec_m0[i];
   if(pe2_c[i/14])pr_t[i]<=rec_m0[i];
   if(pe2_c[4+i/14])pr_n[i]<=rec_m1[i];
  end
 end
 // loop counters: written at the update edge (registered one-hot write copies); valid cleared by start
 wire [31:0] L1v_n,L1z_n;
 for(genvar i=0;i<32;i=i+1)begin:g_l1
  wire [31:0] wd=(i<16) ? inca : incb;
  assign L1v_n[i]=sacc_c[15+i/8] ? 1'b0 : wac[i] ? 1'b1 : L1v[i];
  assign L1z_n[i]=wac[i] ? !tk_c[23+i/8] : L1z[i];
  always @(posedge clk)begin
   if(wac[i])L1q[i][9:0]<=wd[9:0];
   if(wbc[i])L1q[i][20:10]<=wd[20:10];
   if(wcc[i])L1q[i][31:21]<=wd[31:21];
   L1v[i]<=L1v_n[i];L1z[i]<=L1z_n[i];
  end
 end
 // ---------------- control next state (the v7 sequential block, explicit) ----------------
 wire halt_c=rc[1];
 wire sbad=start_q && !sacc;                                   // a start that faults (busy / cfg / fragment / not ready)
 wire rok;                                                     // row pc fully written (fetch check)
 wire busy_n=sacc ? 1'b1 : (v1 && h1) ? 1'b0 : busy_r;
 wire fch_n=sacc ? 1'b1 : (fch_c[0] && halt_c) ? 1'b0 : fch_c[0];
 wire [1:0] ph_n=mw ? 2'd0 : adv ? (mism ? 2'd0 : ph) : (phe==2'd3 ? 2'd3 : phe+2'd1);
 wire sel_n=c0 ? (cfg_q[7:6]!=2'd3) : cfg_selected;
 wire [1:0] bank_n=c0 ? cfg_q[7:6] : cfg_bank;
 wire [3:0] frag_n=c0 ? 4'd0 : m1ok ? fragment+4'd1 : fragment;
 wire [7:0] pc_n=sacc ? start_pc_q : adv ? (take ? rc[14:7] : rc[22:15]) : pc;
 wire fault_n=fault_r || sbad || (fch_c[0] && !rok) || cbad ||
              (c0 && (fragment!=4'd0 || cfg_q[31:10]!=22'd0 || cfg_q[7:6]==2'd3)) ||
              (c1 && !(cfg_selected && cfg_bank!=2'd3)) || (c2 && !m2_ok) || (c3 && !m3_ok);
 // ---------------- predicates of the NEXT edge (from the next state + the pin inputs) ----------------
 wire mism_x=start_pc!=start_pc_q;
 wire [1:0] phe_x=mism_x ? 2'd0 : ph_n;
 wire nbs_x=!(busy_n || start);
 wire sacc_x=start && !(busy_n || cfg[36] || frag_n!=4'd0) && phe_x==2'd3;
 wire adv_x=fch_n && !rc_n[1];
 wire mw_x=cfg[36] && nbs_x && sel_n && frag_n==4'd0 &&
           (cfg[35:32]==4'd2 || (cfg[35:32]==4'd3 && cfg[31:24]==8'd0 && !cfg[21] && !cfg[18]));
 wire m1ok_x=cfg[36] && cfg[35:32]==4'd1 && nbs_x && sel_n && bank_n!=2'd3;
 wire upd_x=adv_x && rc_n[0];
 wire take_x=sacc ? (r_has(pr_c) && f_take(1'b1,32'd0,r_cnt(pr_c))) : adv ? (take ? tt : tn) : take;
 wire [31:0] oht_x=f_dec(1'b1,r_lid(rt_n)),ohn_x=f_dec(1'b1,r_lid(rn_n)),wr_x=f_dec(upd_x,rc_n[6:2]);
 wire [15:0] aen_x;
 for(genvar f=0;f<16;f=f+1)begin:g_aenx assign aen_x[f]=m1ok_x && frag_n==f; end
 // pc copies for the 128-row fetch check (32 rows each)
 wire [255:0] rowok;
 wire [15:0] rsel;
 for(genvar j=0;j<16;j=j+1)begin:g_rsel assign rsel[j]=rowok[j*16+pcm[j]]; end
 assign rok=rsel[pc[7:4]];
 always @(posedge clk)begin
  // free data registers (they hold while reset: written only under reset-cleared enables)
  pc<=pc_n;for(integer j=0;j<16;j=j+1)pcm[j]<=pc_n[3:0];
  if(c0)begin cfg_row<={cfg_q[9:8],cfg_q[5:0]};cfg_bank<=cfg_q[7:6];end
  if(fw)write_row<=cfg_row;
  if(fch_c[1])it0[15:0]<=q[15:0];
  if(fch_c[2])it0[31:16]<=q[31:16];
  if(fch_c[3])fetch_pc<=pc;
  tk_c<={31{take_x}};
  stl<=oht_x & L1v_n & ~L1z_n;sth<=oht_x & L1v_n & ~L1z_n;snl<=ohn_x & L1v_n & ~L1z_n;snh<=ohn_x & L1v_n & ~L1z_n;
  wac<=wr_x;wbc<=wr_x;wcc<=wr_x;aen_a<=aen_x;aen_b<=aen_x;aen_c<=aen_x;
  rh_q0<=f_dec(1'b1,cfg_row[4:0]);rh_q1<=f_dec(1'b1,cfg_row[4:0]);
 end
 for(genvar f=0;f<16;f=f+1)begin:g_asm
  always @(posedge clk)begin
   if(aen_a[f])assemble[f*32+:11]<=cfg_q[10:0];
   if(aen_b[f])assemble[f*32+11+:11]<=cfg_q[21:11];
   if(aen_c[f])assemble[f*32+22+:10]<=cfg_q[31:22];
  end
 end
 // hold while reset (v7: pc1 / it1 sit in the reset block without a reset value)
 always @(posedge clk) if(rcp[8])pc1<=fetch_pc;
 always @(posedge clk) if(rcp[49])it1[10:0]<=it0[10:0];
 always @(posedge clk) if(rcp[50])it1[21:11]<=it0[21:11];
 always @(posedge clk) if(rcp[51])it1[31:22]<=it0[31:22];
 // G0: control + pin + delay chains
 reg busy_d1,done_d1,done_d2,start_d1;
 always @(posedge clk or negedge rcp[0])
  if(!rcp[0])begin
   busy_r<=0;done_r<=0;fault_r<=0;v1<=0;uop_v_r<=0;h0<=0;h1<=0;cfg_selected<=0;fragment<=0;write_v<=0;ph<=0;
   cfgv_q<=0;start_q<=0;busy_d1<=0;busy_d2<=0;busy_d3<=0;done_d1<=0;done_d2<=0;done_d3<=0;start_d1<=0;start_d2<=0;start_d3<=0;
  end else begin
   busy_r<=busy_n;done_r<=v1 && h1;fault_r<=fault_n;v1<=fv_c[3];uop_v_r<=v1;
   if(fch_c[0])h0<=halt_c;
   h1<=h0;cfg_selected<=sel_n;fragment<=frag_n;
   write_v<={fw && cfg_bank==2'd2,fw && cfg_bank==2'd1,fw && cfg_bank==2'd0};ph<=ph_n;
   cfgv_q<=cfg[36];start_q<=start;
   busy_d1<=busy_r;busy_d2<=busy_d1;busy_d3<=busy_d2;done_d1<=done_r;done_d2<=done_d1;done_d3<=done_d2;
   start_d1<=start_q;start_d2<=start_d1;start_d3<=start_d2;
  end
 // G1: fetch copies, uop_pc, mode predecode, metadata valid-set enables
 always @(posedge clk or negedge rcp[1])
  if(!rcp[1])begin fch_c<=0;fv_c<=0;uop_pc_r<=0;md_q<=0;en_ml<=0;end
  else begin
   fch_c<={4{fch_n}};fv_c<={4{fch_c[0]}};uop_pc_r<=pc1;
   md_q<={cfg[36] && cfg[35:32]==4'd3,cfg[36] && cfg[35:32]==4'd2,cfg[36] && cfg[35:32]==4'd1,cfg[36] && cfg[35:32]==4'd0};
   for(integer g=0;g<8;g=g+1)begin
    en_ml[g]<=c2 && m2_ok && cfg_row[7:5]==g;
   end
  end
 // G2: iteration (32)
 always @(posedge clk or negedge rcp[2]) if(!rcp[2])iteration<=0;else iteration<=it1;
 // G3: bank-0 mask + programme-word valid-set enables (28)
 always @(posedge clk or negedge rcp[3])
  if(!rcp[3])begin vm0<=0;en_w0<=0;en_w1<=0;end
  else begin
   vm0<={16{fv_c[0]}};
   for(integer g=0;g<8;g=g+1)begin
    en_w0[g]<=fw && cfg_bank==2'd0 && cfg_row[7:5]==g;en_w1[g]<=fw && cfg_bank==2'd1 && cfg_row[7:5]==g;

   end
  end
 // G4: bank-1 mask, metadata write, effective phase (25)
 always @(posedge clk or negedge rcp[4])
  if(!rcp[4])begin vm1<=0;mw_c<=0;p0_c<=2'b11;p1_c<=0;p2_c<=0;end
  else begin vm1<={16{fv_c[1]}};mw_c<={3{mw_x}};p0_c<={2{phe_x==2'd0}};p1_c<={2{phe_x==2'd1}};p2_c<={2{phe_x==2'd2}};end
 // G5: bank-2 mask, forwarding, prime C (28)
 always @(posedge clk or negedge rcp[5])
  if(!rcp[5])begin vm2<=0;fwt_c<=0;fwn_c<=0;pe1_c<=0;end
  else begin
   vm2<={16{fv_c[2]}};
   fwt_c<={4{upd_x && r_lid(rt_n)==rc_n[6:2]}};fwn_c<={4{upd_x && r_lid(rn_n)==rc_n[6:2]}};
   pe1_c<={4{!mw_x && !adv_x && phe_x==2'd1}};
  end
 // G6: start accept + prime CT / CN (27)
 always @(posedge clk or negedge rcp[6])
  if(!rcp[6])begin sacc_c<=0;pe2_c<=0;end
  else begin sacc_c<={19{sacc_x}};pe2_c<={8{!mw_x && !adv_x && phe_x==2'd2}};end
 // G7: advance (19)
 always @(posedge clk or negedge rcp[7]) if(!rcp[7])adv_c<=0;else adv_c<={19{adv_x}};
 // G8: pc1 hold; G29..G31: it1 hold (above).  Assembly enables need no reset: every slot is rewritten after a select.
 // G9..G28: row-valid bits, 20 groups of 32 (set one edge after the cfg word)
 wire [7:0] envec[0:4];
 assign envec[0]=en_w0;assign envec[1]=en_w1;assign envec[2]=en_w2;assign envec[3]=en_ml;assign envec[4]=en_mh;
 wire [255:0] vbits[0:4];
 for(genvar t=0;t<5;t=t+1)begin:g_vt
  for(genvar g=0;g<8;g=g+1)begin:g_vg
   reg [31:0] v;
   always @(posedge clk or negedge rcp[9+t*8+g])
    if(!rcp[9+t*8+g])v<=32'd0;else v<=v | ({32{envec[t][g]}} & ((t<3)?rh_q0:rh_q1));
   assign vbits[t][g*32+:32]=v;
  end
 end
 assign rowok=vbits[0] & vbits[1] & vbits[2] & vbits[3] & vbits[4];
 // ROWS256 adds20 row-valid reset groups and separate8-bit set-enable leaves.
 always @(posedge clk or negedge rcp[52])
  if(!rcp[52])en_mh<=0;else for(integer g=0;g<8;g=g+1)en_mh[g]<=c3 && m3_ok && cfg_row[7:5]==g;
 always @(posedge clk or negedge rcp[53])
  if(!rcp[53])en_w2<=0;else for(integer g=0;g<8;g=g+1)en_w2[g]<=fw && cfg_bank==2'd2 && cfg_row[7:5]==g;
 // ---------------- outputs ----------------
 assign busy=busy_r | start_q;assign done=done_r;assign fault=fault_r;assign uop_v=uop_v_r;assign uop_pc=uop_pc_r;
 assign tap_iteration=iteration;
 assign tap_steps={uop[1407+:8],uop[1318+:16],uop[1350+:16],uop[1366+:16],uop[1302+:16],uop[1334+:16]};
 always @(posedge clk)uop_d1<=uop;
endmodule

// 512-b programme bank, v8: two ot_sram_1r1w_256x256_m2_r2c2 (bits 255:0 / 511:256), macro read at the fetch
// edge, data registered on the next edge AND-masked by 16 v1 copies (one per 32 bits): data = v1 ? word : 0.
module ot_hgi_coll_program_bank256m(
 input wire clk,read_v,write_v,
 input wire [7:0] read_row,write_row,
 input wire [511:0] write_data,
 input wire [15:0] vm,
 output reg [511:0] data
);
 wire [255:0] rq_lo,rq_hi;
 ot_sram_1r1w_256x256_m2_r2c2 u_sram_lo(
  .clk(clk),.r_ce_in(read_v),.r_addr_in(read_row),.rd_out(rq_lo),
  .w_ce_in(write_v),.w_addr_in(write_row),.wd_in(write_data[255:0]),.w_mask_in({256{1'b1}}),
  .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 ot_sram_1r1w_256x256_m2_r2c2 u_sram_hi(
  .clk(clk),.r_ce_in(read_v),.r_addr_in(read_row),.rd_out(rq_hi),
  .w_ce_in(write_v),.w_addr_in(write_row),.wd_in(write_data[511:256]),.w_mask_in({256{1'b1}}),
  .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 wire [511:0] rq={rq_hi,rq_lo};
 for(genvar j=0;j<16;j=j+1)begin:g_m
  always @(posedge clk)data[j*32+:32]<={32{vm[j]}} & rq[j*32+:32];
 end
endmodule
`default_nettype wire
