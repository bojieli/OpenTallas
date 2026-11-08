`timescale 1ns/1ps
`default_nettype none
// DIE-HEAD-84 11-07: transaction bench for the opt-in hd_lep0N leg stages (ot_s81hd_lep0N_core KS / PIN / POUT / PLW).
// Two cores with the real lane content (PAIR=0: lnland + safe8 coll lane per lane) run the same stimulus:
//   ref = all stages 0 (the built netlist), dut = the stage counts `KTX_DUT / `KRX_DUT / `TXI_DUT / `PIN_DUT / `POUT_DUT / `PLW_DUT.
// Each coll lane talks to a peer e-lane whose core side echoes every received word back (credit-correct: 12 lane
// credits, a 16-deep echo FIFO, li_r per freed slot), so a ring beat goes ro -> TX FIFO -> K link -> lane -> peer ->
// echo -> lane -> K link -> RX pair release -> ri.  MU windows (pair A / pair B / landing) exercise lanes 2 / 3, the
// tag path (mu_c -> mu_rt) and the landing notification lw_o.
// PASS = the ri beat sequence, the mu_rt sequence and the lw_o sequence of dut equal ref (order and value, not time),
// both see the expected beat count, neither raises fault_o0.  Latency / drain differences are printed (declared cycles).
module tb_peer_echo(input wire ck, rs, input wire[511:0] dut_tx, output wire[513:0] dut_rx);
  wire [511:0] ptx; wire elo_r, eli_v; wire [552:0] eli_d; wire [2:0] pf;
  reg elo_v; reg [552:0] elo_d; reg eli_r;
  dsfd_coll_lane_e_safe8_ntf #(.CORE_CRED(12)) u_e(.ck(ck), .rs(rs), .chb(1'b1), .rx({1'b0, 1'b1, dut_tx, 1'b1}), .tx(ptx),
    .lo_v(elo_v), .lo_r(elo_r), .lo_d(elo_d), .li_v(eli_v), .li_r(eli_r), .li_d(eli_d), .flt(pf));
  assign dut_rx = {1'b1, 1'b0, ptx};                    // {live, fault, data}
  reg [552:0] q [0:15]; reg [4:0] n; reg [3:0] wp, rp; reg [4:0] cr;
  wire go = n != 0 && cr != 0;
  always @(posedge ck or negedge rs)
    if (!rs) begin n <= 0; wp <= 0; rp <= 0; cr <= 5'd12; elo_v <= 0; eli_r <= 0; end
    else begin
      if (eli_v) begin q[wp] <= eli_d; wp <= wp + 1'b1; end
      elo_v <= go; eli_r <= go;
      if (go) begin elo_d <= q[rp]; rp <= rp + 1'b1; end
      n <= n + (eli_v ? 5'd1 : 5'd0) - (go ? 5'd1 : 5'd0);
      cr <= cr + (elo_r ? 5'd1 : 5'd0) - (go ? 5'd1 : 5'd0);
      if (eli_v && n == 16) $fatal(1, "peer echo FIFO overflow (credit protocol broken)");
    end
endmodule

