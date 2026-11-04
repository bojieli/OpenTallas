`timescale 1ns/1ps
// DIE-QC-66/CORES-NK 11-03 A0 NL NKP bench (tb_a0_nkp.sv with NL ports: no n_a / n_b / n_y):
//   u_k0 = NL kit form (G4_ROOTS 1, REGROOT_MODE 3, ICG 1, ICG_RRST 1), NKP 0 (== kit RTL)
//   u_k1 = the same with NKP 2 (bit1: raw XTX rung 0 + per-leaf BF16 round, the REGROOT 8 rung-0 form)
//   STRICT: every output bit (t_out, tie_hi/lo) at every negedge, plus the engine's architectural issue state every cycle.
// +MUT=3: u_k1 leaf 0 (slice 0) group 0 BF16 round carry cy forced 0 -> must FAIL
// +MUT=7: u_k1 leaf 0 (slice 1) group 0 BF16 round carry cy forced 0 -> must FAIL
module tb_a0_nlp;
integer NCYC = 14000, MUT = 0;
initial begin
  if ($value$plusargs("NCYC=%d", NCYC)) begin end
  if ($value$plusargs("MUT=%d", MUT)) begin end
end
reg ck = 0; always #0.5 ck = ~ck;
reg rs = 0;
reg [507:0] tap = 0;
wire [513:0] t0, t1;
wire h0, l0, h1, l1;
qfd_tile_nl_a0c #(.G4_ROOTS(1), .REGROOT_MODE(3), .ICG(1), .ICG_RRST(1), .NKP(0), .ROM_TILE(48)) u_k0 (
  .ck(ck), .rst_n(rs), .tile_id(16'd48), .tie_hi(h0), .tie_lo(l0), .tap(tap), .t_out(t0));
qfd_tile_nl_a0c #(.G4_ROOTS(1), .REGROOT_MODE(3), .ICG(1), .ICG_RRST(1), .NKP(7), .ROM_TILE(48)) u_k1 (
  .ck(ck), .rst_n(rs), .tile_id(16'd48), .tie_hi(h1), .tie_lo(l1), .tap(tap), .t_out(t1));
`define ME0 u_k0.u_g.u_tile.u_tile.u_logic.u_me
`define ME1 u_k1.u_g.u_tile.u_tile.u_logic.u_me
// {nout, tiles, k, wsrc, wbase, ts, ks, js, xbase, xks, xjs, xcs, jsh, split, wcs, round, obase, ots, ojs, mmode, oen, amax, rmax, mbase}
function automatic [378:0] cmd(input integer tiles, input integer kk, input integer wsrc, input integer wbase, input integer ts,
                               input integer split, input integer wcs, input integer rnd);
 cmd = {18'd4096, 18'(tiles), 18'(kk), 1'(wsrc), 24'(wbase), 24'(ts), 24'd8, 24'd1,
        24'd0, 24'd1, 24'd1, 24'd1, 3'd0, 4'(split), 24'(wcs), 1'(rnd), 24'd0, 24'd1, 24'd1,
        1'b0, 1'b1, 1'b0, 1'b0, 24'd0};
endfunction
function automatic [378:0] command(input integer n);
  case (n % 9)
    0: command = cmd(2, 32, 0, 0,     64, 7, 1, 0);   // the A0 ICG bench command (bank 0)
    1: command = cmd(3, 300, 1, 512,  5, 7, 3, 0);    // KV, ragged K = 300 at S = 128 (K-limit masks), 3 rounds
    2: command = cmd(3, 4, 0, 4096,   64, 8, 1, 1);   // weight, BF16 round
    3: command = cmd(4, 100, 1, 77,   9, 7, 5, 1);    // KV, K <= S: a round boundary every IL cycles
    4: command = cmd(2, 1000, 1, 3,   11, 9, 2, 0);   // KV, S = 512, ragged
    5: command = cmd(2, 16, 0, 8192,  64, 7, 1, 1);   // weight, round
    6: command = cmd(5, 129, 1, 1000, 13, 7, 7, 1);   // KV, K = S + 1
    7: command = cmd(2, 2000, 1, 0,   3, 11, 1, 0);   // KV, S = 2048
    default: command = cmd(2, 8, 0, 12288, 64, 10, 1, 0);
  endcase
endfunction
function automatic integer popc(input [513:0] v);
  integer i; popc = 0; for (i = 0; i < 514; i = i + 1) popc = popc + v[i];
endfunction
function automatic integer isgo(input integer c);
  isgo = (c == 200 || c == 900 || c == 1300 || c == 1900 || c == 2300 || c == 2900 || c == 3300 || c == 3800 || c == 4400
          || c == 5000 || c == 5600 || c == 6100 || c == 7300 || c == 7900 || c == 8600 || c == 9500 || c == 9530
          || c == 10100 || c == 10700 || c == 10701 || c == 11300 || c == 11900 || c == 12500 || c == 13100);
endfunction
integer cyc, serr = 0, sfirst = -1, ierr = 0, ifirst = -1, checks = 0, tval = 0, tnz = 0, cmds = 0, kvact = 0, gmz = 0;
integer mfail = 0;
wire [1023:0] st0 = {`ME0.active, `ME0.pend, `ME0.cur, `ME0.base_k, `ME0.base_t, `ME0.k, `ME0.t, `ME0.j, `ME0.ot, `ME0.oa,
                     `ME0.wrom_re, `ME0.wrom_addr, `ME0.kv_re, `ME0.kv_addr, `ME0.e_v, (`ME0.e_v ? `ME0.e_gm : 4'd0)};
wire [1023:0] st1 = {`ME1.active, `ME1.pend, `ME1.cur, `ME1.base_k, `ME1.base_t, `ME1.k, `ME1.t, `ME1.j, `ME1.ot, `ME1.oa,
                     `ME1.wrom_re, `ME1.wrom_addr, `ME1.kv_re, `ME1.kv_addr, `ME1.e_v, (`ME1.e_v ? `ME1.e_gm : 4'd0)};
initial begin
  if (MUT == 3) force `ME1.g_hier.g_sl[0].g_hd.g_tx.g_lx.g_x[0].cy = 1'b0;
  if (MUT == 7) force `ME1.g_hier.g_sl[1].g_hd.g_tx.g_lx.g_x[0].cy = 1'b0;
  repeat (8) @(negedge ck); rs = 1;
  for (cyc = 0; cyc < NCYC; cyc = cyc + 1) begin
    tap[0] = 0;
    if (isgo(cyc)) begin tap[379:1] = command(cmds); tap[0] = 1; cmds = cmds + 1; end
    for (integer g = 0; g < 4; g = g + 1)
      tap[380 + g*32 +: 32] = {(((cyc / 700) % 2) == 1), 31'h3f800000 + ((cyc % 8 + g) << 18) + ((cyc * 32'h1357 + g * 32'h9e37) & 32'hFFFF)};
    if (cyc == 7000) rs = 0;                              // reset pulse while idle
    if (cyc == 7005) rs = 1;
    if (cyc == 8700) rs = 0;                              // reset while busy
    if (cyc == 8703) rs = 1;
    @(negedge ck);
    checks = checks + 1;
    if (t1 !== t0 || h1 !== h0 || l1 !== l0) begin
      serr = serr + 1; if (sfirst < 0) sfirst = cyc;
      if (serr <= 3) $display("NKP_SMISMATCH cyc%0d t_out %0d bits ([513:512] k0 %b k1 %b)", cyc, popc(t0 ^ t1), t0[513:512], t1[513:512]);
    end
    if (st1 !== st0) begin
      ierr = ierr + 1; if (ifirst < 0) ifirst = cyc;
      if (ierr <= 3) $display("NKP_IMISMATCH cyc%0d engine state differs (e_gm k0 %b k1 %b cur k0 %h k1 %h)", cyc, `ME0.e_gm, `ME1.e_gm, `ME0.cur, `ME1.cur);
    end
    if (t1[512]) begin tval = tval + 1; if (|t1[511:0]) tnz = tnz + 1; end
    if (`ME0.e_v && `ME0.e_wsrc) begin kvact = kvact + 1; if (`ME0.e_gm != 4'hF) gmz = gmz + 1; end
  end
  $display("NKP_COUNTS MUT=%0d checks=%0d cmds=%0d t_valid=%0d t_nonzero=%0d kv_elems=%0d kv_masked_elems=%0d", MUT, checks, cmds, tval, tnz, kvact, gmz);
  if (tval == 0 || tnz == 0) $display("NKP_ACTIVITY_MISSING");
  if (serr || ierr) $display("NKP_FAIL MUT=%0d strict_out_errors=%0d first=%0d engine_state_errors=%0d first=%0d checks=%0d", MUT, serr, sfirst, ierr, ifirst, checks);
  else if (tval > 0 && tnz > 0) $display("NKP_PASS MUT=%0d checks=%0d strict_out=0 engine_state=0", MUT, checks);
  $finish;
end
endmodule
