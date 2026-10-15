#!/usr/bin/env bash
# S81 FILL 2026-10-15: exact bench of a GEN18r forwarded-clock die station dsfd_stn{h,v}_<W>x1: data captured on the
# FALLING edge of the forwarded clock fi0, fo0 = the kept forwarding inverter (~fi0).  DUT = the hardened RTL file
# (rtl/dsrom_sys/s81_station_native/gen18r/<master>.sv); mutants edit a copy:
#   clock_mutant  the stages capture on ~fi0 (wrong edge)      -> must FAIL
#   data_mutant   bit 0 of the first slice inverted            -> must FAIL
# usage: run_fwd_station_gate.sh pass|clock_mutant|data_mutant <master> <W> <outdir>
set -euo pipefail
mode=${1:?mode}; m=${2:?master}; w=${3:?width}; out=${4:?outdir}
root=$(cd "$(dirname "$0")/../.." && pwd)
mkdir -p "$out"; out=$(cd "$out" && pwd)
python3 - "$root" "$out" "$mode" "$m" <<'PYCODE'
from pathlib import Path
import re, sys
root, out, mode, m = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4]
s = (root / f'rtl/dsrom_sys/s81_station_native/gen18r/{m}.sv').read_text()
if mode == 'clock_mutant':
    n = s.count('.fclk_i(fi0[0])'); assert n >= 1; s = s.replace('.fclk_i(fi0[0])', '.fclk_i(~fi0[0])')
elif mode == 'data_mutant':
    k = re.search(r'\.i_d\(di0\[(\d+):0\]\)', s)
    assert k and s.count(k.group(0)) == 1
    hi = int(k.group(1)); s = s.replace(k.group(0), f".i_d(di0[{hi}:0] ^ {hi + 1}'d1)")
else:
    assert mode == 'pass'
(out / 'dut.sv').write_text(s)
PYCODE
cat > "$out/tb.sv" <<TB
\`timescale 1ns/1ps
module tb;
 localparam integer W = $w;
 reg fi = 0; always #5 fi = ~fi;
 reg [W-1:0] di = 0; wire [W-1:0] dq; wire fo;
 $m dut(.di0(di), .do0(dq), .fi0(fi), .fo0(fo));
 integer n, j; reg [31:0] rng = 32'h9e3779b9; reg [W-1:0] previous; reg valid = 0;
 initial begin
  for (n = 0; n < 20000; n = n + 1) begin
   @(posedge fi); #1;
   if (fo !== ~fi) begin \$display("STATION FAIL forwarded clock fo0 != ~fi0 n=%0d", n); \$fatal(1); end
   for (j = 0; j < W; j = j + 1) begin rng = rng ^ (rng << 13); rng = rng ^ (rng >> 17); rng = rng ^ (rng << 5); di[j] = rng[11]; end
   if (n < W) begin di = 0; di[n] = 1'b1; end
   else if (n < 2 * W) begin di = {W{1'b1}}; di[n - W] = 1'b0; end
   #1; if (valid && dq !== previous) begin \$display("STATION FAIL captured on the rising edge n=%0d", n); \$fatal(1); end
   @(negedge fi); #1;
   if (dq !== di) begin \$display("STATION FAIL payload n=%0d", n); \$fatal(1); end
   previous = di; valid = 1;
  end
  \$display("STATION PASS 20000 words %0d bits fwd_negedge", W); \$finish;
 end
endmodule
TB
verilator --binary --timing --top-module tb -Wno-fatal -Wno-lint -Wno-style -j 2 --Mdir "$out/obj" \
  "$root/rtl/common/ot_fwd_link_stage.sv" "$out/dut.sv" "$out/tb.sv" > "$out/build.log" 2>&1 || { tail -20 "$out/build.log"; exit 3; }
set +e
"$out/obj/Vtb" > "$out/sim.log" 2>&1
rc=$?
set -e
cat "$out/sim.log"
if [ "$mode" = pass ]; then
  [ "$rc" = 0 ] && grep -q "STATION PASS 20000 words $w bits fwd_negedge" "$out/sim.log"
else
  [ "$rc" != 0 ] && grep -q 'STATION FAIL' "$out/sim.log" && echo "STATION MUTANT REJECTED $mode"
fi
