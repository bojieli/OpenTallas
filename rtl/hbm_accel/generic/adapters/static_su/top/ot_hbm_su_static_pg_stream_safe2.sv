`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// LH-PGVM 2026-10-19: PGSTREAM SAFE2 -- the 14 roots > 32 loads left by the regional bridge source (47d9b210c, r3 census:
// bridge_rst_n 1,726; tap write/read selects 564/564/36/36; tap reset 92; leaf reset 73; inject decode/select
// 83/82/81/81/41/41/35) are removed by SOURCE structure, with every data, valid, fault, reset and seam edge unchanged:
//   * bridge_rst_n / rst_n: the kit lands both in ONE face stage (spec reset_landing.stages 1); this source adds a
//     balanced tree: face flop -> kept stage-A cells -> one kept terminal cell PER LOAD REGION (bridge request/return
//     regions, done/monitor, inject regions, MUT14 term).  Serial-domain terminals are clk_ctl flops; stream-domain
//     terminals are pg_clk flops fed by serial feeders, so BOTH domains leave reset on the same coincident edge 12q
//     after the face flop (the seam windows' assumption).  rst_n: two serial source stages (serial loads only).
//   * leaf / tap stream reset synchronisers: stage 1 unchanged, stage 2 replicated as kept cells, one per load group
//     (leaf: read calendar+fault / write calendar per bank leaf, fault publication; tap: control, read calendar, write
//     calendar, write-select copies per tap bank).  Same two pg_clk ages.
//   * tap selects: write_d / read_d payload muxes use kept per-region select copies (14-bit write regions, 8-bit read
//     regions) sampled from local_write / local_read on the same edge as write_d / read_d (same reset).
//   * inject: five kept group-aligned regions per side ({v[g],row g} for g=0..3, {bad}); each owns its slot counter
//     (sp / sq, same reset and recurrence) and, on the stream side, its own decode cone (10-bit bank enables / selects).
//   * bridge_s monitor: verbatim equations with two reset groups (r3: 46 loads on one terminal).
// Equivalence: tb_hbm_su_pg_stream_safe2 (lockstep against the current two-root ot_hbm_su_static_pg_stream, the kit's
// remaining reset stages modelled in the bench for the reference) + the per-group seam windows + all causal mutants.
// Kept cells are distinct keep_hierarchy paramodules (ID), so no optimisation merges them back.
// ---------------------------------------------------------------------------------------------------------------------

(* keep_hierarchy = 1 *) module ot_pgs_rst_cell #(parameter integer ID=0)(input wire clk, input wire d, output wire q);
 (* keep *) reg r;
 always @(posedge clk) r <= d;
 assign q = r;
endmodule

(* keep_hierarchy = 1 *) module ot_pgs_sel_cell #(parameter integer ID=0)(input wire clk, input wire rst_n, input wire d,
 output wire q);
 (* keep *) reg r;
 always @(posedge clk or negedge rst_n) if(!rst_n) r <= 1'b0; else r <= d;
 assign q = r;
endmodule

// face flop -> NA stage-A cells -> N terminal cells (terminal i on stage-A cell i mod NA: <= BR terminals each)
module ot_pgs_rst_tree #(parameter integer N=8, BR=32, BASE=0)(input wire clk, input wire rin, output wire [N-1:0] t);
 localparam integer NA=(N+BR-1)/BR;
 wire [NA-1:0] a;
 for(genvar i=0;i<NA;i=i+1) begin:ga
  ot_pgs_rst_cell #(.ID(BASE+i)) u(.clk(clk),.d(rin),.q(a[i]));
 end
 for(genvar i=0;i<N;i=i+1) begin:gt
  ot_pgs_rst_cell #(.ID(BASE+NA+i)) u(.clk(clk),.d(a[i%NA]),.q(t[i]));
 end
endmodule

// ---- bridge halves: the 47d9b210c regional bodies, one terminal reset per region
module ot_hbm_pgs_bridge_q_safe2 #(
 parameter integer RQ_BITS=17,WQ_BITS=281,RR_BITS=257,READ_RETURN=10,WRITE_RETURN=7,MUT=0,
 parameter integer NREQ=(RQ_BITS+WQ_BITS+6)/7, NRET=(RR_BITS+14)/15, NT=NREQ+NRET+1
)(input wire serial_clk, input wire [NT-1:0] rst_t,
 input wire [RQ_BITS-1:0] serial_rq,input wire [WQ_BITS-1:0] serial_wq,
 output wire [RR_BITS-1:0] serial_rr,output wire serial_done,
 output wire [RQ_BITS-1:0] rq_b0,rq_b1,output wire [WQ_BITS-1:0] wq_b0,wq_b1,
 input wire [RR_BITS-1:0] rr_b0,rr_b1,input wire dn_b0,dn_b1);
 wire [RQ_BITS+WQ_BITS-1:0] request={serial_wq,serial_rq};
 wire [RQ_BITS+WQ_BITS-1:0] bank0,bank1;
 assign {wq_b0,rq_b0}=bank0; assign {wq_b1,rq_b1}=bank1;
 for(genvar r=0;r<NREQ;r=r+1)begin:req
  localparam integer W=((RQ_BITS+WQ_BITS-r*7)>7)?7:RQ_BITS+WQ_BITS-r*7;
  ot_hbm_pgs_request_q_region #(.W(W),.ID(r),.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MUT(MUT)) u_copy(
   .clk(serial_clk),.rst_n(rst_t[r]),.d(request[r*7+:W]),.b0(bank0[r*7+:W]),.b1(bank1[r*7+:W]));
 end
 for(genvar r=0;r<NRET;r=r+1)begin:ret
  localparam integer W=((RR_BITS-r*15)>15)?15:RR_BITS-r*15;
  ot_hbm_pgs_return_q_region #(.W(W),.ID(r),.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MUT(MUT)) u_copy(
   .clk(serial_clk),.rst_n(rst_t[NREQ+r]),.b0(rr_b0[r*15+:W]),.b1(rr_b1[r*15+:W]),.d(serial_rr[r*15+:W]));
 end
 ot_hbm_su_multirate_bridge_q #(.RQ_BITS(1),.WQ_BITS(1),.RR_BITS(1),.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MUT(MUT)) u_done(
  .serial_clk(serial_clk),.rst_n(rst_t[NT-1]),.serial_rq(1'b0),.serial_wq(1'b0),.serial_rr(),.serial_done(serial_done),
  .rq_b0(),.rq_b1(),.wq_b0(),.wq_b1(),.rr_b0(1'b0),.rr_b1(1'b0),.dn_b0(dn_b0),.dn_b1(dn_b1));
 wire rsel = ret[0].u_copy.u_q.rsel;
endmodule

module ot_hbm_pgs_bridge_s_safe2 #(
 parameter integer RQ_BITS=17,WQ_BITS=281,RR_BITS=257,READ_RETURN=10,WRITE_RETURN=7,MUT=0,
 parameter integer NREQ=(RQ_BITS+WQ_BITS+14)/15, NRET=(RR_BITS+14)/15, NT=NREQ+NRET+2
)(input wire stream_clk, input wire [NT-1:0] rst_t,
 input wire [RQ_BITS-1:0] rq_b0,rq_b1,input wire [WQ_BITS-1:0] wq_b0,wq_b1,
 output wire [RR_BITS-1:0] rr_b0,rr_b1,output wire dn_b0,dn_b1,
 output wire [RQ_BITS-1:0] stream_rq,output wire [WQ_BITS-1:0] stream_wq,
 input wire [RR_BITS-1:0] stream_rr,input wire stream_done,
 output wire fault);
 wire [RQ_BITS+WQ_BITS-1:0] bank0={wq_b0,rq_b0},bank1={wq_b1,rq_b1};
 wire [RQ_BITS+WQ_BITS-1:0] launched;
 assign {stream_wq,stream_rq}=launched;
 for(genvar r=0;r<NREQ;r=r+1)begin:req
  localparam integer W=((RQ_BITS+WQ_BITS-r*15)>15)?15:RQ_BITS+WQ_BITS-r*15;
  ot_hbm_pgs_request_s_region #(.W(W),.ID(r),.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MUT(MUT)) u_copy(
   .clk(stream_clk),.rst_n(rst_t[r]),.b0(bank0[r*15+:W]),.b1(bank1[r*15+:W]),.d(launched[r*15+:W]));
 end
 for(genvar r=0;r<NRET;r=r+1)begin:ret
  localparam integer W=((RR_BITS-r*15)>15)?15:RR_BITS-r*15;
  ot_hbm_pgs_return_s_region #(.W(W),.ID(r),.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MUT(MUT)) u_copy(
   .clk(stream_clk),.rst_n(rst_t[NREQ+r]),.d(stream_rr[r*15+:W]),.b0(rr_b0[r*15+:W]),.b1(rr_b1[r*15+:W]));
 end
 ot_pgs_bridge_s_mon2 #(.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MUT(MUT)) u_monitor(
  .stream_clk(stream_clk),.rst_a(rst_t[NT-2]),.rst_b(rst_t[NT-1]),.rq_b0(rq_b0[RQ_BITS-1]),.rq_b1(rq_b1[RQ_BITS-1]),
  .wq_b0(wq_b0[WQ_BITS-1]),.wq_b1(wq_b1[WQ_BITS-1]),.rr_b0(),.rr_b1(),.dn_b0(dn_b0),.dn_b1(dn_b1),
  .stream_rq(),.stream_wq(),.stream_rr(stream_rr[RR_BITS-1]),.stream_done(stream_done),.fault(fault));
 wire rd_v = req[0].u_copy.u_s.rd_v;
 wire rd_b = req[0].u_copy.u_s.rd_b;
endmodule

// ---- bridge_s valid/calendar monitor (ot_hbm_su_multirate_bridge_s at 1-bit widths, verbatim equations) with two reset
//      groups: rst_a phase / warm / read pipe, rst_b write pipe / active pipe / fault (r3 census: one 46-load reset)
module ot_pgs_bridge_s_mon2 #(parameter integer READ_RETURN=10,WRITE_RETURN=7,MUT=0)(
 input wire stream_clk, input wire rst_a, input wire rst_b,
 input wire rq_b0,rq_b1,wq_b0,wq_b1,
 output reg rr_b0,rr_b1,output reg dn_b0,dn_b1,
 output reg stream_rq,output reg stream_wq,
 input wire stream_rr,input wire stream_done,
 output reg fault);
 localparam integer RP=READ_RETURN+2, WP=WRITE_RETURN+2;
 reg [3:0] phase;
 reg [4:0] stream_warm;
 reg [RP-1:0] active_pipe,read_pipe;
 reg [WP-1:0] write_pipe;
 function automatic [1:0] slot_for_phase(input [3:0] p);
  reg [3:0] n;
  begin
   n=3*{2'b0,p[3:2]};
   if(p[1:0]==3)n=n+1;
   if(p[1:0]==0)n=n-1;
   slot_for_phase=n[1:0];
  end
 endfunction
 wire active=phase[1:0]!=1 && stream_warm>=2;
 wire [1:0] lslot=slot_for_phase(phase), rslot=slot_for_phase(phase-4'(RP)), dslot=slot_for_phase(phase-4'(WP));
 wire lsel=lslot[0] ^ (MUT==2);
 wire rsel=rslot[0];
 wire dsel=dslot[0];
 wire rq_sel = lsel ? rq_b1 : rq_b0;
 wire wq_sel = lsel ? wq_b1 : wq_b0;
 wire [1:0] nslot=slot_for_phase(phase+4'd1);
 wire nsel=nslot[0];
 reg rq_pre, wq_pre;
 always @(posedge stream_clk) begin rq_pre <= nsel ? rq_b1 : rq_b0; wq_pre <= nsel ? wq_b1 : wq_b0; end
 wire rq_pick = (MUT==12) ? rq_pre : rq_sel;
 wire wq_pick = (MUT==12) ? wq_pre : wq_sel;
 always @(posedge stream_clk) begin
  stream_rq<=active ? rq_pick : 1'b0;
  stream_wq<=active ? wq_pick : 1'b0;
 end
 always @(posedge stream_clk)begin
  if(active_pipe[RP-1])begin if(rsel)rr_b1<=stream_rr; else rr_b0<=stream_rr; end
  if(active_pipe[WP-1])begin if(dsel)dn_b1<=stream_done; else dn_b0<=stream_done; end
 end
 always @(posedge stream_clk or negedge rst_a)begin
  if(!rst_a)begin
   phase<=0;stream_warm<=0;read_pipe<=0;
  end else begin
   phase<=phase+1'b1;if(stream_warm<16)stream_warm<=stream_warm+1'b1;
   read_pipe<={read_pipe[RP-2:0],active && rq_pick};
  end
 end
 always @(posedge stream_clk or negedge rst_b)begin
  if(!rst_b)begin
   active_pipe<=0;write_pipe<=0;fault<=0;
  end else begin
   active_pipe<={active_pipe[RP-2:0],active};
   write_pipe<={write_pipe[WP-2:0],active && wq_pick};
   if(stream_rr!==read_pipe[RP-1] || stream_done!==write_pipe[WP-1])fault<=1;
  end
 end
endmodule

// ---- VM bank leaf (ot_hbm_su_static_vm_bank_leaf_s) with two reset groups: read calendar + fault / write calendar
module ot_pgs_bank_leaf_s_safe2 #(parameter integer READ_RETURN=10,WRITE_RETURN=7)(
 input wire clk, input wire rst_a, input wire rst_b,
 input wire [1:0] qid, input wire [2:0] b,
 input wire [16:0] su_rq, input wire [280:0] su_wq,
 output wire [256:0] su_rr, output wire su_w_done,
 output wire [16:0] lg_rq, output wire [280:0] lg_wq,
 input wire [256:0] lg_rr, input wire lg_w_done,
 output reg fault
);
 reg [READ_RETURN:0] rcal;
 reg [WRITE_RETURN:0] wcal;
 wire rq_ok=!su_rq[15]&&su_rq[14:13]==qid&&su_rq[2:0]==b;
 wire wq_ok=!su_wq[279]&&su_wq[278:277]==qid&&su_wq[266:264]==b;
 assign lg_rq=su_rq;
 assign lg_wq=su_wq;
 assign su_rr=lg_rr;
 assign su_w_done=lg_w_done;
 always @(posedge clk or negedge rst_a)
  if(!rst_a) begin fault<=1'b0; rcal<='0; end
  else begin
   rcal<={rcal[READ_RETURN-1:0],su_rq[16]};
   if(su_rq[16]&&!rq_ok)fault<=1'b1;
   if(su_wq[280]&&!wq_ok)fault<=1'b1;
   if(lg_rr[256]!==rcal[READ_RETURN])fault<=1'b1;
   if(lg_w_done!==wcal[WRITE_RETURN])fault<=1'b1;
  end
 always @(posedge clk or negedge rst_b)
  if(!rst_b) wcal<='0;
  else wcal<={wcal[WRITE_RETURN-1:0],su_wq[280]};
endmodule

// ---- LG tap bank (ot_hbm_vm_lg_static_bank, LOCAL_SPLIT=1 / RET_PIN=0 / MUT=0 form) with kept select copies and
//      four reset groups: rst_c control (+ read-select copies), rst_r read calendar, rst_w write calendar,
//      rst_s write-select copies.
module ot_pgs_tap_bank_safe2 #(parameter integer READ_RETURN=10,WRITE_RETURN=7,IDB=0)(
 input wire clk, input wire rst_c, input wire rst_r, input wire rst_w, input wire rst_s,
 input wire [16:0] local_rq,far_rq,
 input wire [280:0] local_wq,far_wq,
 input wire local_read,local_write,
 output wire [16:0] near_rq,
 output wire [280:0] near_wq,
 input wire [256:0] near_rr,
 input wire near_w_done,
 output wire [256:0] local_rr,far_rr,
 output reg local_w_done,far_w_done,
 output reg fault
);
 initial if(READ_RETURN<3||WRITE_RETURN<3)$fatal(1,"LOCAL_SPLIT needs returns >= 3");
 localparam integer NWS=20;          // 280 payload bits / 14
 localparam integer NRS=2;           // 16 sector bits / 8
 reg [16:0] lrq_d,frq_d;
 reg [280:0] lwq_d,fwq_d;
 reg lrq_v,frq_v,lwq_v,fwq_v,read_d,write_d;
 reg [15:0] rq_d;
 reg [279:0] wq_d;
 reg rq_v,wq_v;
 reg [256:0] rr_d,return_d;
 reg rr_v,done_d,local_rr_v,far_rr_v;
 reg [READ_RETURN-2:0] rcal;         // read_calendar[0..READ_RETURN-2] (entry READ_RETURN-1 is never read)
 reg [WRITE_RETURN-2:0] wcal;
 wire read_due=rcal[READ_RETURN-2];
 wire write_due=wcal[WRITE_RETURN-2];
 wire [255:0] return_l;
 ot_hbm_vm_lg_keep_reg u_ret_l(.clk(clk),.d(rr_d[255:0]),.q(return_l));
 wire [NRS-1:0] rsel; wire [NWS-1:0] wsel;
 for(genvar r=0;r<NRS;r=r+1)begin:g_rs
  ot_pgs_sel_cell #(.ID(IDB*64+r)) u(.clk(clk),.rst_n(rst_c),.d(local_read),.q(rsel[r]));
  always @(posedge clk) rq_d[r*8+:8] <= rsel[r] ? lrq_d[r*8+:8] : frq_d[r*8+:8];
 end
 for(genvar r=0;r<NWS;r=r+1)begin:g_ws
  ot_pgs_sel_cell #(.ID(IDB*64+32+r)) u(.clk(clk),.rst_n(rst_s),.d(local_write),.q(wsel[r]));
  always @(posedge clk) wq_d[r*14+:14] <= wsel[r] ? lwq_d[r*14+:14] : fwq_d[r*14+:14];
 end
 always @(posedge clk) begin
  lrq_d<=local_rq; frq_d<=far_rq; lwq_d<=local_wq; fwq_d<=far_wq;
  rr_d<=near_rr; return_d<=rr_d;
 end
 always @(posedge clk or negedge rst_c)
  if(!rst_c) begin
   lrq_v<=0;frq_v<=0;lwq_v<=0;fwq_v<=0;read_d<=0;write_d<=0;
   rq_v<=0;wq_v<=0;rr_v<=0;done_d<=0;
   local_rr_v<=0;far_rr_v<=0;local_w_done<=0;far_w_done<=0;fault<=0;
  end else begin
   read_d<=local_read; write_d<=local_write; done_d<=near_w_done;
   lrq_v<=local_rq[16]; frq_v<=far_rq[16]; lwq_v<=local_wq[280]; fwq_v<=far_wq[280];
   rr_v<=near_rr[256];
   rq_v<=read_d?lrq_v:frq_v;
   wq_v<=write_d?lwq_v:fwq_v;
   local_rr_v<=read_due;
   far_rr_v<=rr_v&&!read_due;
   local_w_done<=write_due;
   far_w_done<=done_d&&!write_due;
   if((lrq_v&&!read_d)||(lwq_v&&!write_d)||(read_d&&frq_v)||(write_d&&fwq_v)||
      (read_due&&!rr_v)||(write_due&&!done_d)) fault<=1;
  end
 always @(posedge clk or negedge rst_r)
  if(!rst_r) rcal<='0; else rcal<={rcal[READ_RETURN-3:0], read_d&&lrq_v};
 always @(posedge clk or negedge rst_w)
  if(!rst_w) wcal<='0; else wcal<={wcal[WRITE_RETURN-3:0], write_d&&lwq_v};
 assign near_rq={rq_v,rq_d};
 assign near_wq={wq_v,wq_d};
 assign local_rr={local_rr_v,return_l};
 assign far_rr={far_rr_v,return_d[255:0]};
endmodule

// ---- inject regions (41-bit word {bad,row36,v4} -> bits [LO +: W])
// Regions are group-aligned (M = the bits a region owns): {v[g], row group g} for g = 0..3, {bad};
// unowned bits are masked at the parent, so synthesis drops their flops and their decode cone.
(* keep_hierarchy = 1 *) module ot_pgs_inj_s_region #(parameter [40:0] M=41'h0,parameter integer MUT=0)(
 input wire clk, input wire rst_n, input wire [161:0] ij, input wire [1:0] g_id, input wire b39_on,
 output wire [40:0] b0, output wire [40:0] b1, output wire [40:0] b2);
 reg [40:0] q0, q1, q2;
 assign b0 = q0 & M; assign b1 = q1 & M; assign b2 = q2 & M;
 reg [1:0] sp;
 always @(posedge clk or negedge rst_n) if(!rst_n) sp<=2'd0; else sp<=sp+2'd1;
 reg [3:0] v; reg [35:0] row; reg bad; integer k;
 always @* begin
  v=0; row=0; bad=0;
  for(k=0;k<4;k=k+1) begin : dec
   reg [39:0] a, lo; reg on; reg [1:0] grp;
   a = ij[40*k+:40]; lo = ij[80*(k/2)+:40];
   on = ij[160+(k/2)] && !(b39_on && lo[39] && MUT!=9) && a[5:4]==g_id;
   grp = {a[6],a[3]};
   if(on) begin
    if(v[grp] && row[9*grp+:9]!=a[15:7]) bad=1'b1;
    v[grp]=1'b1; row[9*grp+:9]=a[15:7];
   end
  end
 end
 wire [40:0] w = {bad,row,v};
 always @(posedge clk) begin
  if(sp==2'd0) q0 <= w;
  if(sp==2'd1) q1 <= w;
  if(sp==2'd3) q2 <= w;
 end
endmodule

(* keep_hierarchy = 1 *) module ot_pgs_inj_q_region #(parameter [40:0] M=41'h0,parameter integer MUT=0)(
 input wire clk, input wire rst_n, input wire [40:0] b0, input wire [40:0] b1, input wire [40:0] b2,
 output wire [40:0] q, output wire [1:0] ib_o);
 reg [40:0] qr;
 assign q = qr & M;
 reg [1:0] sq;
 always @(posedge clk or negedge rst_n) if(!rst_n) sq<=2'd0; else sq<=(sq==2'd2)?2'd0:sq+2'd1;
 wire [1:0] ib0 = (sq==2'd1)?2'd0:(sq==2'd2)?2'd1:2'd2;
 wire [1:0] ib = (MUT==8) ? ((ib0==2'd2)?2'd0:ib0+2'd1) : ib0;
 always @(posedge clk) qr <= (ib==2'd0)?b0:(ib==2'd1)?b1:b2;
 assign ib_o = ib;
endmodule

// ---- serial half
module ot_hbm_su_static_pg_stream_q_safe2 #(
 parameter integer READ_RETURN=10,WRITE_RETURN=7,MUT=0,NTQ=62
)(
 input wire clk_ctl,
 input wire rst_n,                       // landed (face + 2 source stages)
 input wire [2*NTQ-1:0] brt,             // bridge reset terminals
 input wire [4:0] brt_i,                 // inject region reset terminals
 input wire [2*30-1:0] vmr_cmd,
 input wire [2*281-1:0] su_wq,
 output wire [2*257-1:0] su_rr,
 output wire [3:0] ij_v, output wire [35:0] ij_row, output wire ij_bad,
 output wire pg_fault,
 output wire [2*17-1:0] rq_b0, rq_b1,
 output wire [2*281-1:0] wq_b0, wq_b1,
 input wire [2*257-1:0] rr_b0, rr_b1,
 input wire [40:0] ijb0, ijb1, ijb2,
 input wire pgf_s,
 output wire rc_leaf, output wire rc_tap
);
 wire rst_s;
 ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rst(.clk(clk_ctl),.rst_n_in(rst_n),.rst_n(rst_s));
 reg rcl, rct;
 always @(posedge clk_ctl) begin rcl <= rst_s; rct <= rst_n; end
 assign rc_leaf = rcl; assign rc_tap = rct;
 for(genvar h=0;h<2;h=h+1)begin:g_br
  ot_hbm_pgs_bridge_q_safe2 #(.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MUT((MUT==1||MUT==3||MUT==6)?MUT:0)) u_bq(
   .serial_clk(clk_ctl),.rst_t(brt[h*NTQ+:NTQ]),
   .serial_rq({vmr_cmd[h*30+29],vmr_cmd[h*30+13+:16]}),.serial_wq(su_wq[h*281+:281]),
   .serial_rr(su_rr[h*257+:257]),.serial_done(),
   .rq_b0(rq_b0[h*17+:17]),.rq_b1(rq_b1[h*17+:17]),.wq_b0(wq_b0[h*281+:281]),.wq_b1(wq_b1[h*281+:281]),
   .rr_b0(rr_b0[h*257+:257]),.rr_b1(rr_b1[h*257+:257]),.dn_b0(1'b0),.dn_b1(1'b0));
 end
 localparam [40:0] IM0 = 41'h00000001FF1, IM1 = 41'h000003FE002, IM2 = 41'h0007FC00004, IM3 = 41'h0FF80000008, IM4 = 41'h10000000000;
 wire [40:0] ijr [0:4];
 wire [1:0] ibr [0:4];
 for(genvar r=0;r<5;r=r+1)begin:g_ij
  localparam [40:0] M = (r==0)?IM0:(r==1)?IM1:(r==2)?IM2:(r==3)?IM3:IM4;
  ot_pgs_inj_q_region #(.M(M),.MUT(MUT==8?8:0)) u_r(.clk(clk_ctl),.rst_n(brt_i[r]),
   .b0(ijb0 & M),.b1(ijb1 & M),.b2(ijb2 & M),.q(ijr[r]),.ib_o(ibr[r]));
 end
 wire [40:0] ijq = ijr[0] | ijr[1] | ijr[2] | ijr[3] | ijr[4];
 wire [1:0] ib = ibr[0];                 // bench window probe (all three regions are exact copies)
 assign ij_v=ijq[3:0]; assign ij_row=ijq[39:4]; assign ij_bad=ijq[40];
 reg [1:0] fs;
 always @(posedge clk_ctl or negedge rst_n) if(!rst_n) fs<=2'd0; else fs<={fs[0],pgf_s};
 assign pg_fault=fs[1];
endmodule

// ---- stream half
module ot_hbm_su_static_pg_stream_s_safe2 #(
 parameter integer QID=1,G=2,READ_RETURN=10,WRITE_RETURN=7,MUT=0,B39_NOOP=(QID==0),STRAP=1,FAULT_REG=0,NTS=40
)(
 input wire pg_clk,
 input wire [2*NTS-1:0] brt,
 input wire [4:0] brt_i,
 input wire brt_m,                       // MUT 14 only (cross-reset mutant)
 input wire [3:0] pos,
 input wire [2*17-1:0] rq_b0, rq_b1,
 input wire [2*281-1:0] wq_b0, wq_b1,
 output wire [2*257-1:0] rr_b0, rr_b1,
 output wire [40:0] ijb0, ijb1, ijb2,
 output wire pgf_s,
 input wire rc_leaf, input wire rc_tap,
 input wire [1:0] inj_rd,
 input wire [159:0] inj_addr,
 output wire [33:0] lg_rq,
 output wire [561:0] lg_wq,
 input wire [513:0] lg_rr,
 input wire [1:0] lg_w_done,
 input wire [1:0] lg_read,lg_write,
 input wire [33:0] far_rq,
 input wire [561:0] far_wq,
 output wire [513:0] far_rr,
 output wire [1:0] far_w_done,
 output wire lg_fault
);
 wire [1:0] q_id=(STRAP!=0)?pos[3:2]:2'(QID);
 wire [1:0] g_id=(STRAP!=0&&MUT!=11)?pos[1:0]:2'(G);
 wire b39_on=(STRAP!=0)?(q_id==2'd0):(B39_NOOP!=0);
 // reset synchronisers: first stage as before, second stage replicated (same two pg_clk ages)
 reg rq_s0, rs_s0;
 always @(posedge pg_clk) begin rq_s0 <= rc_leaf; rs_s0 <= rc_tap; end
 wire [4:0] lr; wire [7:0] tr;
 for(genvar i=0;i<5;i=i+1)begin:g_lr ot_pgs_rst_cell #(.ID(9000+i)) u(.clk(pg_clk),.d(rq_s0),.q(lr[i])); end
 for(genvar i=0;i<8;i=i+1)begin:g_tr ot_pgs_rst_cell #(.ID(9100+i)) u(.clk(pg_clk),.d(rs_s0),.q(tr[i])); end
 wire leaf_rst_n = lr[4];                // fault-publication copy (also the bench probe)
 wire [33:0] s_rq; wire [561:0] s_wq; wire [513:0] s_rr; wire [1:0] s_done;
 wire [33:0] leaf_rq; wire [561:0] leaf_wq; wire [513:0] leaf_rr; wire [1:0] leaf_done, leaf_fault, bridge_fault;
 for(genvar h=0;h<2;h=h+1)begin:g_leaf
  ot_hbm_pgs_bridge_s_safe2 #(.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MUT((MUT==2||MUT==12)?MUT:0)) u_bs(
   .stream_clk(pg_clk),.rst_t(brt[h*NTS+:NTS]),
   .rq_b0(rq_b0[h*17+:17]),.rq_b1(rq_b1[h*17+:17]),.wq_b0(wq_b0[h*281+:281]),.wq_b1(wq_b1[h*281+:281]),
   .rr_b0(rr_b0[h*257+:257]),.rr_b1(rr_b1[h*257+:257]),.dn_b0(),.dn_b1(),
   .stream_rq(leaf_rq[h*17+:17]),.stream_wq(leaf_wq[h*281+:281]),
   .stream_rr(leaf_rr[h*257+:257]),.stream_done(leaf_done[h]),.fault(bridge_fault[h]));
  ot_pgs_bank_leaf_s_safe2 #(.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN)) u_leaf(
   .clk(pg_clk),.rst_a(lr[2*h]),.rst_b(lr[2*h+1]),.qid(q_id),.b({g_id,1'(h)}),.su_rq(leaf_rq[h*17+:17]),.su_wq(leaf_wq[h*281+:281]),
   .su_rr(leaf_rr[h*257+:257]),.su_w_done(leaf_done[h]),.lg_rq(s_rq[h*17+:17]),.lg_wq(s_wq[h*281+:281]),
   .lg_rr(s_rr[h*257+:257]),.lg_w_done(s_done[h]),.fault(leaf_fault[h]));
 end
 wire pgf_raw=(|leaf_fault)||(|bridge_fault);
 generate if(FAULT_REG!=0) begin:g_pgf_reg
  reg pgf_q;
  always @(posedge pg_clk)
   if(!leaf_rst_n || (MUT==14 && !brt_m)) pgf_q<=1'b0;
   else pgf_q <= (MUT==13) ? !pgf_raw : pgf_raw;
  assign pgf_s=pgf_q;
 end else begin:g_pgf_legacy
  assign pgf_s=pgf_raw;
 end endgenerate
 wire [1:0] tf;
 for(genvar b=0;b<2;b=b+1)begin:g_tap
  ot_pgs_tap_bank_safe2 #(.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.IDB(b)) u_tap(
   .clk(pg_clk),.rst_c(tr[4*b]),.rst_r(tr[4*b+1]),.rst_w(tr[4*b+2]),.rst_s(tr[4*b+3]),
   .local_rq(s_rq[b*17+:17]),.far_rq(far_rq[b*17+:17]),.local_wq(s_wq[b*281+:281]),.far_wq(far_wq[b*281+:281]),
   .local_read(lg_read[b]),.local_write(lg_write[b]),.near_rq(lg_rq[b*17+:17]),.near_wq(lg_wq[b*281+:281]),
   .near_rr(lg_rr[b*257+:257]),.near_w_done(lg_w_done[b]),.local_rr(s_rr[b*257+:257]),.far_rr(far_rr[b*257+:257]),
   .local_w_done(s_done[b]),.far_w_done(far_w_done[b]),.fault(tf[b]));
 end
 assign lg_fault=|tf;
 wire [161:0] ij = {inj_rd, inj_addr};
 localparam [40:0] IM0 = 41'h00000001FF1, IM1 = 41'h000003FE002, IM2 = 41'h0007FC00004, IM3 = 41'h0FF80000008, IM4 = 41'h10000000000;
 wire [40:0] s0 [0:4], s1 [0:4], s2 [0:4];
 for(genvar r=0;r<5;r=r+1)begin:g_ij
  localparam [40:0] M = (r==0)?IM0:(r==1)?IM1:(r==2)?IM2:(r==3)?IM3:IM4;
  ot_pgs_inj_s_region #(.M(M),.MUT(MUT==9?9:0)) u_r(.clk(pg_clk),.rst_n(brt_i[r]),.ij(ij),.g_id(g_id),
   .b39_on(b39_on),.b0(s0[r]),.b1(s1[r]),.b2(s2[r]));
 end
 assign ijb0 = s0[0] | s0[1] | s0[2] | s0[3] | s0[4];
 assign ijb1 = s1[0] | s1[1] | s1[2] | s1[3] | s1[4];
 assign ijb2 = s2[0] | s2[1] | s2[2] | s2[3] | s2[4];
endmodule

// ---- tile top (same ports as ot_hbm_su_static_pg_stream_split; kit lands rst_n / bridge_rst_n in ONE face stage)
module ot_hbm_su_static_pg_stream_split_safe2 #(
 parameter integer QID=1,G=2,READ_RETURN=10,WRITE_RETURN=7,MUT=0,B39_NOOP=(QID==0),STRAP=1,FAULT_REG=0
)(
 input wire clk_ctl,
 input wire pg_clk,
 input wire rst_n,
 input wire bridge_rst_n,
 input wire [3:0] pos,
 input wire [2*30-1:0] vmr_cmd,
 input wire [2*281-1:0] su_wq,
 output wire [2*257-1:0] su_rr,
 output wire [3:0] ij_v, output wire [35:0] ij_row, output wire ij_bad,
 output wire pg_fault,
 input wire [1:0] inj_rd,
 input wire [159:0] inj_addr,
 output wire [33:0] lg_rq,
 output wire [561:0] lg_wq,
 input wire [513:0] lg_rr,
 input wire [1:0] lg_w_done,
 input wire [1:0] lg_read,lg_write,
 input wire [33:0] far_rq,
 input wire [561:0] far_wq,
 output wire [513:0] far_rr,
 output wire [1:0] far_w_done,
 output wire lg_fault
);
 localparam integer NTQ=(17+281+6)/7+(257+14)/15+1;    // 62
 localparam integer NTS=(17+281+14)/15+(257+14)/15+2;  // 40 (monitor has two reset groups)
 localparam integer NQT=2*NTQ+5;                         // 129 serial-domain bridge reset terminals
 localparam integer NST=2*NTS+5+1;                       // 86 stream-domain terminals (bridge_s regions, inject_s, MUT14)
 localparam integer NBS=(NST+31)/32;                     // 3 serial feeders of the stream terminals
 // rst_n: two source stages after the face flop (old kit: 3 face stages)
 wire rst_a, rst_core;
 ot_pgs_rst_cell #(.ID(9900)) u_rst_a(.clk(clk_ctl),.d(rst_n),.q(rst_a));
 ot_pgs_rst_cell #(.ID(9901)) u_rst_t(.clk(clk_ctl),.d(rst_a),.q(rst_core));
 // bridge_rst_n: face flop (C) -> stage A (C+4q) -> serial terminals (C+8q; serial loads count from C+12q)
 //                                              -> serial feeders (C+8q) -> pg_clk terminals (C+9q; stream loads count
 //                                                 from C+12q).  Both domains leave reset on the SAME coincident edge,
 //                                                 as the seam calendar assumes (a clk_ctl-released stream reset would
 //                                                 let the stream side start one stream edge early: windows break).
 wire [NQT+NBS-1:0] bq; wire [NST-1:0] bs;
 ot_pgs_rst_tree #(.N(NQT+NBS),.BR(32),.BASE(10000)) u_brt(.clk(clk_ctl),.rin(bridge_rst_n),.t(bq));
 for(genvar i=0;i<NST;i=i+1)begin:g_bst
  ot_pgs_rst_cell #(.ID(20000+i)) u(.clk(pg_clk),.d(bq[NQT+(i%NBS)]),.q(bs[i]));
 end
 wire [33:0] rq_b0, rq_b1; wire [561:0] wq_b0, wq_b1; wire [513:0] rr_b0, rr_b1;
 wire [40:0] ijb0, ijb1, ijb2; wire pgf_s, rc_leaf, rc_tap;
 ot_hbm_su_static_pg_stream_q_safe2 #(.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MUT(MUT),.NTQ(NTQ)) u_q(
  .clk_ctl(clk_ctl),.rst_n(rst_core),.brt(bq[0+:2*NTQ]),.brt_i(bq[2*NTQ+:5]),.vmr_cmd(vmr_cmd),.su_wq(su_wq),.su_rr(su_rr),
  .ij_v(ij_v),.ij_row(ij_row),.ij_bad(ij_bad),.pg_fault(pg_fault),
  .rq_b0(rq_b0),.rq_b1(rq_b1),.wq_b0(wq_b0),.wq_b1(wq_b1),.rr_b0(rr_b0),.rr_b1(rr_b1),
  .ijb0(ijb0),.ijb1(ijb1),.ijb2(ijb2),.pgf_s(pgf_s),.rc_leaf(rc_leaf),.rc_tap(rc_tap));
 ot_hbm_su_static_pg_stream_s_safe2 #(.QID(QID),.G(G),.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MUT(MUT),
  .B39_NOOP(B39_NOOP),.STRAP(STRAP),.FAULT_REG(FAULT_REG),.NTS(NTS)) u_s(
  .pg_clk(pg_clk),.brt(bs[0+:2*NTS]),.brt_i(bs[2*NTS+:5]),.brt_m(bs[NST-1]),.pos(pos),
  .rq_b0(rq_b0),.rq_b1(rq_b1),.wq_b0(wq_b0),.wq_b1(wq_b1),.rr_b0(rr_b0),.rr_b1(rr_b1),
  .ijb0(ijb0),.ijb1(ijb1),.ijb2(ijb2),.pgf_s(pgf_s),.rc_leaf(rc_leaf),.rc_tap(rc_tap),
  .inj_rd(inj_rd),.inj_addr(inj_addr),.lg_rq(lg_rq),.lg_wq(lg_wq),.lg_rr(lg_rr),.lg_w_done(lg_w_done),
  .lg_read(lg_read),.lg_write(lg_write),.far_rq(far_rq),.far_wq(far_wq),.far_rr(far_rr),.far_w_done(far_w_done),
  .lg_fault(lg_fault));
endmodule
`default_nettype wire
