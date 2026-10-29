`timescale 1ns/1ps
// DIE-QC-16 A0 tile-root ICG bench (tools/qwen_romleaf/a0core/icg/): qfd_tile_<t>_a0c ICG=0 (ungated, == main) vs
// ICG=1 (gated body clock, enable from existing signals), same stimulus, every output bit compared at every negedge.
// Stimulus (gen_tb.py A0 equiv pattern + gating phases): x line / n data toggle EVERY cycle (also while idle); 5 commands
// (all banks) spaced 1200; idle stretches with and without node traffic; n valid every 11 cycles in windows; a reset
// pulse while idle and one while busy; back-to-back go while busy.  +ICG_MUT=n selects an RTL mutant in the ICG=1 side.
module tb_a0_icg;
integer NCYC = 12000;
initial if ($value$plusargs("NCYC=%d", NCYC)) begin end
reg ck = 0; always #0.5 ck = ~ck;
reg rs = 0;
reg [507:0] tap = 0;
reg [513:0] na = 0, nb = 0;
wire [513:0] ot, gt, on_, gn;
wire ohi, olo, ghi, glo;
`ifdef TB_NL
qfd_tile_nl_a0c #(.REGROOT_MODE(3), .ROM_TILE(48), .ICG(0)) u_off (.ck(ck), .rst_n(rs), .tile_id(16'd48), .tie_hi(ohi), .tie_lo(olo), .tap(tap), .t_out(ot));
qfd_tile_nl_a0c #(.REGROOT_MODE(3), .ROM_TILE(48), .ICG(1)) u_on  (.ck(ck), .rst_n(rs), .tile_id(16'd48), .tie_hi(ghi), .tie_lo(glo), .tap(tap), .t_out(gt));
assign on_ = 0; assign gn = 0;
localparam TILE = "nl";
`else
qfd_tile_nk_a0c #(.REGROOT_MODE(3), .ROM_TILE(48), .ICG(0)) u_off (.ck(ck), .rst_n(rs), .tile_id(16'd48), .tie_hi(ohi), .tie_lo(olo), .tap(tap), .t_out(ot), .n_a(na), .n_b(nb), .n_y(on_));
qfd_tile_nk_a0c #(.REGROOT_MODE(3), .ROM_TILE(48), .ICG(1)) u_on  (.ck(ck), .rst_n(rs), .tile_id(16'd48), .tie_hi(ghi), .tie_lo(glo), .tap(tap), .t_out(gt), .n_a(na), .n_b(nb), .n_y(gn));
localparam TILE = "nk";
`endif
function automatic [378:0] command(input integer bank);
 command={18'd4096,18'd2,18'd32,1'b0,24'(bank*4096),24'd64,24'd8,24'd1,
          24'd0,24'd1,24'd1,24'd1,3'd0,4'd7,24'd1,1'b0,24'd0,24'd1,24'd1,
          1'b0,1'b1,1'b0,1'b0,24'd0};
endfunction
function automatic integer popc(input [513:0] v);
  integer i; popc = 0; for (i = 0; i < 514; i = i + 1) popc = popc + v[i];
endfunction
function automatic integer isgo(input integer c);
  isgo = (c == 200 || c == 1400 || c == 2600 || c == 3800 || c == 5000 || c == 7300 || c == 8600 || c == 9500
          || c == 9530 || c == 10400 || c == 10401);
endfunction
integer cyc, errors = 0, checks = 0, tval = 0, tnz = 0, nval = 0, gated = 0, cmds = 0, first_err = -1, et = 0, en_ = 0;
integer reactivated_valid = 0;
integer qerr = 0, qfirst = -1, qt = 0, qn = 0, busy_c = 0, idle_gated = 0, wake = 0, last_en = 1;
initial begin
  repeat (8) @(negedge ck); rs = 1;
  for (cyc = 0; cyc < NCYC; cyc = cyc + 1) begin
    tap[0] = 0;
    if (isgo(cyc)) begin tap[379:1] = command(cmds % 5); tap[0] = 1; cmds = cmds + 1; end
    for (integer g = 0; g < 4; g = g + 1) tap[380 + g*32 +: 32] = 32'h3f800000 + ((cyc % 8 + g) << 18);
    for (integer lane = 0; lane < 16; lane = lane + 1) begin
      na[lane*32 +: 32] = 32'h3f000000 + ((cyc % 16 + lane) << 17);
      nb[lane*32 +: 32] = 32'h3f800000 + ((cyc % 8 + lane) << 17);
    end
    // node valid every 11 cycles only in windows (one inside a run, one while the engine is idle), fault bit once
    na[513:512] = {(cyc == 6205), ((cyc >= 600 && cyc < 900) || (cyc >= 6000 && cyc < 6400)) && (cyc % 11 == 0)};
    nb[513:512] = na[513:512];
    if (cyc == 6300) nb[512] = 1;                         // one misaligned leg (mis_q sticky fault)
    if (cyc == 7000) rs = 0;                              // reset pulse while idle
    if (cyc == 7005) rs = 1;
    if (cyc == 8700) rs = 0;                              // reset while busy (run of the 8600 command)
    if (cyc == 8703) rs = 1;
    @(negedge ck);
    checks = checks + 1;
    if (ot !== gt || on_ !== gn || ohi !== ghi || olo !== glo) begin
      errors = errors + 1; if (first_err < 0) first_err = cyc;
      if (ot !== gt) et = et + 1;
      if (on_ !== gn) en_ = en_ + 1;
      if (errors <= 2) $display("A0ICG_MISMATCH cyc%0d t_out %0d bits ([513:512] off%b on%b) n_y %0d bits ([513:512] off%b on%b)",
        cyc, popc(ot ^ gt), ot[513:512], gt[513:512], popc(on_ ^ gn), on_[513:512], gn[513:512]);
    end
    // valid-qualified compare (the tile's contract: data words are values only under their valid bit; valid and fault
    // bits are compared every cycle).  Strict = every bit every cycle (reported, not the gate: invalid words carry
    // free-running x / n data in the ungated form).
    if (ot[513:512] !== gt[513:512] || (ot[512] && ot[511:0] !== gt[511:0])) qt = qt + 1;
    if (on_[513:512] !== gn[513:512] || (on_[512] && on_[511:0] !== gn[511:0])) qn = qn + 1;
    if (ot[513:512] !== gt[513:512] || (ot[512] && ot[511:0] !== gt[511:0]) || on_[513:512] !== gn[513:512]
        || (on_[512] && on_[511:0] !== gn[511:0]) || ohi !== ghi || olo !== glo) begin
      qerr = qerr + 1; if (qfirst < 0) qfirst = cyc;
      if (qerr <= 5) $display("A0ICG_QMISMATCH cyc%0d t_out [513:512] off%b on%b data %0d bits | n_y [513:512] off%b on%b data %0d bits",
        cyc, ot[513:512], gt[513:512], popc({2'b0, ot[511:0] ^ gt[511:0]}), on_[513:512], gn[513:512], popc({2'b0, on_[511:0] ^ gn[511:0]}));
    end
    if (ot[512] && wake > 0) reactivated_valid = reactivated_valid + 1;
    if (ot[512]) begin tval = tval + 1; if (|ot[511:0]) tnz = tnz + 1; end
    if (on_[512]) nval = nval + 1;
    if (!u_on.g_icg.en) gated = gated + 1;
    if (!u_off.u_g.u_tile.u_tile.u_logic.u_me.idle) busy_c = busy_c + 1;
    if (u_on.g_icg.en && !last_en) wake = wake + 1;
    last_en = u_on.g_icg.en;
  end
  $display("A0ICG_NEXT_ACTIVATION valid_after_wakeup=%0d",reactivated_valid);
  $display("A0ICG_COUNTS tile=%s MUT=%0d checks=%0d cmds=%0d t_valid=%0d t_nonzero=%0d n_valid=%0d gated_cycles=%0d (%0d%%) engine_busy=%0d wakeups=%0d",
    TILE, u_on.g_icg.mut, checks, cmds, tval, tnz, nval, gated, gated * 100 / checks, busy_c, wake);
  $display("A0ICG_STRICT tile=%s MUT=%0d strict_mismatch_cycles=%0d (t_out %0d n_y %0d) first=%0d", TILE, u_on.g_icg.mut, errors, et, en_, first_err);
  if (tval == 0 || tnz == 0 || gated == 0 || wake < 3) $display("A0ICG_ACTIVITY_MISSING");
  if (qerr) $display("A0ICG_FAIL tile=%s MUT=%0d qualified_errors=%0d (t_out %0d n_y %0d) first_cycle=%0d checks=%0d", TILE, u_on.g_icg.mut, qerr, qt, qn, qfirst, checks);
  else if (tval > 0 && tnz > 0 && gated > 0 && wake >= 3) $display("A0ICG_PASS tile=%s MUT=%0d checks=%0d gated=%0d qualified_errors=0 strict=%0d", TILE, u_on.g_icg.mut, checks, gated, errors);
  $finish;
end
endmodule
