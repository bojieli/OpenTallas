#!/usr/bin/env bash
# S-NET: ot_s81_static_lane_end (static meso end) exact first epoch + every edge over phases x trunk delays; offset mutant
#   run_lane_end_gate.sh pass|mut OUT
set -eu
cd "$(dirname "$0")/../.."
mode=${1:?}; out=${2:?}; mkdir -p "$out"
src=(rtl/dsrom_sys/s81_die_bind/ot_s81_static_lane_cross.sv rtl/dsrom_sys/s81_static_net/ot_s81_static_lane_end.sv
     rtl/dsrom_sys/s81_static_net/test/tb_s81_static_lane_end.sv)
if [ "$mode" = pass ]; then
  for ph in 1 3 4 6 9; do for tr in 3 17; do
    iverilog -g2012 -s tb_s81_static_lane_end -Ptb_s81_static_lane_end.PHASE=$ph -Ptb_s81_static_lane_end.TRUNK=$tr -o "$out/sim" "${src[@]}"
    vvp -n "$out/sim" | grep "STATIC_LANE_END PASS" || { echo "STATIC_LANE_END_GATE FAIL phase $ph trunk $tr"; exit 1; }
  done; done; echo "STATIC_LANE_END_GATE PASS 10 phase/trunk runs exact"
else
  iverilog -g2012 -DOT_S81_STATIC_CROSS_MUT_OFFSET -s tb_s81_static_lane_end -o "$out/sim" "${src[@]}"
  if vvp -n "$out/sim" > "$out/mut.log" 2>&1 && grep -q "STATIC_LANE_END PASS" "$out/mut.log"; then echo "STATIC_LANE_END_GATE MUTANT ESCAPED"; exit 1; fi
  grep -m1 -E "wrong|mismatch|fault" "$out/mut.log"; echo "STATIC_LANE_END_GATE MUTANT REJECTED"
fi
