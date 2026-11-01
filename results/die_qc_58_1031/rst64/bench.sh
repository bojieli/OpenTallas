#!/bin/bash
# QC die reset contract bench (DIE-QC-58).  cells.sv = the reset cells extracted verbatim from tools/die_plan/gen_rtl.py.
#   bash results/die_qc_58_1031/rst64/bench.sh   (from the repo root; needs iverilog)  -> receipt on stdout
set -eu
D=results/die_qc_58_1031/rst64
python3 -I - tools/die_plan/gen_rtl.py "$D/cells.sv" <<'PY'
import re, sys
t = open(sys.argv[1]).read()
out = []
for m in ("ot_dp_rsync_s2", "ot_dp_rrelay", "ot_dp_rrelay_drive", "ot_dp_rgate"):
    x = re.search(r"\(\* keep_hierarchy(?:, keep)? \*\)\nmodule " + m + r" \(.*?\nendmodule\n", t, re.S)
    assert x, m
    out.append(x.group(0))
open(sys.argv[2], "w").write("`timescale 1ns/1fs\n" + "".join(out))
PY
T=$(mktemp -d)
echo "QC die reset contract receipt (DIE-QC-58, $(date '+%Y-%m-%d %H:%M %Z'), $(hostname), $(iverilog -V 2>/dev/null | head -1))"
echo "bench: iverilog -g2012 -P tb.HOLD=H -o rH tb64.sv cells.sv; vvp -n rH   (cells = ot_dp_rsync_s2 + ot_dp_rrelay + ot_dp_rrelay_drive + ot_dp_rgate extracted from tools/die_plan/gen_rtl.py)"
sha256sum "$D/tb64.sv" "$D/cells.sv" "$D/bench.sh" tools/die_plan/gen_rtl.py
echo "contract: COORD DIE-QC-58 10-31 (12.28b default, S81/HBM/KV form): boot holds the QC die rst_n low >= 64 clocks with the clock running"
for H in 64 63 61; do
  iverilog -g2012 -P tb.HOLD=$H -o $T/r$H $D/tb64.sv $D/cells.sv
  case $H in 64) echo "--- HOLD=64 (contract)";; 63) echo "--- HOLD=63";; 61) echo "--- HOLD=61 (mutant control)";; esac
  vvp -n $T/r$H | grep -v '^VCD\|finish' | tee $T/o$H
done
V=PASS; grep -q BELOW64 $T/o64 && V=FAIL
M=MISSED; grep -q BELOW64 $T/o61 && M=CAUGHT
echo "VERDICT: contract HOLD=64 $V (min known-low sink edges $(grep -o "min_sink_known_low=[0-9]*" $T/o64 | awk -F= "NR==1||\$2<m{m=\$2} END{print m}")); mutant HOLD=61 $M"
rm -rf $T
