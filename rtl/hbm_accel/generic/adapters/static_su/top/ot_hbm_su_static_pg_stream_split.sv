`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// TW3-PGSTREAM 2026-10-19 (coordinator 10-19): ot_hbm_su_static_pg_stream (two-root 4:3 leaf, gate hbm_su_pg_stream_1019
// FAIL: cross_clock TT setup -126.9 rr_slot -> serial_rr and -479.3 sq -> ij decode register; a 3:4 crossing with logic
// cannot close inside one leaf) split into TWO ONE-ROOT LEAVES that abut along a banked seam:
//   ot_hbm_su_static_pg_stream_q (clk_ctl, serial; faces the slice S band): bridge serial halves (request banks written by
//     serial event n into bank n mod 2; return banks staged one serial edge early), the serial reset sources (rst relay +
//     the two reset-synchroniser source flops), the inject decode read (3 banks -> one serial register), the pg fault
//     synchroniser.
//   ot_hbm_su_static_pg_stream_s (pg_clk, stream; faces LG / far / COLL inject): bridge stream halves, the two VM bank
//     leaves, the LG tap pair (ot_hbm_vm_lg_pair_tap) with its pg_clk reset synchroniser, the leaf reset synchroniser,
//     the inject slot counter + decode written into 3 banks.
// Every seam arc is a die-level 3:4 arc with a static calendar window (bridge: see multirate_bridge_split.sv, >= 2q;
// inject banks: written at stream edges 12m / 12m+3 / 12m+9, read at serial 12m+4 / +8 / +12, rewritten one epoch later
// => setup >= 3q, rewrite-after-read >= 7q; reset sources: cdc synchronisers (2 pg_clk flops each, as before);
// pg fault: 2-flop synchroniser of a sticky flag).
// EDGES vs ot_hbm_su_static_pg_stream (lockstep tb_hbm_su_pg_stream_split; compiler/calendar deltas in lanes/H-D4G.md):
//   su_rr / VM fill, VM drain, lg_* / far_* / lg_fault, leaf + tap reset release: UNCHANGED (same serial / stream edges).
//   ij_v / ij_row / ij_bad (inject port-5 reads): +1 SERIAL edge (the slice consumes the inject read of COLL stream slot
//     j at serial edge k+1 instead of k; the old crossing had 1q / 2q / 3q windows by construction, no zero-edge banked form
//     exists without moving the slice's capture) -> inj_q +1 serial edge.
//   pg_fault: +2 serial edges (sticky, synchronised; faults never alter issue timing).
// Seam: q -> s 2 x (34 + 562) + 2 = 1,194 b; s -> q 2 x 514 + 3 x 41 + 1 = 1,152 b; total 2,346 b (the bridges'
// write-done return is unused at the slice: its banks are not carried).
// MUT (bench, must FAIL): 1/3/6 bridge_q (see bridge), 2 bridge_s, 8 inject bank read one bank late (as pg_stream MUT 8),
//      9 B39 no-op ignored (as pgslice), 12 request bank read one stream edge early (seam-window mutant, window-only).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hbm_su_static_pg_stream_q #(
 parameter integer READ_RETURN=10,WRITE_RETURN=7,MUT=0
)(
 input wire clk_ctl,
 input wire rst_n,
 input wire bridge_rst_n,
 // slice S band (serial)
 input wire [2*30-1:0] vmr_cmd,
 input wire [2*281-1:0] su_wq,
 output wire [2*257-1:0] su_rr,
 output wire [3:0] ij_v, output wire [35:0] ij_row, output wire ij_bad,
 output wire pg_fault,
 // seam (to / from pg_stream_s)
 output wire [2*17-1:0] rq_b0, rq_b1,
 output wire [2*281-1:0] wq_b0, wq_b1,
 input wire [2*257-1:0] rr_b0, rr_b1,
 input wire [40:0] ijb0, ijb1, ijb2,
 input wire pgf_s,
 output wire rc_leaf, output wire rc_tap
);
 // serial reset sources (as pg_stream: leaf = region-9 relay copy rst_s -> rc; tap = rst_n -> rc)
 wire rst_s;
 ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rst(.clk(clk_ctl),.rst_n_in(rst_n),.rst_n(rst_s));
 reg rcl, rct;
 always @(posedge clk_ctl) begin rcl <= rst_s; rct <= rst_n; end
 assign rc_leaf = rcl; assign rc_tap = rct;
 for(genvar h=0;h<2;h=h+1)begin:g_br
  ot_hbm_su_multirate_bridge_q #(.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MUT((MUT==1||MUT==3||MUT==6)?MUT:0)) u_bq(
   .serial_clk(clk_ctl),.rst_n(bridge_rst_n),
   .serial_rq({vmr_cmd[h*30+29],vmr_cmd[h*30+13+:16]}),.serial_wq(su_wq[h*281+:281]),
   .serial_rr(su_rr[h*257+:257]),.serial_done(),
   .rq_b0(rq_b0[h*17+:17]),.rq_b1(rq_b1[h*17+:17]),.wq_b0(wq_b0[h*281+:281]),.wq_b1(wq_b1[h*281+:281]),
   .rr_b0(rr_b0[h*257+:257]),.rr_b1(rr_b1[h*257+:257]),.dn_b0(1'b0),.dn_b1(1'b0));   // write-done unused at the slice
 end
 // inject: serial edge k (sq = k mod 3) registers bank (k mod 3 = 1 -> 0, 2 -> 1, 0 -> 2) = the decode the old slice
 // sampled at k (COLL stream slot j = 4m / 4m+1 / 4m+3); the slice samples it at k+1.
 reg [1:0] sq;
 always @(posedge clk_ctl or negedge bridge_rst_n) if(!bridge_rst_n) sq<=2'd0; else sq<=(sq==2'd2)?2'd0:sq+2'd1;
 wire [1:0] ib0 = (sq==2'd1)?2'd0:(sq==2'd2)?2'd1:2'd2;
 wire [1:0] ib = (MUT==8) ? ((ib0==2'd2)?2'd0:ib0+2'd1) : ib0;
 reg [40:0] ijq;
 always @(posedge clk_ctl) ijq <= (ib==2'd0)?ijb0:(ib==2'd1)?ijb1:ijb2;
 assign ij_v=ijq[3:0]; assign ij_row=ijq[39:4]; assign ij_bad=ijq[40];
 // pg fault (sticky stream flags) -> 2-flop synchroniser
 reg [1:0] fs;
 always @(posedge clk_ctl or negedge rst_n) if(!rst_n) fs<=2'd0; else fs<={fs[0],pgf_s};
 assign pg_fault=fs[1];
endmodule

module ot_hbm_su_static_pg_stream_s #(
 parameter integer QID=1,G=2,READ_RETURN=10,WRITE_RETURN=7,MUT=0,B39_NOOP=(QID==0),STRAP=1,FAULT_REG=0
)(
 input wire pg_clk,
 input wire bridge_rst_n,
 input wire [3:0] pos,
 // seam
 input wire [2*17-1:0] rq_b0, rq_b1,
 input wire [2*281-1:0] wq_b0, wq_b1,
 output wire [2*257-1:0] rr_b0, rr_b1,
 output reg [40:0] ijb0, ijb1, ijb2,
 output wire pgf_s,
 input wire rc_leaf, input wire rc_tap,
 // COLLPORT inject (stream pin slots)
 input wire [1:0] inj_rd,
 input wire [159:0] inj_addr,
 // LG side
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
 // reset synchronisers (second / third flops of the old two-root synchronisers; sources rc_leaf / rc_tap in _q)
 reg [1:0] rq_s, rs_s;
 always @(posedge pg_clk) begin rq_s <= {rq_s[0], rc_leaf}; rs_s <= {rs_s[0], rc_tap}; end
 wire leaf_rst_n = rq_s[1], tap_rst_n = rs_s[1];
 wire [33:0] s_rq; wire [561:0] s_wq; wire [513:0] s_rr; wire [1:0] s_done;
 wire [33:0] leaf_rq; wire [561:0] leaf_wq; wire [513:0] leaf_rr; wire [1:0] leaf_done, leaf_fault, bridge_fault;
 for(genvar h=0;h<2;h=h+1)begin:g_leaf
  ot_hbm_su_multirate_bridge_s #(.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MUT((MUT==2||MUT==12)?MUT:0)) u_bs(
   .stream_clk(pg_clk),.rst_n(bridge_rst_n),
   .rq_b0(rq_b0[h*17+:17]),.rq_b1(rq_b1[h*17+:17]),.wq_b0(wq_b0[h*281+:281]),.wq_b1(wq_b1[h*281+:281]),
   .rr_b0(rr_b0[h*257+:257]),.rr_b1(rr_b1[h*257+:257]),.dn_b0(),.dn_b1(),
   .stream_rq(leaf_rq[h*17+:17]),.stream_wq(leaf_wq[h*281+:281]),
   .stream_rr(leaf_rr[h*257+:257]),.stream_done(leaf_done[h]),.fault(bridge_fault[h]));
  ot_hbm_su_static_vm_bank_leaf_s #(.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN)) u_leaf(
   .clk(pg_clk),.rst_n(leaf_rst_n),.qid(q_id),.b({g_id,1'(h)}),.su_rq(leaf_rq[h*17+:17]),.su_wq(leaf_wq[h*281+:281]),
   .su_rr(leaf_rr[h*257+:257]),.su_w_done(leaf_done[h]),.lg_rq(s_rq[h*17+:17]),.lg_wq(s_wq[h*281+:281]),
   .lg_rr(s_rr[h*257+:257]),.lg_w_done(s_done[h]),.fault(leaf_fault[h]));
 end
 // FAULT_REG is opt-in: publish the stream fault OR in a source-domain
 // register before the exact two-flop serial synchronizer. The arbitrary
 // fault transition is not part of the banked data calendar.
 wire pgf_raw=(|leaf_fault)||(|bridge_fault);
 generate if(FAULT_REG!=0) begin:g_pgf_reg
  reg pgf_q;
  always @(posedge pg_clk)
   if(!leaf_rst_n || !bridge_rst_n) pgf_q<=1'b0;
   else pgf_q <= (MUT==13) ? !pgf_raw : pgf_raw;
  assign pgf_s=pgf_q;
 end else begin:g_pgf_legacy
  assign pgf_s=pgf_raw;
 end endgenerate
 ot_hbm_vm_lg_pair_tap #(.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.LOCAL_SPLIT(1)) u_tap(
  .clk(pg_clk),.rst_n(tap_rst_n),.local_rq(s_rq),.far_rq(far_rq),.local_wq(s_wq),.far_wq(far_wq),
  .local_read(lg_read),.local_write(lg_write),.near_rq(lg_rq),.near_wq(lg_wq),.near_rr(lg_rr),.near_w_done(lg_w_done),
  .local_rr(s_rr),.far_rr(far_rr),.local_w_done(s_done),.far_w_done(far_w_done),.fault(lg_fault));
 // ---- COLLPORT inject: slot counter + decode straight into 3 banks at the slots the slice reads
 // (stream edge with sp = 0 / 1 / 3 -> bank 0 / 1 / 2; sp = 2 was never read)
 reg [1:0] sp;
 always @(posedge pg_clk or negedge bridge_rst_n) if(!bridge_rst_n) sp<=2'd0; else sp<=sp+2'd1;
 wire [161:0] ij = {inj_rd, inj_addr};
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
 always @(posedge pg_clk) begin
  if(sp==2'd0) ijb0 <= {bad,row,v};
  if(sp==2'd1) ijb1 <= {bad,row,v};
  if(sp==2'd3) ijb2 <= {bad,row,v};
 end
endmodule

// composition with ot_hbm_su_static_pg_stream's ports (bench lockstep; the die binds _q + _s as two abutted leaves)
module ot_hbm_su_static_pg_stream_split #(
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
 wire [33:0] rq_b0, rq_b1; wire [561:0] wq_b0, wq_b1; wire [513:0] rr_b0, rr_b1;
 wire [40:0] ijb0, ijb1, ijb2; wire pgf_s, rc_leaf, rc_tap;
 ot_hbm_su_static_pg_stream_q #(.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MUT(MUT)) u_q(
  .clk_ctl(clk_ctl),.rst_n(rst_n),.bridge_rst_n(bridge_rst_n),.vmr_cmd(vmr_cmd),.su_wq(su_wq),.su_rr(su_rr),
  .ij_v(ij_v),.ij_row(ij_row),.ij_bad(ij_bad),.pg_fault(pg_fault),
  .rq_b0(rq_b0),.rq_b1(rq_b1),.wq_b0(wq_b0),.wq_b1(wq_b1),.rr_b0(rr_b0),.rr_b1(rr_b1),
  .ijb0(ijb0),.ijb1(ijb1),.ijb2(ijb2),.pgf_s(pgf_s),.rc_leaf(rc_leaf),.rc_tap(rc_tap));
 ot_hbm_su_static_pg_stream_s #(.QID(QID),.G(G),.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MUT(MUT),
  .B39_NOOP(B39_NOOP),.STRAP(STRAP),.FAULT_REG(FAULT_REG)) u_s(
  .pg_clk(pg_clk),.bridge_rst_n(bridge_rst_n),.pos(pos),
  .rq_b0(rq_b0),.rq_b1(rq_b1),.wq_b0(wq_b0),.wq_b1(wq_b1),.rr_b0(rr_b0),.rr_b1(rr_b1),
  .ijb0(ijb0),.ijb1(ijb1),.ijb2(ijb2),.pgf_s(pgf_s),.rc_leaf(rc_leaf),.rc_tap(rc_tap),
  .inj_rd(inj_rd),.inj_addr(inj_addr),.lg_rq(lg_rq),.lg_wq(lg_wq),.lg_rr(lg_rr),.lg_w_done(lg_w_done),
  .lg_read(lg_read),.lg_write(lg_write),.far_rq(far_rq),.far_wq(far_wq),.far_rr(far_rr),.far_w_done(far_w_done),
  .lg_fault(lg_fault));
endmodule
`default_nettype wire
