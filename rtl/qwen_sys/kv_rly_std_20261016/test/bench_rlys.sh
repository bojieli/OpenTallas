#!/bin/bash
# Bit-exact bench of one KV die relay standard (Verilator 5.050).  usage: bench_rlys.sh <pass|mut> <master> <W> <work dir>
# pass: 20,000 random words; b must equal the previous cycle's a on every cycle and every bit (one register stage).
# mut:  the same bench on the OT_QKD_RLYS_MUT build (bit 0 inverted in the register) -- must FAIL.
set -u
mode=$1; M=$2; W=$3; O=$4
cd "$(dirname "$0")/../../../.."; mkdir -p "$O"
[ -d /home/ubuntu/.local/opentallas-tools/verilator-5.050/bin ] && export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
cat > "$O/tb.sv" <<EOT
module tb;
  reg ck = 0; reg [$W-1:0] a = 0; wire [$W-1:0] b; reg [$W-1:0] ex = 0;
  integer n = 0, err = 0;
  $M dut(.ck(ck), .a(a), .b(b));
  always #5 ck = ~ck;
  initial begin
    @(posedge ck); ex = a;
    for (n = 0; n < 20000; n = n + 1) begin
      @(negedge ck); if (b !== ex) err = err + 1;
      for (int k = 0; k < $W; k++) a[k] = \$urandom;
      @(posedge ck); ex = a;
    end
    \$display("RLYS_BENCH %s %0d errors in %0d words (%s W=%0d)", err ? "FAIL" : "PASS", err, n, "$M", $W);
    \$finish;
  end
endmodule
EOT
DEF=""; [ "$mode" = mut ] && DEF="-DOT_QKD_RLYS_MUT"
verilator --binary --timing -Wno-fatal -Wno-WIDTH $DEF --top-module tb -Mdir "$O/obj" -o tb \
  "$O/tb.sv" rtl/qwen_sys/kv_rly_std_20261016/qkd_rlys.sv > "$O/build.log" 2>&1 || { echo BUILD_FAILED; tail -5 "$O/build.log"; exit 2; }
"$O/obj/tb" | tee "$O/bench.log" | grep RLYS_BENCH
grep -q 'RLYS_BENCH PASS' "$O/bench.log"
