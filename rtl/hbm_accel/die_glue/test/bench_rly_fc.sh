#!/bin/bash
# Bench of one F1 forwarded-clock HBM die relay master hbfd_rly_<W>_<FLOW>_fc (Verilator 5.050).
#   bench_rly_fc.sh <pass|mut|ckmut|rrmut> <W> <FLOW> <work dir> [REL]
# 20,000 words (zero words under the reset releases when REL = 0), every cycle and every bit:
#   (1) o of the _fc tile == the previous cycle's i (the old bench_rly.sh model) AND == o of the existing tile
#       hbfd_rly_<W>_<FLOW> clocked by the same clock (lockstep: the register stage is unchanged);
#   (2) clk_out == clk_in at both clock levels;
#   (3) a SECOND _fc tile clocked by the first one's clk_out and fed by its o reproduces o one cycle later (the chain
#       forwards a usable clock);  async clear checked mid-stream.
# mut: OT_HBM_RLY_MUT (bit 0 of the register inverted) -> FAIL.  ckmut: OT_HBM_RLY_FC_MUT_CLKOUT (clk_out held low) -> FAIL.
# REL (NATIVE-FIX3 2026-10-18, default 0 = the bench as before): a master built with ot_hbm_rly RS_RELAY=1 releases its
# stage REL = 3 clock edges after rs.  REL > 0: RANDOM words also under both reset releases (initial + mid-stream), o of the
# _fc tile must be 0 for the first REL edges after rs rises and the previous cycle's i after that (expected-o model);
# the unchanged old tile hbfd_rly_<W>_<FLOW> is checked against the plain model, and the two must agree outside the
# REL-edge windows; >= REL non-zero in-window words must have been dropped (non-vacuous).
# rrmut: OT_HBM_RLY_MUT_NORR (reset relay bypassed, release on the rs edge) -> FAIL under REL > 0.
# OREL (HBM-NATIVE5/RLY4 2026-10-18): the release edges of the OLD tile hbfd_rly_<W>_<FLOW> itself, read from its RTL
# (3 when its ot_hbm_rly takes RS_RELAY(1), as the base 136 NS / SN since RLY4, or W > 256; else 0): the old tile is
# checked against the plain model delayed by OREL edges, and the lockstep compare skips both windows.
set -u
mode=$1; W=$2; FL=$3; O=$4; REL=${5:-0}
M=hbfd_rly_${W}_${FL}
cd "$(dirname "$0")/../../../.."; mkdir -p "$O"
OREL=0
if [ "$W" -gt 256 ] || awk -v m="$M" '$1 == "module" && $2 == m { getline; print; exit }' rtl/hbm_accel/die_glue/hbfd_rly_masters.sv | grep -q 'RS_RELAY(1)'; then OREL=3; fi
[ -d /home/ubuntu/.local/opentallas-tools/verilator-5.050/bin ] && export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
cat > "$O/tb.sv" <<EOT
module tb;
  reg ck = 0, rs = 0; reg [$W-1:0] i = 0; wire [$W-1:0] o_old, o1, o2; wire ck1, ck2; reg [$W-1:0] ex = 0, ex2 = 0;
  integer n = 0, err = 0, cerr = 0, perr = 0, rel = 0, win = 0, inw = 0, relo = 0, inwo = 0; reg [$W-1:0] exo = 0;
  $M u_old (.ck(ck), .rs(rs), .i(i), .o(o_old));
  ${M}_fc u_fc1 (.clk_in(ck), .rs(rs), .i(i), .o(o1), .clk_out(ck1));
  ${M}_fc u_fc2 (.clk_in(ck1), .rs(rs), .i(o1), .o(o2), .clk_out(ck2));
  always #5 ck = ~ck;
  always @(ck) begin #1 if (ck1 !== ck || ck2 !== ck) cerr = cerr + 1; end
  initial begin
    repeat (3) @(negedge ck); if (o1 !== '0 || o2 !== '0) err = err + 1;
    rs = 1; rel = 1; relo = 1;   // the posedge before the first loop check (i = 0) is release edge 1 of the relay
    for (n = 0; n < 20000; n = n + 1) begin
      @(negedge ck);
      if (o1 !== ex || o_old !== exo || (!inw && !inwo && o1 !== o_old)) err = err + 1;
      if (n > 9010 || (n > 10 && n < 9000)) if (o2 !== ex2) perr = perr + 1;
      if (n == 9000) begin rs = 0; #1 if (o1 !== '0 || o2 !== '0) err = err + 1; ex = '0; exo = '0; rel = 0; relo = 0; #1 rs = 1; end
      if ($REL == 0 && (n < 4 || (n >= 9000 && n < 9004))) i = '0; else for (int b = 0; b < $W; b++) i[b] = \$urandom;
      @(posedge ck); ex2 = ex;
      inwo = (relo < $OREL); if (inwo) begin relo = relo + 1; exo = '0; end else exo = i;
      inw = (rel < $REL); if (inw) begin rel = rel + 1; ex = '0; if (i !== '0) win = win + 1; end else ex = i;
    end
    if (win < $REL) err = err + 1;
    \$display("RLY_FC_BENCH %s %0d errors %0d clock_errors %0d chain_errors in %0d words (%s_fc W=%0d) release_edges=%0d window_words=%0d",
              (err || cerr || perr) ? "FAIL" : "PASS", err, cerr, perr, n, "$M", $W, $REL, win);
    \$finish;
  end
endmodule
EOT
DEF=""; [ "$mode" = mut ] && DEF="-DOT_HBM_RLY_MUT"; [ "$mode" = ckmut ] && DEF="-DOT_HBM_RLY_FC_MUT_CLKOUT"; [ "$mode" = rrmut ] && DEF="-DOT_HBM_RLY_MUT_NORR"
verilator --binary --timing -Wno-fatal -Wno-WIDTH $DEF --top-module tb -Mdir "$O/obj" -o tb \
  "$O/tb.sv" rtl/lib/ot_rst_relay.sv rtl/hbm_accel/die_glue/ot_hbm_rly.sv rtl/hbm_accel/die_glue/hbfd_rly_masters.sv \
  rtl/hbm_accel/die_glue/ot_hbm_rly_fc.sv rtl/hbm_accel/die_glue/hbfd_rly_fc_masters.sv > "$O/build.log" 2>&1 || { echo BUILD_FAILED; tail -5 "$O/build.log"; exit 2; }
"$O/obj/tb" | tee "$O/bench.log" | grep RLY_FC_BENCH
grep -q 'RLY_FC_BENCH PASS' "$O/bench.log"
