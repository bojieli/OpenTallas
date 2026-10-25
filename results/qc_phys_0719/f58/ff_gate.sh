#!/bin/bash
# PATH-QC-RP1 f58 route gate (cqb COORD GEOM VERDICT): detailed route only if the FF hold estimate on the calibrated GRT RC
# (independent measure.tcl after the GRT-stage hold repair) is >= 0 at 0 endpoints AND the GRT-RC related-pair skew is <= 80 ps
# at TT and FF.  09:20 fix: parse the field after 'hold_wns' on the 'RP1_M FF setup_wns' line (measure.tcl now also prints a
# 'RP1_M FF vclk source latency := ...' line, which broke the old '^RP1_M FF' | $8 parse -> false CRASH), and enforce pairs.
f=/work/meas_route_FF.log
row=$(grep -h "^RP1_M FF setup_wns" $f | tail -1)
h=$(echo "$row" | awk '{for(i=1;i<NF;i++) if($i=="hold_wns") print $(i+1)}')
n=$(echo "$row" | awk '{for(i=1;i<NF;i++) if($i=="hold_ep") print $(i+1)}')
echo "RP1_GATE FF hold_wns(GRT cal) $h hold_ep $n"
[ -n "$h" ] && [ -n "$n" ] || { echo "RP1_GATE FAIL: no FF measurement"; exit 3; }
awk -v h="$h" -v n="$n" 'BEGIN{exit !(h>=0 && n==0)}' || { echo "RP1_GATE FAIL: FF hold $h ($n ep) -- stop before detailed route"; exit 3; }
for c in TT FF; do
  w=$(grep -h "^RP1_PAIR $c max" /work/meas_route_$c.log | tail -1 | awk '{for(i=1;i<NF;i++) if($i=="worst") print $(i+1)}')
  echo "RP1_GATE pair $c max worst $w"
  [ -n "$w" ] && awk -v w="$w" 'BEGIN{exit !(w<=80)}' || { echo "RP1_GATE FAIL: pair $c $w > 80 or missing"; exit 3; }
done
echo "RP1_GATE PASS"
