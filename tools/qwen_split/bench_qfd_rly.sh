#!/bin/bash
# Q-ELEM-CMP: bit-exact bench of a generated Qwen die data relay qfd_rly_<W>_* (Verilator 5.050).
# usage: bench_qfd_rly.sh <pass|mut> <master> <W> <rtl file> <work dir>
# pass: 20,000 random words, b must equal the previous edge's a on every edge (one register stage, no reset).
# mut : the same bench on a mutant copy of the master built in the work dir (bit 0 inverted in the register) -- must FAIL.
set -u
mode=$1; M=$2; W=$3; SRC=$4; O=$5
cd "$(dirname "$0")/../.."; mkdir -p "$O"
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
DUT="$SRC"
if [ "$mode" = mut ]; then DUT="$O/mut.sv"; sed 's/b <= a;/b <= a ^ 1;/' "$SRC" > "$DUT"; cmp -s "$SRC" "$DUT" && { echo MUTANT_NOT_APPLIED; exit 3; }; fi
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
      for (int i = 0; i < $W; i++) a[i] = \$urandom;
      @(posedge ck); ex = a;
    end
    \$display("QRLY_BENCH %s %0d errors in %0d words (%s W=%0d)", err ? "FAIL" : "PASS", err, n, "$M", $W);
    \$finish;
  end
endmodule
EOT
verilator --binary --timing -Wno-fatal -Wno-WIDTH --top-module tb -Mdir "$O/obj" -o tb "$O/tb.sv" "$DUT" > "$O/build.log" 2>&1 || { echo BUILD_FAILED; tail -5 "$O/build.log"; exit 2; }
"$O/obj/tb" | tee "$O/bench.log" | grep QRLY_BENCH
grep -q 'QRLY_BENCH PASS' "$O/bench.log"
