#!/bin/bash
# Bit-exact bench of one S81 relay master (Verilator 5.050).  usage: bench_rly.sh <pass|mut|rsmut> <master> <W> <work dir> [RSREG]
# pass: 20,000 random words, o must equal the previous cycle's i on every cycle; async clear checked mid-stream.
# mut : the same bench on the OT_S81_RLY_MUT build (bit 0 inverted in the register) -- must FAIL.
# RSREG=1 (5th argument; masters built with ot_s81_rly #(.RSREG(1))): the first ck edge after every rs release is the reset
# pin register's release edge, so the data register stays cleared on it (expected word 0; the first release edge falls
# before the stream).
# rsmut: the RSREG master on the OT_S81_RLY_RSMUT build (reset pin register bypassed) -- must FAIL.
set -u
mode=$1; M=$2; W=$3; O=$4; RSR=${5:-0}
cd "$(dirname "$0")/../../../.."; mkdir -p "$O"
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
if [ "$W" = 1 ]; then DECL="reg i = 0; wire o; reg ex = 0;"; RND="i = \$urandom;"; else DECL="reg [$W-1:0] i = 0; wire [$W-1:0] o; reg [$W-1:0] ex = 0;"; RND="for (int b = 0; b < $W; b++) i[b] = \$urandom;"; fi
cat > "$O/tb.sv" <<EOT
module tb;
  reg ck = 0, rs = 0; $DECL
  integer n = 0, err = 0, hold = 0;
  $M dut(.ck(ck), .rs(rs), .i(i), .o(o));
  always #5 ck = ~ck;
  initial begin
    repeat (3) @(negedge ck); if (o !== '0) err = err + 1;
    rs = 1;
    for (n = 0; n < 20000; n = n + 1) begin
      @(negedge ck); if (o !== ex) err = err + 1;
      if (n == 9000) begin rs = 0; #1 if (o !== '0) err = err + 1; ex = '0; #1 rs = 1; hold = $RSR; end
      $RND
      @(posedge ck); if (hold) begin ex = '0; hold = 0; end else ex = i;
    end
    \$display("RLY_BENCH %s %0d errors in %0d words (%s W=%0d)", err ? "FAIL" : "PASS", err, n, "$M", $W);
    \$finish;
  end
endmodule
EOT
DEF=""; [ "$mode" = mut ] && DEF="-DOT_S81_RLY_MUT"; [ "$mode" = rsmut ] && DEF="-DOT_S81_RLY_RSMUT"
verilator --binary --timing -Wno-fatal -Wno-WIDTH $DEF --top-module tb -Mdir "$O/obj" -o tb \
  "$O/tb.sv" rtl/dsrom_sys/s81_glue/ot_s81_rly.sv rtl/dsrom_sys/s81_glue/dsfd_rly_masters*.sv > "$O/build.log" 2>&1 || { echo BUILD_FAILED; tail -5 "$O/build.log"; exit 2; }
"$O/obj/tb" | tee "$O/bench.log" | grep RLY_BENCH
grep -q 'RLY_BENCH PASS' "$O/bench.log"
