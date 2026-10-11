`timescale 1ns/1ps
// tb_mtp_p2_lanes (mtp-colllane-1011): the P2 variant of the collective's dedicated MTP lanes, end to end.
// Draft die A = dsfd_sp_collective with OT_S81PH_COLL_P2L (collective lanes 0..7 idle) whose P2 die bus crosses the
// draft-A relay stations (collective <-> p2 FC / RC, vm <-> p2 FV / RV) into dsfd_p2_rtt (dsfd_p2_lnk + the unchanged
// rb4 core ot_mtp_p2_prefix_path).  The far ends are the real lane tile + dsfd_coll_p2_lane: the DSpark PRIMARY (board
// lane W4: sends starts + abort events, receives result rows + done / fault / corrected) and DIE B (UCIe lane E4: sends
// the lane-1 expert words).  Channels are raw beat channels with deterministic bit errors (link-layer replay).
// Same transaction as tb_mtp_p2_fixlat (start, 80 lane-1 E3 words, 160 lane-0 words, 80 numeric rows vs gold.hex),
// NTX back-to-back transactions; the primary's result-row consumer stalls (incl. a 200-cycle window).
// ABORT events: the primary toggles its abort wire at AB0 / AB0 + 40 (one pulse) while the starts wait in die A (SGHOLD); the
// pulse must reach die A's t_p2 abort pin within ABMAX cycles (the bench keeps the core's abort tied low: abort
// semantics are not under test, its transport is).
//   default PASS | OT_P2L_MUT_SEG FAIL (segmentation) | OT_P2L_MUT_CRED FAIL (row class buffer overflow) |
//   OT_P2L_MUT_DIRECT FAIL (abort blocked behind the pending start = HOL) | OT_FIXLAT_MUT_LAT1 FAIL (link ends)
module tb_mtp_p2_lanes #(parameter integer FV=12, RV=14, FC=8, RC=9, SEED=1, NTX=2, START_DELAY=300, NOSTALL=0,
                         CHB=60, CHU=12, EPER=97, AB0=1700, ABMAX=400, SGHOLD=2500, RS0=20, RS1=3020);
 reg refclk=0; always #5 refclk=~refclk;
 reg por=0; initial #50 por=1;
 wire clk, rstd;
 reg [31:0] inputs[0:3839], gold[0:1279];
 localparam [73:0] IDN0=74'h12345678; localparam [26:0] IDS={9'd127,9'd65,9'd3};
 integer cycles=0, received=0, s0=0, s1=0, i;
 function automatic [511:0] flit(input integer e, w);
  integer s; begin for(s=0;s<16;s=s+1) flit[32*s+:32]=inputs[e*1280+w*16+s]; end
 endfunction
 function automatic [603:0] l1w(input integer n); integer w; reg [73:0] id; begin w=n%80; id=IDN0+n/80;
  l1w={id,9'd3,1'b0,w==79,7'(w),flit(0,w)}; end endfunction
 function automatic [603:0] l0w(input integer n); integer k; reg [73:0] id; begin k=n%160; id=IDN0+n/160;
  l0w = k<80 ? {id,9'd127,1'b0,k==79,7'(k),flit(2,k)} : {id,9'd65,1'b0,k==159,7'(k-80),flit(1,k-80)}; end
 endfunction
 function automatic [31:0] mix(input [31:0] a, b); mix=(a^(b*32'h9e3779b9))*32'h85ebca6b ^ (a>>13); endfunction
 reg [31:0] rnd;
 always @(negedge clk) rnd = mix(cycles+SEED, 32'h51ed2701);
 // ---------------------------------------------------------------- die A collective slab (P2L)
 wire [708:0] t_p2; wire [599:0] f_p2; wire [1:0] p2flt;
 wire [514:0] a_rw4, a_re4; wire [511:0] a_tw4, a_te4;
 dsfd_sp_collective u_a (.refclk(refclk), .por(por), .f_vm(592'd0), .ts(3'd0),
  .rW0(515'd0), .rW1(515'd0), .rW2(515'd0), .rW3(515'd0), .rE0(515'd0), .rE1(515'd0), .rE2(515'd0), .rE3(515'd0),
  .pll_stream(clk), .pll_serial(), .pll_hbm(), .rst_stream(rstd), .rst_serial(), .rst_hbm(), .t_vm(),
  .tdW0(), .tdW1(), .tdW2(), .tdW3(), .tdE0(), .tdE1(), .tdE2(), .tdE3(),
  .tfW0(), .tfW1(), .tfW2(), .tfW3(), .tfE0(), .tfE1(), .tfE2(), .tfE3(),
  .t_p2(t_p2), .f_p2(f_p2), .rW4(a_rw4), .rE4(a_re4), .tdW4(a_tw4), .tdE4(a_te4), .tfW4(), .tfE4(), .t_p2flt(p2flt));
 // ---------------------------------------------------------------- far ends: primary (board) and die B (UCIe)
 wire [514:0] p_rx, b_rx; wire [511:0] p_tx, b_tx;
 wire pv0, bv0, av0, ae0; wire [511:0] pd0, bd0, ad0, ae0d;
 ot_dsrom_link_chan #(.W(512), .MAXD(CHB), .ERR_PERIOD(EPER), .ERR_OFFSET(3), .ERR_STRIDE(37)) c_ap (.clk(clk), .rst_n(rstd),
  .delay(16'd0), .in_valid(rstd), .in_data(a_tw4), .out_valid(pv0), .out_data(pd0), .err_injected());
 ot_dsrom_link_chan #(.W(512), .MAXD(CHB), .ERR_PERIOD(EPER), .ERR_OFFSET(5), .ERR_STRIDE(37)) c_pa (.clk(clk), .rst_n(rstd),
  .delay(16'd0), .in_valid(rstd), .in_data(p_tx), .out_valid(av0), .out_data(ad0), .err_injected());
 ot_dsrom_link_chan #(.W(512), .MAXD(CHU), .ERR_PERIOD(EPER), .ERR_OFFSET(7), .ERR_STRIDE(37)) c_ab (.clk(clk), .rst_n(rstd),
  .delay(16'd0), .in_valid(rstd), .in_data(a_te4), .out_valid(bv0), .out_data(bd0), .err_injected());
 ot_dsrom_link_chan #(.W(512), .MAXD(CHU), .ERR_PERIOD(EPER), .ERR_OFFSET(11), .ERR_STRIDE(37)) c_ba (.clk(clk), .rst_n(rstd),
  .delay(16'd0), .in_valid(rstd), .in_data(b_tx), .out_valid(ae0), .out_data(ae0d), .err_injected());
 assign p_rx = {1'b0, 1'b1, pd0, pv0}; assign a_rw4 = {1'b0, 1'b1, ad0, av0};
 assign b_rx = {1'b0, 1'b1, bd0, bv0}; assign a_re4 = {1'b0, 1'b1, ae0d, ae0};
 wire pl_lov, pl_lor, pl_liv, pl_lir, bl_lov, bl_lor, bl_liv, bl_lir; wire [552:0] pl_lod, pl_lid, bl_lod, bl_lid;
 wire [2:0] pl_flt, bl_flt; wire p_aflt, b_aflt;
 dsfd_coll_lane_w #(.LCR(1)) u_plt (.ck(clk), .rs(rstd), .chb(1'b1), .rx(p_rx), .tx(p_tx), .tf(),
  .lo_v(pl_lov), .lo_r(pl_lor), .lo_d(pl_lod), .li_v(pl_liv), .li_r(pl_lir), .li_d(pl_lid), .flt(pl_flt));
 dsfd_coll_lane_w #(.LCR(1)) u_blt (.ck(clk), .rs(rstd), .chb(1'b0), .rx(b_rx), .tx(b_tx), .tf(),
  .lo_v(bl_lov), .lo_r(bl_lor), .lo_d(bl_lod), .li_v(bl_liv), .li_r(bl_lir), .li_d(bl_lid), .flt(bl_flt));
 reg cs_v=0, c1_v=0, c0_v=0, co_r=0, ab=0; integer starts=0, row1=-1;
 wire cs_r, c1_r, c0_r, co_v; wire [593:0] co_d; wire [2:0] p_ev;
 dsfd_coll_p2_lane #(.TXK(6), .TXW(101), .RXK(7), .RXW(594), .EVT(1), .EVR(3), .CRED(8), .TCRED(8)) u_pr (
  .ck(clk), .rs(rstd), .x_v(cs_v), .x_r(cs_r), .x_d({IDN0+starts,IDS}), .r_v(co_v), .r_r(co_r), .r_d(co_d),
  .x_ev(ab), .r_ev(p_ev), .lo_v(pl_lov), .lo_r(pl_lor), .lo_d(pl_lod), .li_v(pl_liv), .li_r(pl_lir), .li_d(pl_lid),
  .f_lflt(pl_flt), .t_flt(p_aflt));
 dsfd_coll_p2_lane #(.TXK(5), .TXW(604), .RXK(0), .RXW(0), .EVT(0), .EVR(0), .CRED(0), .TCRED(0)) u_db (
  .ck(clk), .rs(rstd), .x_v(c1_v), .x_r(c1_r), .x_d(l1w(s1)), .r_v(), .r_r(1'b0), .r_d(),
  .x_ev(1'b0), .r_ev(), .lo_v(bl_lov), .lo_r(bl_lor), .lo_d(bl_lod), .li_v(bl_liv), .li_r(bl_lir), .li_d(bl_lid),
  .f_lflt(bl_flt), .t_flt(b_aflt));
 // ---------------------------------------------------------------- die A: P2 die bus over the stations, VM lane 0
 wire l0v_s, l0g_s, l0v_p, l0g_p; wire [603:0] l0d_s, l0d_p;
 wire l1v_p, l1g_p, sv_p, sg_p, ov_p, og_p; wire [603:0] l1d_p; wire [100:0] sd_p; wire [593:0] od_p;
 wire done, fault, corr, ab_p;
 dsfd_vm_p2_ep vme(.ck(clk), .rst(rstd), .c_l0v(c0_v), .c_l0r(c0_r), .c_l0d(l0w(s0)), .t_l0v(l0v_s), .t_l0d(l0d_s), .f_l0g(l0g_s));
 p2fl_relay #(.W(605),.N(FV)) r0 (clk, rstd, {l0v_s,l0d_s}, {l0v_p,l0d_p});
 p2fl_relay #(.W(1),.N(RV))   r0g(clk, rstd, l0g_p, l0g_s);
 p2fl_relay #(.W(709),.N(FC)) rcp(clk, rstd, t_p2, {og_p, ab_p, sd_p, sv_p, l1d_p, l1v_p});
 // SGHOLD: the P2 slab grants no start before this cycle (a busy core): starts 1..3 wait in die A's start class buffer
 // while the primary's abort event crosses the same lane (credited: not blocked; OT_P2L_MUT_DIRECT: blocked = HOL)
 wire sg_g = sg_p && (cycles >= SGHOLD);
 p2fl_relay #(.W(600),.N(RC)) rpc(clk, rstd, {corr, fault, done, sg_g, l1g_p, od_p, ov_p}, f_p2);
 dsfd_p2_rtt #(.FWD_V(FV),.RET_V(RV),.FWD_C(FC),.RET_C(RC)) dut(.ck(clk), .rst(rstd),
  .f_l0v(l0v_p), .f_l0d(l0d_p), .t_l0g(l0g_p), .f_l1v(l1v_p), .f_l1d(l1d_p), .t_l1g(l1g_p), .f_sv(sv_p), .f_sd(sd_p), .t_sg(sg_p),
  .t_ov(ov_p), .t_od(od_p), .f_og(og_p), .f_abort(1'b0), .t_done(done), .t_fault(fault), .t_corrected(corr));
 // ---------------------------------------------------------------- drivers / checks
 always @(negedge clk) if(rstd) begin
  cs_v = starts<NTX && cycles>=START_DELAY;
  c1_v = s1<80*NTX  && (NOSTALL || rnd[2:0]!=0);
  c0_v = s0<160*NTX && (NOSTALL || rnd[5:3]!=0);
  // the result-row consumer: random gaps, 50-cycle windows, and one long window RS0..RS1 cycles after the first row (rows
  // are still flowing: the row class buffer runs full, one credit over its capacity overflows it)
  co_r = NOSTALL || (!(row1>=0 && cycles>=row1+RS0 && cycles<row1+RS1) && rnd[9:7]!=0 && !(cycles%300>=250));
  ab = cycles>=AB0 && cycles<AB0+40;
 end
 // transport monitors at die A (lane 1 on the die bus, starts at coll_p2_ep's core side): every lane-1 word / start equals what the far end sent, in order
 integer a_l1=0, a_st=0;
 always @(posedge clk) if(rstd) begin
  if(t_p2[0]) begin                       // lane 1 leaves die A's u_ba on the die bus (grant protocol: one word a valid)
   if(t_p2[604:1] !== l1w(a_l1)) $fatal(1,"P2L transport lane-1 word %0d mismatch: got id %h exp %h got lo %h exp lo %h", a_l1,
       t_p2[604:531], l1w(a_l1)>>530, t_p2[64:1], l1w(a_l1)[63:0]);
   a_l1 <= a_l1 + 1;
  end
  if(u_a.c_sv && u_a.c_sr) begin
   if(u_a.c_sd !== {IDN0+a_st,IDS}) $fatal(1,"P2L transport start %0d mismatch %h", a_st, u_a.c_sd);
   a_st <= a_st + 1;
  end
 end
 integer done_seen=0, ab_rise=-1, ab_arrive=-1, flt_seen=0; reg pdone_q=0, abp_q=0;
 always @(posedge clk) if(rstd) begin
  cycles<=cycles+1;
  if(cs_v&&cs_r) starts<=starts+1;
  if(c1_v&&c1_r) s1<=s1+1;
  if(c0_v&&c0_r) s0<=s0+1;
  if(fault) $display("P2L core fault parts tr %0d ar %0d pub %0d broken %0d lost %0d abort %0d cur_id %h c_start %0d/%0d %h c_in_v %b c_in_r %b in_id1 %h in_id0 %h",
     dut.u_core.enabled.tr_fault, dut.u_core.enabled.ar_fault, dut.u_core.enabled.pub_fault, dut.u_core.enabled.broken,
     dut.u_core.enabled.lost_q, dut.u_core.enabled.abort_q, dut.u_lnk.cur_id, dut.u_lnk.c_start_v, dut.u_lnk.c_start_r,
     dut.u_lnk.c_start_d[100:27], dut.u_lnk.c_in_v, dut.u_lnk.c_in_r, dut.u_lnk.c_in_d[1207:1134], dut.u_lnk.c_in_d[603:530]);
  if(fault || p_ev[1]) $fatal(1,"P2L unexpected core fault cycle %0d (core %0d primary-seen %0d) starts %0d s0 %0d s1 %0d sv_p %0d l1v_p %0d l0v_p %0d id_s %h id_1 %h",
                              cycles, fault, p_ev[1], starts, s0, s1, sv_p, l1v_p, l0v_p, sd_p[100:27], l1d_p[603:530]);
  if(p2flt!=0 || p_aflt || b_aflt) begin flt_seen=flt_seen+1; if(flt_seen==1) $display("P2L lane FAULT a=%b p=%b b=%b cycle %0d",p2flt,p_aflt,b_aflt,cycles); end
  pdone_q<=p_ev[0]; if(p_ev[0]&&!pdone_q) done_seen<=done_seen+1;   // done (level-carried pulse) at the primary
  abp_q<=ab_p; if(ab_p&&!abp_q&&ab_arrive<0) ab_arrive=cycles;
  if(cycles==AB0) ab_rise=cycles;
  if(co_v && row1<0) row1<=cycles;
  if(co_v&&co_r) begin
   if(received>=80*NTX) $fatal(1,"P2L extra/duplicate output row %0d",received);
   if(co_d[81:8]!==IDN0+received/80 || co_d[7:1]!==7'(received%80) || co_d[0]!==(received%80==79))
    $fatal(1,"P2L metadata row %0d (word %0d last %0d)",received,co_d[7:1],co_d[0]);
   for(i=0;i<16;i=i+1) if(co_d[82+32*i+:32]!==gold[(received%80)*16+i]) $fatal(1,"P2L numeric row %0d lane %0d",received,i);
   received<=received+1;
  end
  if(cycles>40000*NTX) $fatal(1,"P2L timeout received=%0d s0=%0d s1=%0d done=%0d",received,s0,s1,done_seen);
 end
 initial begin
  $readmemh("inputs.hex",inputs); $readmemh("gold.hex",gold);
  wait(rstd===1'b1);
  wait(received==80*NTX && done_seen==NTX);
  repeat(400) @(posedge clk);
  if(co_v || done_seen!=NTX) $fatal(1,"P2L extra output / done after completion");
  if(flt_seen) $fatal(1,"P2L lane / adapter fault");
  if(ab_arrive<0 || ab_arrive-ab_rise>ABMAX) $fatal(1,"P2L abort event late / lost (HOL): sent %0d arrived %0d (max %0d)",ab_rise,ab_arrive,ABMAX);
  $display("P2L PASS FV=%0d RV=%0d FC=%0d RC=%0d transactions=%0d rows=%0d lane0=%0d lane1=%0d cycles=%0d abort_latency=%0d starts=%0d",
           FV,RV,FC,RC,NTX,received,s0,s1,cycles,ab_arrive-ab_rise,starts);
  $finish;
 end
endmodule
