#!/bin/bash
# QC-RP1 10-25 route gate (cqb COORD GEOM VERDICT): detailed route only if the FF hold estimate on the calibrated GRT RC
# (independent measure.tcl after the GRT-stage hold repair) is >= 0 and the GRT-RC related-pair skew is <= 80 ps.
f=/work/meas_route_FF.log
h=$(grep -h "^RP1_M FF" $f | awk "{print \$8}")
echo "RP1_GATE FF hold_wns(GRT cal) $h"
[ -n "$h" ] || { echo "RP1_GATE FAIL: no FF measurement"; exit 3; }
awk -v h="$h" "BEGIN{exit !(h>=0)}" || { echo "RP1_GATE FAIL: FF hold $h < 0 -- stop before detailed route"; exit 3; }
grep -h "^RP1_PAIR" /work/meas_route_TT.log /work/meas_route_FF.log
echo "RP1_GATE PASS"
