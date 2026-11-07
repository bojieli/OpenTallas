`timescale 1ns/1ps
// QC-A0C-B5 11-06 vB bench (tools/qwen_romleaf/a0core/lqr/): qfd_tile_<t>_a0c LQR=0 (ref) vs LQR=`TB_LQR (dut), both with the
// kit's top parameters, same stimulus (tb_a0_icg pattern: 5 commands over all banks, x line / n data toggling every cycle,
// node traffic windows, an idle reset pulse, back-to-back go while busy).  LQR adds cycles, so t_out is compared as a
// latency-shifted stream: the k-th valid word of dut == the k-th valid word of ref (data and fault bit), equal counts,
// and the dut - ref cycle delta of every word is reported (= the PIN CYCLES).  n_y (node path, LQR does not touch it) is
// compared every edge.  `OT_LQR_MUT selects an RTL mutant (lqr_patch.py) that must FAIL.
`ifndef TB_LQR
`define TB_LQR 1
`endif
module tb_a0_lqr;
integer NCYC = 12000;
initial if ($value$plusargs("NCYC=%d", NCYC)) begin end
reg ck = 0; always #0.5 ck = ~ck;
reg rs = 0;
reg [507:0] tap = 0;
reg [513:0] na = 0, nb = 0;
wire [513:0] rt, dt, rn, dn;
wire rhi, rlo, dhi, dlo;
// TB_OLD (default-off proof): ref = the kit's ORIGINAL rtl (before lqr_patch.py), every module prefixed K_ (equiv/rename.py)
`ifdef TB_OLD
`define REF_NL K_qfd_tile_nl_a0c
`define REF_NK K_qfd_tile_nk_a0c
`define REF_LQR
`else
`define REF_NL qfd_tile_nl_a0c
`define REF_NK qfd_tile_nk_a0c
`define REF_LQR .LQR(0),
`endif
`ifdef TB_NL
`REF_NL #(.G4_ROOTS(1), .REGROOT_MODE(3), .ICG(1), .ICG_RRST(1), .NKP(15), `REF_LQR .ROM_TILE(48)) u_ref
  (.ck(ck), .rst_n(rs), .tile_id(16'd48), .tie_hi(rhi), .tie_lo(rlo), .tap(tap), .t_out(rt));
qfd_tile_nl_a0c #(.G4_ROOTS(1), .REGROOT_MODE(3), .ICG(1), .ICG_RRST(1), .NKP(15), .LQR(`TB_LQR), .ROM_TILE(48)) u_dut
  (.ck(ck), .rst_n(rs), .tile_id(16'd48), .tie_hi(dhi), .tie_lo(dlo), .tap(tap), .t_out(dt));
assign rn = 0; assign dn = 0;
localparam TILE = "nl";
`else
`REF_NK #(.G4_ROOTS(1), .REGROOT_MODE(3), .ICG(1), .ICG_EREG(1), .ICG_IREG(1), .ICG_RRST(1), .NKP(15), .ICG_IDLE_RT(1),
  `REF_LQR .ROM_TILE(48)) u_ref
  (.ck(ck), .rst_n(rs), .tile_id(16'd48), .tie_hi(rhi), .tie_lo(rlo), .tap(tap), .t_out(rt), .n_a(na), .n_b(nb), .n_y(rn));
qfd_tile_nk_a0c #(.G4_ROOTS(1), .REGROOT_MODE(3), .ICG(1), .ICG_EREG(1), .ICG_IREG(1), .ICG_RRST(1), .NKP(15), .ICG_IDLE_RT(1),
  .LQR(`TB_LQR), .ROM_TILE(48)) u_dut
  (.ck(ck), .rst_n(rs), .tile_id(16'd48), .tie_hi(dhi), .tie_lo(dlo), .tap(tap), .t_out(dt), .n_a(na), .n_b(nb), .n_y(dn));
localparam TILE = "nk";
`endif
// vB2 (lqr2_patch.py): the t_out fault bit [513] is a status, compared as its own stream shifted by TB_FSHIFT
// (LQR bit3: +1); `OT_LQR_FINJ injects one fault pulse in both sides so the fault path is exercised.
`ifndef TB_FSHIFT
`define TB_FSHIFT 0
`endif
`ifdef OT_LQR_FINJ
localparam integer FINJ = 1;
`else
localparam integer FINJ = 0;
`endif
`ifdef OT_LQR_MUT
localparam integer MUT = `OT_LQR_MUT;
`else
localparam integer MUT = 0;
`endif
function automatic [378:0] command(input integer bank);
 command={18'd4096,18'd2,18'd32,1'b0,24'(bank*4096),24'd64,24'd8,24'd1,
          24'd0,24'd1,24'd1,24'd1,3'd0,4'd7,24'd1,1'b0,24'd0,24'd1,24'd1,
          1'b0,1'b1,1'b0,1'b0,24'd0};
endfunction
function automatic integer isgo(input integer c);
  isgo = (c == 200 || c == 1400 || c == 2600 || c == 3800 || c == 5000 || c == 7300 || c == 8600 || c == 9500
          || c == 9530 || c == 10400 || c == 10401);
endfunction
// valid t_out words (data + fault bit) of each side, in order, with their cycle
reg [512:0] rq [0:65535]; integer rc [0:65535]; integer nr = 0;
reg [512:0] dq [0:65535]; integer dc [0:65535]; integer nd = 0;
integer cyc, cmds = 0, nerr = 0, nfirst = -1, tnz = 0, rfault = 0, dfault = 0, k, derr = 0, dfirst = -1, dmin = 1 << 30, dmax = -(1 << 30);
integer hist [0:15];
integer rfc [0:65535]; integer dfc [0:65535]; integer nrf = 0, ndf = 0, ferr = 0;
integer nstrict = 0, nval = 0;
initial begin
  for (k = 0; k < 16; k = k + 1) hist[k] = 0;
  repeat (8) @(negedge ck); rs = 1;
  for (cyc = 0; cyc < NCYC; cyc = cyc + 1) begin
    tap[0] = 0;
    if (isgo(cyc)) begin tap[379:1] = command(cmds % 5); tap[0] = 1; cmds = cmds + 1; end
    for (integer g = 0; g < 4; g = g + 1) tap[380 + g*32 +: 32] = 32'h3f800000 + ((cyc % 8 + g) << 18);
    for (integer lane = 0; lane < 16; lane = lane + 1) begin
      na[lane*32 +: 32] = 32'h3f000000 + ((cyc % 16 + lane) << 17);
      nb[lane*32 +: 32] = 32'h3f800000 + ((cyc % 8 + lane) << 17);
    end
    na[513:512] = {(cyc == 6205), ((cyc >= 600 && cyc < 900) || (cyc >= 6000 && cyc < 6400)) && (cyc % 11 == 0)};
    nb[513:512] = na[513:512];
    if (cyc == 6300) nb[512] = 1;                         // one misaligned leg (node sticky fault)
    if (cyc == 7000) rs = 0;                              // reset pulse while idle (no busy reset: a run cut by
    if (cyc == 7005) rs = 1;                              // reset legitimately ends at a different word with LQR)
    @(negedge ck);
    if (rt[512]) begin rq[nr] = {1'b0, rt[511:0]}; rc[nr] = cyc; nr = nr + 1; if (|rt[511:0]) tnz = tnz + 1; end
    if (dt[512]) begin dq[nd] = {1'b0, dt[511:0]}; dc[nd] = cyc; nd = nd + 1; end
    if (rt[513]) begin rfault = rfault + 1; rfc[nrf] = cyc; nrf = nrf + 1; end
    if (dt[513]) begin dfault = dfault + 1; dfc[ndf] = cyc; ndf = ndf + 1; end
    // n_y: valid / fault bits every edge, data under valid (the tile contract, as tb_a0_icg: invalid words carry
    // free-running node data, which the root ICG holds for different idle stretches once LQR lengthens a run)
    if (rn[513:512] !== dn[513:512] || (rn[512] && rn[511:0] !== dn[511:0]) || rhi !== dhi || rlo !== dlo) begin
      nerr = nerr + 1; if (nfirst < 0) nfirst = cyc; end
    if (rn !== dn) nstrict = nstrict + 1;
    if (rn[512]) nval = nval + 1;
  end
  for (k = 0; k < nr && k < nd; k = k + 1) begin
    if (rq[k] !== dq[k]) begin derr = derr + 1; if (dfirst < 0) dfirst = k;
      if (derr <= 3) $display("A0LQR_MISMATCH word %0d ref cyc %0d dut cyc %0d", k, rc[k], dc[k]); end
    if (dc[k] - rc[k] < dmin) dmin = dc[k] - rc[k];
    if (dc[k] - rc[k] > dmax) dmax = dc[k] - rc[k];
    if (dc[k] - rc[k] >= 0 && dc[k] - rc[k] < 16) hist[dc[k] - rc[k]] = hist[dc[k] - rc[k]] + 1;
  end
  for (k = 0; k < nrf && k < ndf; k = k + 1) if (dfc[k] - rfc[k] != `TB_FSHIFT) ferr = ferr + 1;
  $display("A0LQR_FAULT fault edges ref=%0d dut=%0d first ref=%0d dut=%0d shift_mismatch=%0d declared_shift=%0d inject=%0d",
    nrf, ndf, (nrf > 0) ? rfc[0] : -1, (ndf > 0) ? dfc[0] : -1, ferr, `TB_FSHIFT, FINJ);
  $display("A0LQR_COUNTS tile=%s LQR=%0d MUT=%0d cmds=%0d ref_words=%0d dut_words=%0d nonzero=%0d fault_cycles ref=%0d dut=%0d",
    TILE, `TB_LQR, MUT, cmds, nr, nd, tnz, rfault, dfault);
  $display("A0LQR_NODE n_y valid words=%0d qualified_mismatch_edges=%0d strict_mismatch_edges=%0d (info)", nval, nerr, nstrict);
  $display("A0LQR_SHIFT t_out delta min=%0d max=%0d hist d0=%0d d1=%0d d2=%0d d3=%0d d4=%0d", dmin, dmax, hist[0], hist[1], hist[2], hist[3], hist[4]);
  if (nr == 0 || tnz == 0 || (TILE == "nk" && nval == 0) || nr != nd || derr != 0 || nerr != 0 || rfault != dfault || ferr != 0 || (FINJ != 0 && nrf == 0) || dmin != dmax)
    $display("A0LQR_FAIL tile=%s LQR=%0d MUT=%0d word_mismatch=%0d (first word %0d) count ref=%0d dut=%0d n_y/tie_mismatch_edges=%0d (first %0d) delta %0d..%0d",
      TILE, `TB_LQR, MUT, derr, dfirst, nr, nd, nerr, nfirst, dmin, dmax);
  else
    $display("A0LQR_PASS tile=%s LQR=%0d MUT=%0d words=%0d t_out_added_cycles=%0d n_y_exact_edges=%0d", TILE, `TB_LQR, MUT, nr, dmin, NCYC);
  $finish;
end
endmodule
