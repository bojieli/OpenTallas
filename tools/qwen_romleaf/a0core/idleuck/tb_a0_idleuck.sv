`timescale 1ns/1ps
// DIE-QC-66/CORES 11-03 A0 NL IDLE_UCK bench (stimulus = tools/qwen_romleaf/a0core/icg/tb_a0_icg.sv):
//   u_k1 = NL kit form as built (G4_ROOTS 1, REGROOT_MODE 3, ICG 1, ICG_RRST 1, IDLE_UCK 1: u_me.idle on the ungated ck)
//   u_k0 = the same with IDLE_UCK 0 (the pre-route LEC-signed kit RTL)          -> STRICT: every output bit, every negedge
//   u_off = ICG 0 (ungated body, the bound form)                                -> valid-qualified (the ICG contract)
// +MUT=1: u_k1's u_me.idle forced 1 for cycles [MS, MS+ML) of a busy run (premature idle -> early gate) -> must FAIL.
// +MUT=2: u_k1's u_me.idle forced 1 for one cycle at the go cycle 1400                                    -> must FAIL.
module tb_a0_idleuck;
integer NCYC = 12000, MUT = 0, MS = 1450, ML = 300;
initial begin
  if ($value$plusargs("NCYC=%d", NCYC)) begin end
  if ($value$plusargs("MUT=%d", MUT)) begin end
  if ($value$plusargs("MS=%d", MS)) begin end
  if ($value$plusargs("ML=%d", ML)) begin end
end
reg ck = 0; always #0.5 ck = ~ck;
reg rs = 0;
reg [507:0] tap = 0;
wire [513:0] ot, t0, t1;
wire ohi, olo, h0, l0, h1, l1;
qfd_tile_nl_a0c #(.G4_ROOTS(1), .REGROOT_MODE(3), .ICG(0), .ICG_RRST(1), .IDLE_UCK(0), .ROM_TILE(48)) u_off (.ck(ck), .rst_n(rs), .tile_id(16'd48), .tie_hi(ohi), .tie_lo(olo), .tap(tap), .t_out(ot));
qfd_tile_nl_a0c #(.G4_ROOTS(1), .REGROOT_MODE(3), .ICG(1), .ICG_RRST(1), .IDLE_UCK(0), .ROM_TILE(48)) u_k0  (.ck(ck), .rst_n(rs), .tile_id(16'd48), .tie_hi(h0), .tie_lo(l0), .tap(tap), .t_out(t0));
qfd_tile_nl_a0c #(.G4_ROOTS(1), .REGROOT_MODE(3), .ICG(1), .ICG_RRST(1), .IDLE_UCK(1), .ROM_TILE(48)) u_k1  (.ck(ck), .rst_n(rs), .tile_id(16'd48), .tie_hi(h1), .tie_lo(l1), .tap(tap), .t_out(t1));
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
integer cyc, serr = 0, sfirst = -1, qerr = 0, qfirst = -1, checks = 0, tval = 0, tnz = 0, gated = 0, wake = 0, last_en = 1;
integer busy = 0, idiff = 0, forced = 0;
initial begin
  repeat (8) @(negedge ck); rs = 1;
  for (cyc = 0; cyc < NCYC; cyc = cyc + 1) begin
    tap[0] = 0;
    if (isgo(cyc)) begin tap[379:1] = command(cyc % 5); tap[0] = 1; end
    for (integer g = 0; g < 4; g = g + 1) tap[380 + g*32 +: 32] = 32'h3f800000 + ((cyc % 8 + g) << 18);
    if (cyc == 7000) rs = 0;                              // reset pulse while idle
    if (cyc == 7005) rs = 1;
    if (cyc == 8700) rs = 0;                              // reset while busy
    if (cyc == 8703) rs = 1;
    if ((MUT == 1 && cyc == MS) || (MUT == 2 && cyc == 1400)) begin force u_k1.u_g.u_tile.u_tile.u_logic.u_me.idle = 1'b1; forced = forced + 1; end
    if ((MUT == 1 && cyc == MS + ML) || (MUT == 2 && cyc == 1401)) release u_k1.u_g.u_tile.u_tile.u_logic.u_me.idle;
    @(negedge ck);
    checks = checks + 1;
    if (t1 !== t0 || h1 !== h0 || l1 !== l0) begin
      serr = serr + 1; if (sfirst < 0) sfirst = cyc;
      if (serr <= 3) $display("IDLEUCK_SMISMATCH cyc%0d t_out %0d bits ([513:512] k0 %b k1 %b)", cyc, popc(t0 ^ t1), t0[513:512], t1[513:512]);
    end
    if (ot[513:512] !== t1[513:512] || (ot[512] && ot[511:0] !== t1[511:0]) || ohi !== h1 || olo !== l1) begin
      qerr = qerr + 1; if (qfirst < 0) qfirst = cyc;
      if (qerr <= 3) $display("IDLEUCK_QMISMATCH cyc%0d off %b k1 %b data %0d bits", cyc, ot[513:512], t1[513:512], popc({2'b0, ot[511:0] ^ t1[511:0]}));
    end
    if (u_k1.u_g.u_tile.u_tile.u_logic.u_me.idle !== u_k0.u_g.u_tile.u_tile.u_logic.u_me.idle) idiff = idiff + 1;
    if (t1[512]) begin tval = tval + 1; if (|t1[511:0]) tnz = tnz + 1; end
    if (!u_k1.g_icg.en) gated = gated + 1;
    if (!u_k1.u_g.u_tile.u_tile.u_logic.u_me.idle) busy = busy + 1;
    if (u_k1.g_icg.en && !last_en) wake = wake + 1;
    last_en = u_k1.g_icg.en;
  end
  $display("IDLEUCK_COUNTS MUT=%0d checks=%0d t_valid=%0d t_nonzero=%0d gated_cycles=%0d (%0d%%) k1_busy=%0d wakeups=%0d idle_k0_vs_k1_diff_cycles=%0d forced=%0d",
    MUT, checks, tval, tnz, gated, gated * 100 / checks, busy, wake, idiff, forced);
  if (tval == 0 || tnz == 0 || gated == 0 || wake < 3) $display("IDLEUCK_ACTIVITY_MISSING");
  if (serr || qerr) $display("IDLEUCK_FAIL MUT=%0d strict_k0_k1_errors=%0d first=%0d qualified_vs_ungated_errors=%0d first=%0d checks=%0d", MUT, serr, sfirst, qerr, qfirst, checks);
  else if (tval > 0 && tnz > 0 && gated > 0 && wake >= 3) $display("IDLEUCK_PASS MUT=%0d checks=%0d strict_k0_k1=0 qualified_vs_ungated=0 gated=%0d", MUT, checks, gated);
  $finish;
end
endmodule