module tb_head_lepk_stages;
`ifndef KTX_DUT
`define KTX_DUT 16'h0000
`endif
`ifndef KRX_DUT
`define KRX_DUT 16'h1331
`endif
`ifndef TXI_DUT
`define TXI_DUT 16'h1331
`endif
`ifndef PIN_DUT
`define PIN_DUT 3
`endif
`ifndef POUT_DUT
`define POUT_DUT 3
`endif
`ifndef PLW_DUT
`define PLW_DUT 3
`endif
`ifndef COL0_DUT
`define COL0_DUT 0
`endif
  reg ck = 0; always #1 ck = ~ck;
  reg rs = 0;
  reg [1103:0] ro; reg [44:0] unit; reg lepf;
  wire [1103:0] ri_r, ri_d; wire [31:0] rt_r, rt_d; wire f_r, f_d; wire [10:0] lw_r, lw_d;
  wire [511:0] co_r [0:3]; wire [513:0] ci_r [0:3]; wire [511:0] co_d [0:3]; wire [513:0] ci_d [0:3];
  ot_s81hd_lep0N_noidx_core #(.CH_B(4'b1111), .PAIR(0)) u_ref(.ck(ck), .rst_n(rs),
    .coll_i0(ci_r[0]), .coll_i1(ci_r[1]), .coll_i2(ci_r[2]), .coll_i3(ci_r[3]),
    .coll_o0(co_r[0]), .coll_o1(co_r[1]), .coll_o2(co_r[2]), .coll_o3(co_r[3]),
    .lepk_i0(ro), .lepk_o0(ri_r), .lepf_i0(lepf), .unit_i0(unit), .ctrl_o0(rt_r), .fault_o0(f_r), .lw_o(lw_r));
  ot_s81hd_lep0N_noidx_core #(.CH_B(4'b1111), .PAIR(0), .KTX(`KTX_DUT), .KRX(`KRX_DUT), .TXI(`TXI_DUT), .PIN(`PIN_DUT), .POUT(`POUT_DUT), .PLW(`PLW_DUT), .COL0(`COL0_DUT)) u_dut(
    .ck(ck), .rst_n(rs),
    .coll_i0(ci_d[0]), .coll_i1(ci_d[1]), .coll_i2(ci_d[2]), .coll_i3(ci_d[3]),
    .coll_o0(co_d[0]), .coll_o1(co_d[1]), .coll_o2(co_d[2]), .coll_o3(co_d[3]),
    .lepk_i0(ro), .lepk_o0(ri_d), .lepf_i0(lepf), .unit_i0(unit), .ctrl_o0(rt_d), .fault_o0(f_d), .lw_o(lw_d));
  genvar g;
  generate for (g = 0; g < 4; g = g + 1) begin : g_peer
    tb_peer_echo u_pr(.ck(ck), .rs(rs), .dut_tx(co_r[g]), .dut_rx(ci_r[g]));
    tb_peer_echo u_pd(.ck(ck), .rs(rs), .dut_tx(co_d[g]), .dut_rx(ci_d[g]));
  end endgenerate
  // ------------------------------------------------------------------ captured transaction streams
  localparam integer MAXE = 8192;
  reg [1103:0] ev_ri_r [0:MAXE-1]; reg [1103:0] ev_ri_d [0:MAXE-1];
  reg [31:0] ev_rt_r [0:MAXE-1]; reg [31:0] ev_rt_d [0:MAXE-1];
  reg [10:0] ev_lw_r [0:MAXE-1]; reg [10:0] ev_lw_d [0:MAXE-1];
  integer n_ri_r = 0, n_ri_d = 0, n_rt_r = 0, n_rt_d = 0, n_lw_r = 0, n_lw_d = 0;
  integer first_r = -1, first_d = -1, last_r = -1, last_d = -1, cyc = 0;
  always @(posedge ck) begin
    cyc <= cyc + 1;
    if (rs) begin
      if (ri_r != 0) begin ev_ri_r[n_ri_r] <= ri_r; n_ri_r <= n_ri_r + 1; if (first_r < 0) first_r <= cyc; last_r <= cyc; end
      if (ri_d != 0) begin ev_ri_d[n_ri_d] <= ri_d; n_ri_d <= n_ri_d + 1; if (first_d < 0) first_d <= cyc; last_d <= cyc; end
      if (rt_r[31]) begin ev_rt_r[n_rt_r] <= rt_r; n_rt_r <= n_rt_r + 1; end
      if (rt_d[31]) begin ev_rt_d[n_rt_d] <= rt_d; n_rt_d <= n_rt_d + 1; end
      if (lw_r[0]) begin ev_lw_r[n_lw_r] <= lw_r; n_lw_r <= n_lw_r + 1; end
      if (lw_d[0]) begin ev_lw_d[n_lw_d] <= lw_d; n_lw_d <= n_lw_d + 1; end
    end
  end
  // ------------------------------------------------------------------ first-fault trace (which collector term, when)
  integer phase = 0; reg ftr_r = 0, ftr_d = 0;
