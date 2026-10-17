#!/bin/bash
# Bench of one F1 forwarded-clock HBM die relay master hbfd_rly_<W>_<FLOW>_fc (Verilator 5.050).
#   bench_rly_fc.sh <pass|mut|ckmut> <W> <FLOW> <work dir>
# 20,000 words (zero words under the reset releases), every cycle and every bit:
#   (1) o of the _fc tile == the previous cycle's i (the old bench_rly.sh model) AND == o of the existing tile
#       hbfd_rly_<W>_<FLOW> clocked by the same clock (lockstep: the register stage is unchanged);
#   (2) clk_out == clk_in at both clock levels;
#   (3) a SECOND _fc tile clocked by the first one's clk_out and fed by its o reproduces o one cycle later (the chain
#       forwards a usable clock);  async clear checked mid-stream.
# mut: OT_HBM_RLY_MUT (bit 0 of the register inverted) -> FAIL.  ckmut: OT_HBM_RLY_FC_MUT_CLKOUT (clk_out held low) -> FAIL.
set -u
mode=$1; W=$2; FL=$3; O=$4
M=hbfd_rly_${W}_${FL}
cd "$(dirname "$0")/../../../.."; mkdir -p "$O"
[ -d /home/ubuntu/.local/opentallas-tools/verilator-5.050/bin ] && export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
cat > "$O/tb.sv" <<EOT
module tb;
  reg ck = 0, rs = 0; reg [$W-1:0] i = 0; wire [$W-1:0] o_old, o1, o2; wire ck1, ck2; reg [$W-1:0] ex = 0, ex2 = 0;
  integer n = 0, err = 0, cerr = 0, perr = 0;
  $M u_old (.ck(ck), .rs(rs), .i(i), .o(o_old));
  ${M}_fc u_fc1 (.clk_in(ck), .rs(rs), .i(i), .o(o1), .clk_out(ck1));
  ${M}_fc u_fc2 (.clk_in(ck1), .rs(rs), .i(o1), .o(o2), .clk_out(ck2));
  always #5 ck = ~ck;
  always @(ck) begin #1 if (ck1 !== ck || ck2 !== ck) cerr = cerr + 1; end
  initial begin
    repeat (3) @(negedge ck); if (o1 !== '0 || o2 !== '0) err = err + 1;
    rs = 1;
    for (n = 0; n < 20000; n = n + 1) begin
      @(negedge ck);
      if (o1 !== ex || o1 !== o_old) err = err + 1;
      if (n > 9010 || (n > 10 && n < 9000)) if (o2 !== ex2) perr = perr + 1;
      if (n == 9000) begin rs = 0; #1 if (o1 !== '0 || o2 !== '0) err = err + 1; ex = '0; #1 rs = 1; end
      if (n < 4 || (n >= 9000 && n < 9004)) i = '0; else for (int b = 0; b < $W; b++) i[b] = \$urandom;
      @(posedge ck); ex2 = ex; ex = i;
    end
    \$display("RLY_FC_BENCH %s %0d errors %0d clock_errors %0d chain_errors in %0d words (%s_fc W=%0d)",
              (err || cerr || perr) ? "FAIL" : "PASS", err, cerr, perr, n, "$M", $W);
    \$finish;
  end
endmodule
EOT
DEF=""; [ "$mode" = mut ] && DEF="-DOT_HBM_RLY_MUT"; [ "$mode" = ckmut ] && DEF="-DOT_HBM_RLY_FC_MUT_CLKOUT"
verilator --binary --timing -Wno-fatal -Wno-WIDTH $DEF --top-module tb -Mdir "$O/obj" -o tb \
  "$O/tb.sv" rtl/lib/ot_rst_relay.sv rtl/hbm_accel/die_glue/ot_hbm_rly.sv rtl/hbm_accel/die_glue/hbfd_rly_masters.sv \
  rtl/hbm_accel/die_glue/ot_hbm_rly_fc.sv rtl/hbm_accel/die_glue/hbfd_rly_fc_masters.sv > "$O/build.log" 2>&1 || { echo BUILD_FAILED; tail -5 "$O/build.log"; exit 2; }
"$O/obj/tb" | tee "$O/bench.log" | grep RLY_FC_BENCH
grep -q 'RLY_FC_BENCH PASS' "$O/bench.log"
