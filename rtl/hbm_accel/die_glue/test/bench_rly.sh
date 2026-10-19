#!/bin/bash
# Bit-exact bench of one HBM die relay master (Verilator 5.050).  usage: bench_rly.sh <pass|mut|rrmut> <master> <W> <work dir> [REL]
# pass: 20,000 words (random but for 8 zero words under the two reset releases), o must equal the previous cycle's i on every cycle and every bit; async clear checked
#       mid-stream.   mut: the same bench on the OT_HBM_RLY_MUT build (bit 0 inverted in the register) -- must FAIL.
# REL (HBM-NATIVE5/RLY4 2026-10-18, default 0 = the bench as before): a master built with ot_hbm_rly RS_RELAY=1 releases
# its stage REL = 3 clock edges after rs.  REL > 0: RANDOM words also under both reset releases (initial + mid-stream),
# o must be 0 for the first REL edges after rs rises and the previous cycle's i after that (expected-o model); >= REL
# non-zero in-window words must have been dropped (non-vacuous).  rrmut: OT_HBM_RLY_MUT_NORR (reset relay bypassed,
# release on the rs edge) -> FAIL under REL > 0.
set -u
mode=$1; M=$2; W=$3; O=$4; REL=${5:-0}
cd "$(dirname "$0")/../../../.."; mkdir -p "$O"
[ -d /home/ubuntu/.local/opentallas-tools/verilator-5.050/bin ] && export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
cat > "$O/tb.sv" <<EOT
module tb;
  reg ck = 0, rs = 0; reg [$W-1:0] i = 0; wire [$W-1:0] o; reg [$W-1:0] ex = 0;
  integer n = 0, err = 0, rel = 0, win = 0;
  $M dut(.ck(ck), .rs(rs), .i(i), .o(o));
  always #5 ck = ~ck;
  initial begin
    repeat (3) @(negedge ck); if (o !== '0) err = err + 1;
    rs = 1; rel = 1;   // the posedge before the first loop check (i = 0) is release edge 1 of the relay
    for (n = 0; n < 20000; n = n + 1) begin
      @(negedge ck); if (o !== ex) err = err + 1;
      if (n == 9000) begin rs = 0; #1 if (o !== '0) err = err + 1; ex = '0; rel = 0; #1 rs = 1; end
      // the words under a reset release (the first 4, and 4 after the mid-stream clear) are zero: a class > 256 b
      // releases its flops 3 clock edges after rs (registered reset relay)
      if ($REL == 0 && (n < 4 || (n >= 9000 && n < 9004))) i = '0; else for (int b = 0; b < $W; b++) i[b] = \$urandom;
      @(posedge ck);
      if (rel < $REL) begin rel = rel + 1; ex = '0; if (i !== '0) win = win + 1; end else ex = i;
    end
    if (win < $REL) err = err + 1;
    \$display("RLY_BENCH %s %0d errors in %0d words (%s W=%0d) release_edges=%0d window_words=%0d", err ? "FAIL" : "PASS", err, n, "$M", $W, $REL, win);
    \$finish;
  end
endmodule
EOT
DEF=""; [ "$mode" = mut ] && DEF="-DOT_HBM_RLY_MUT"; [ "$mode" = rrmut ] && DEF="-DOT_HBM_RLY_MUT_NORR"
verilator --binary --timing -Wno-fatal -Wno-WIDTH $DEF --top-module tb -Mdir "$O/obj" -o tb \
  "$O/tb.sv" rtl/lib/ot_rst_relay.sv rtl/hbm_accel/die_glue/ot_hbm_rly.sv rtl/hbm_accel/die_glue/hbfd_rly_masters.sv > "$O/build.log" 2>&1 || { echo BUILD_FAILED; tail -5 "$O/build.log"; exit 2; }
"$O/obj/tb" | tee "$O/bench.log" | grep RLY_BENCH
grep -q 'RLY_BENCH PASS' "$O/bench.log"