`define LEPK_FT(T, P) \
  $display("LEPK_FAULT %s cyc=%0d phase=%0d ovf=%b perr=%b herr=%b slq=%b lfq=%b lfbq=%b mferr=%b(terr=%b mcol=%b mlf=%b) ie=%b merr=%b", T, cyc, phase, \
    P.ovf, P.perr, P.herr, P.slq, P.lfq, P.lfbq, P.mferr, P.terr, P.mcol_w, P.ml_f, P.ie, P.merr)
  always @(posedge ck) begin
    if (rs && !ftr_r && u_ref.u.u_lep.u.fault) begin ftr_r <= 1; `LEPK_FT("ref", u_ref.u.u_lep.u); end
    if (rs && !ftr_d && u_dut.u.u_lep.u.fault) begin ftr_d <= 1; `LEPK_FT("dut", u_dut.u.u_lep.u); end
  end
  // the collector registers its terms one cycle late: show the terms on the cycle before too
  always @(posedge ck) if (rs && !ftr_r && !u_ref.u.u_lep.u.fault && ((|u_ref.u.u_lep.u.ovf) || u_ref.u.u_lep.u.perr ||
      u_ref.u.u_lep.u.herr || u_ref.u.u_lep.u.slq || (|u_ref.u.u_lep.u.lfq) || (|u_ref.u.u_lep.u.lfbq) || u_ref.u.u_lep.u.mferr ||
      u_ref.u.u_lep.u.ie || u_ref.u.u_lep.u.merr)) `LEPK_FT("ref-pre", u_ref.u.u_lep.u);
  // DIE-HEAD-85: a hang (e.g. the replay wait never satisfied) is a FAIL with its phase, not a 50-min timeout
  always @(posedge ck) if (cyc > 60000) begin
    $display("LEPK_STAGES FAIL hang at cyc=%0d phase=%0d ri ref=%0d dut=%0d lw ref=%0d dut=%0d landed=%0d", cyc, phase,
      n_ri_r, n_ri_d, n_lw_r, n_lw_d, landed);
    $fflush; $finish;
  end
  // ------------------------------------------------------------------ stimulus
  localparam integer TG = 1045, NB = 80;
  integer sent = 0, landed = 0, i, w, k, seed = 7;
  task automatic beat(input [2:0] kind);
    begin
      ro = '0;
      for (k = 0; k < 35; k = k + 1) ro[32*k +: 32] = $urandom(seed + sent * 37 + k);
      ro[0] = 1'b1; ro[3:1] = kind; ro[TG +: 33] = '0;   // unstamped (a window stamps its own tag)
      sent = sent + 1;
    end
  endtask
  task automatic idle(input integer c); begin ro = '0; unit[44:11] = '0; repeat (c) @(negedge ck); end endtask
  task automatic window(input ab, input land, input [9:0] user);
    begin
      ro = '0; unit[44:11] = {21'(sent), user, land, ab, 1'b1}; @(negedge ck);
      unit[44:11] = '0; idle(3);
      for (w = 0; w < NB; w = w + 1) begin
        beat((w % 2) ? 3'd2 : 3'd1); if (land) landed = landed + 1; @(negedge ck);
        ro = '0; if ($urandom(seed + w) % 3 == 0) @(negedge ck);
      end
      idle(4);
    end
  endtask
  // DIE-HEAD-85: back-to-back windows at the tightest legal spacing.  The next window's command enters on the SAME input
  // cycle as the previous window's last beat (the core accepts that: `!(rov && wn == 1)`), so a mu_c that skips or adds
  // input stages relative to ro (MUT_MUSKEW) opens the next window while beats of the previous one are still counted
  // (tag error -> fault) or misses the first beat; with matched stages ref and dut stamp the same tags.
  task automatic windows_b2b(input integer nw, input [9:0] user0);
    integer x;
    begin
      ro = '0; unit[44:11] = {21'(sent), user0, 1'b0, 1'b0, 1'b1}; @(negedge ck); unit[44:11] = '0;
      for (x = 0; x < nw; x = x + 1) begin
        for (w = 0; w < NB; w = w + 1) begin
          beat((w % 2) ? 3'd2 : 3'd1);
          if (w == NB - 1 && x < nw - 1) unit[44:11] = {21'(sent), 10'(user0 + 2 * (x + 1)), 1'b0, 1'b0, 1'b1};   // same pair: alternating pairs b2b releases both pairs in one cycle (perr collision, ref too)
          @(negedge ck); ro = '0; unit[44:11] = '0;
          if (w < NB - 1 && $urandom(seed + 11 * w + x) % 3 == 0) @(negedge ck);
        end
      end
      idle(4);
    end
  endtask
  // DIE-HEAD-85 (COORD 22:4x): release-gap assert.  A pair release (relp[0] pair A, relp[1] pair B) that follows the
  // other pair's last release must leave >= 1 idle cycle; both in one cycle is the collision perr.  The minimum A<->B
  // handoff gap of ref and dut is printed so the schedule margin of the declared leg cycles is visible.
  integer gl_r = -1, gl_d = -1, gp_r = -1, gp_d = -1, gmin_r = 1 << 30, gmin_d = 1 << 30, gcol_d = 0;
  always @(posedge ck) if (rs) begin
    if (u_ref.u.u_lep.u.relp == 2'b11) gmin_r <= -1;
    else if (u_ref.u.u_lep.u.relp != 2'b00) begin
      if (gp_r >= 0 && u_ref.u.u_lep.u.relp[1] != gp_r[0] && cyc - gl_r - 1 < gmin_r) gmin_r <= cyc - gl_r - 1;
      gp_r <= u_ref.u.u_lep.u.relp[1]; gl_r <= cyc; end
    if (u_dut.u.u_lep.u.relp == 2'b11) begin gmin_d <= -1; gcol_d <= gcol_d + 1; end
    else if (u_dut.u.u_lep.u.relp != 2'b00) begin
      if (gp_d >= 0 && u_dut.u.u_lep.u.relp[1] != gp_d[0] && cyc - gl_d - 1 < gmin_d) gmin_d <= cyc - gl_d - 1;
      gp_d <= u_dut.u.u_lep.u.relp[1]; gl_d <= cyc; end
  end
  integer err = 0, ri_exp;
  initial begin
    ro = '0; unit = '0; lepf = 0;
    repeat (40) @(negedge ck); rs = 1; phase = 0;
    repeat (3000) @(negedge ck);                       // link bring-up
    phase = 1;
    // phase 1: plain ring beats (pair A), bursts at about 1/2 rate
    for (i = 0; i < 400; i = i + 1) begin
      beat(3'd0); @(negedge ck); ro = '0; if (i % 2 == 0) @(negedge ck);
    end
    idle(200);
    phase = 2;
    // phase 2: MU windows on pair A and pair B (copy select), one landing window
    window(1'b0, 1'b0, 10'd3);
    window(1'b1, 1'b0, 10'd5);
    window(1'b1, 1'b0, 10'd9);
    window(1'b0, 1'b0, 10'd17);
    phase = 5; windows_b2b(4, 10'd7); phase = 2;
    window(1'b1, 1'b1, 10'd21);
    // replay only after every landed beat is in the landing store (lw_o notification per beat on both cores): the land
    // faults by design on a replay of an incomplete slot
    phase = 3; idle(20); wait (n_lw_r >= landed && n_lw_d >= landed); idle(20);
    unit[10:0] = {10'd21, 1'b1}; @(negedge ck); unit[10:0] = '0; idle(300);   // replay the landed window
    phase = 4;
    // phase 3: back-to-back burst (TX FIFO absorbs; lanes drain at link rate)
    for (i = 0; i < 300; i = i + 1) begin beat(3'd0); @(negedge ck); end
    idle(1);
    repeat (6000) @(negedge ck);
    ri_exp = sent - landed;
    $display("LEPK_STAGES COL0=%0d", `COL0_DUT);
    $display("LEPK_STAGES release gap A<->B min ref=%0d dut=%0d (collisions dut %0d)", gmin_r, gmin_d, gcol_d);
    if (gcol_d != 0) begin $display("FAIL release gap: %0d dut cycles release both pairs", gcol_d); err = err + 1; end
    $display("LEPK_STAGES KTX=%h KRX=%h TXI=%h PIN=%0d POUT=%0d PLW=%0d sent=%0d landed=%0d ri ref=%0d dut=%0d rt ref=%0d dut=%0d lw ref=%0d dut=%0d",
      16'(`KTX_DUT), 16'(`KRX_DUT), 16'(`TXI_DUT), `PIN_DUT, `POUT_DUT, `PLW_DUT, sent, landed, n_ri_r, n_ri_d, n_rt_r, n_rt_d, n_lw_r, n_lw_d);
    $display("LEPK_STAGES first ri ref=%0d dut=%0d (+%0d)  last ri ref=%0d dut=%0d (+%0d)", first_r, first_d, first_d - first_r,
      last_r, last_d, last_d - last_r);
    $display("LEPK_STAGES info: ref ri beats %0d, ring beats sent %0d (landed %0d, replayed on ri)", n_ri_r, sent, landed);
    if (n_ri_r < sent - landed) begin $display("FAIL ref lost beats: ri %0d < %0d", n_ri_r, sent - landed); err = err + 1; end
    if (n_ri_d != n_ri_r) begin $display("FAIL ri count dut %0d ref %0d", n_ri_d, n_ri_r); err = err + 1; end
    if (n_rt_d != n_rt_r) begin $display("FAIL mu_rt count dut %0d ref %0d", n_rt_d, n_rt_r); err = err + 1; end
    if (n_lw_d != n_lw_r) begin $display("FAIL lw count dut %0d ref %0d", n_lw_d, n_lw_r); err = err + 1; end
    if (n_rt_r == 0 || n_lw_r == 0) begin $display("FAIL bench did not exercise mu_rt (%0d) / lw (%0d)", n_rt_r, n_lw_r); err = err + 1; end
    for (i = 0; i < n_ri_r && i < n_ri_d; i = i + 1)
      if (ev_ri_r[i] !== ev_ri_d[i]) begin if (err < 20) $display("FAIL ri beat %0d differs", i); err = err + 1; end
    for (i = 0; i < n_rt_r && i < n_rt_d; i = i + 1)
      if (ev_rt_r[i] !== ev_rt_d[i]) begin if (err < 20) $display("FAIL mu_rt %0d differs %h %h", i, ev_rt_r[i], ev_rt_d[i]); err = err + 1; end
    for (i = 0; i < n_lw_r && i < n_lw_d; i = i + 1)
      if (ev_lw_r[i] !== ev_lw_d[i]) begin if (err < 20) $display("FAIL lw %0d differs", i); err = err + 1; end
    if (f_r || f_d) begin $display("FAIL fault ref=%0d dut=%0d", f_r, f_d); err = err + 1; end
    if (err == 0) $display("LEPK_STAGES PASS");
    else $display("LEPK_STAGES FAIL errors=%0d", err);
    $finish;
  end
`ifdef LEPK_DBG
  // DIE-HEAD-85 debug: which perr condition fires first in the dut (relp collision, full RX FIFO, pair parity)
  reg dbg_done = 0;
  always @(posedge ck) if (rs && !dbg_done && (u_dut.u.u_lep.u.relp == 2'b11 || |u_dut.u.u_lep.u.rxf ||
      (u_dut.u.u_lep.u.rel && u_dut.u.u_lep.u.h0[552] != u_dut.u.u_lep.u.h1[552]))) begin
    dbg_done <= 1;
    $display("LEPK_DBG cyc=%0d phase=%0d relp=%b rxf=%b rne=%b h0p=%b h1p=%b", cyc, phase, u_dut.u.u_lep.u.relp,
      u_dut.u.u_lep.u.rxf, u_dut.u.u_lep.u.rne, u_dut.u.u_lep.u.h0[552], u_dut.u.u_lep.u.h1[552]);
  end
  integer dbg_n = 0;
  always @(posedge ck) if (rs && dbg_n < 400 && cyc > 4700 && cyc < 4870) begin dbg_n <= dbg_n + 1;
    $display("LEPK_TR cyc=%0d rne_dut=%b rne_ref=%b", cyc, u_dut.u.u_lep.u.rne, u_ref.u.u_lep.u.rne); end
`endif
endmodule
`default_nettype wire
