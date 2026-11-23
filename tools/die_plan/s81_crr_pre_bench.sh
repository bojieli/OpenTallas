#!/bin/bash
# S81-CRR-PRE bench: ot_s81sl_crr after the overlay, PRE 0 (define off) = d delayed 1 edge, PRE 2 (OT_S81SL_CRR_PRE2) = 3
# edges, lock-step vs reference shift registers on random d; a mutant (PRE 2 compared at 2 edges) must FAIL.
#   bash tools/die_plan/s81_crr_pre_bench.sh SLICE_SV [WORKDIR]     (SLICE_SV: an event-tree ot_s81sl_slice.sv)
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd); SRC=${1:?slice.sv}; W=${2:-$(mktemp -d)}; mkdir -p "$W"
awk '/^\(\* keep_hierarchy, keep \*\)$/{k=NR} /^module ot_s81sl_crr /{p=1} p{print} p&&/^endmodule/{exit}' "$SRC" > "$W/crr.sv"
grep -q "module ot_s81sl_crr" "$W/crr.sv"
python3 -I "$ROOT/tools/die_plan/s81_crr_pre_overlay.py" "$W/crr.sv" >/dev/null
for D in "" "-DOT_S81SL_CRR_PRE2"; do
  N=$([ -n "$D" ] && echo 3 || echo 1)
  cat > "$W/tb.sv" <<TB
\`timescale 1ns/1ps
module tb; reg clk = 0, d = 0; wire q; reg [7:0] h = 0; integer i, bad = 0, badm = 0;
  ot_s81sl_crr u (.clk(clk), .d(d), .q(q));
  always #1 clk = ~clk;
  always @(posedge clk) h <= {h[6:0], d};
  initial begin
    for (i = 0; i < 3000; i = i + 1) begin @(negedge clk); if (i > 8) begin if (q !== h[$N-1]) bad = bad + 1; if (q !== h[(($N == 1) ? 1 : $N-2)]) badm = badm + 1; end d = \$urandom; end
    \$display("CRR_BENCH edges=$N mismatch=%0d mutant_mismatch=%0d", bad, badm); \$finish;
  end
endmodule
TB
  iverilog -g2012 $D -o "$W/sim$N" "$W/tb.sv" "$W/crr.sv"
  vvp -n "$W/sim$N" | grep CRR_BENCH | tee -a "$W/bench.log"
done
awk '/CRR_BENCH/{split($3,a,"=");split($4,b,"="); if (a[2]!=0 || b[2]==0) f=1} END{print f?"CRR_BENCH FAIL":"CRR_BENCH PASS"; exit f}' "$W/bench.log"
