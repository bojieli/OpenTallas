#!/usr/bin/env bash
# S81 FILL 2026-10-15: exact bench of a GEN18r common-clock die station dsfd_hstn{h,v}_<W> (generalises Codex's
# run_gate.sh / tb_hstnh_1024.sv of 7110ec4a7 to every width).  The DUT is the hardened RTL file itself
# (rtl/dsrom_sys/s81_station_native/gen18r/<master>.sv); mutants edit a copy:
#   clock_mutant  the kept INV input becomes ~ck  (captures on the wrong edge)  -> must FAIL
#   (append _raw to a mutant mode: the script exits with the mutant run status, for expect=fail)
#   data_mutant   bit 0 of the first stage slice inverted                       -> must FAIL
# usage: run_station_gate.sh pass|clock_mutant|data_mutant <master> <W> <outdir>
set -euo pipefail
mode=${1:?mode}; m=${2:?master}; w=${3:?width}; out=${4:?outdir}
raw=0; case $mode in *_raw) raw=1; mode=${mode%_raw};; esac   # *_raw: exit with the mutant sim status (loop expect=fail)
root=$(cd "$(dirname "$0")/../.." && pwd)
mkdir -p "$out"; out=$(cd "$out" && pwd)
python3 - "$root" "$out" "$mode" "$m" <<'PYCODE'
from pathlib import Path
import re, sys
root, out, mode, m = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4]
s = (root / f'rtl/dsrom_sys/s81_station_native/gen18r/{m}.sv').read_text()
posedge = 'always @(posedge ck[0]) q <= di;' in s      # --hstn-posedge form (plain flops); else INV + negedge stage
if mode == 'clock_mutant' and posedge:
    s = s.replace('always @(posedge ck[0]) q <= di;', 'always @(negedge ck[0]) q <= di;')
elif mode == 'data_mutant' and posedge:
    w = int(re.search(r'reg \[(\d+):0\] q;', s).group(1)) + 1
    s = s.replace('q <= di;', f"q <= di ^ {w}'d1;")
elif mode == 'clock_mutant':
    assert s.count('.a(ck[0])') == 1; s = s.replace('.a(ck[0])', '.a(~ck[0])')
elif mode == 'data_mutant':
    k = re.search(r'\.i_d\(di\[(\d+):0\]\)', s)
    assert k and s.count(k.group(0)) == 1
    hi = int(k.group(1)); s = s.replace(k.group(0), f".i_d(di[{hi}:0] ^ {hi + 1}'d1)")
else:
    assert mode == 'pass'
(out / 'dut.sv').write_text(s)
PYCODE
cat > "$out/tb.sv" <<TB
\`timescale 1ns/1ps
module tb;
 localparam integer W = $w;
 reg ck = 0; always #5 ck = ~ck;
 reg [W-1:0] di = 0; wire [W-1:0] dq;
 $m dut(.ck(ck), .di(di), .dq(dq));
 integer n, j; reg [31:0] rng = 32'h12345678; reg [W-1:0] previous; reg valid = 0;
 initial begin
  for (n = 0; n < 20000; n = n + 1) begin
   @(negedge ck); #1;
   for (j = 0; j < W; j = j + 1) begin rng = rng ^ (rng << 13); rng = rng ^ (rng >> 17); rng = rng ^ (rng << 5); di[j] = rng[7]; end
   if (n < W) begin di = 0; di[n] = 1'b1; end
   else if (n < 2 * W) begin di = {W{1'b1}}; di[n - W] = 1'b0; end
   #1; if (valid && dq !== previous) begin \$display("STATION FAIL captured wrong clock edge n=%0d", n); \$fatal(1); end
   @(posedge ck); #1;
   if (dq !== di) begin \$display("STATION FAIL payload n=%0d", n); \$fatal(1); end
   previous = di; valid = 1;
  end
  \$display("STATION PASS 20000 words %0d bits top_posedge", W); \$finish;
 end
endmodule
TB
verilator --binary --timing --top-module tb -Wno-fatal -Wno-lint -Wno-style -j 2 --Mdir "$out/obj" \
  "$root/rtl/common/ot_fwd_link_stage.sv" "$out/dut.sv" "$out/tb.sv" > "$out/build.log" 2>&1 || { tail -20 "$out/build.log"; exit 3; }
# harness guard (hstnv_1029-f8 18:5x: "Vtb: Permission denied", rc 126 read as a mutant result): the simulator must be an
# executable file before it runs; rebuild once, else exit 3 (harness error, never a bench verdict)
if [ ! -x "$out/obj/Vtb" ]; then
  echo "HARNESS: $out/obj/Vtb not executable after build; rebuilding once" >&2
  rm -rf "$out/obj"
  verilator --binary --timing --top-module tb -Wno-fatal -Wno-lint -Wno-style -j 2 --Mdir "$out/obj" \
    "$root/rtl/common/ot_fwd_link_stage.sv" "$out/dut.sv" "$out/tb.sv" > "$out/build2.log" 2>&1 || { tail -20 "$out/build2.log"; exit 3; }
  [ -x "$out/obj/Vtb" ] || { echo "HARNESS: $out/obj/Vtb still not executable" >&2; exit 3; }
fi
set +e
"$out/obj/Vtb" > "$out/sim.log" 2>&1
rc=$?
set -e
cat "$out/sim.log"
[ "$raw" = 1 ] && exit "$rc"
if [ "$mode" = pass ]; then
  [ "$rc" = 0 ] && grep -q "STATION PASS 20000 words $w bits top_posedge" "$out/sim.log"
else
  [ "$rc" != 0 ] && grep -q 'STATION FAIL' "$out/sim.log" && echo "STATION MUTANT REJECTED $mode"
fi
