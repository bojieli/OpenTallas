#!/bin/bash
set -eu
cd /work
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
for mode in positive mutant; do
  f=primitive.sv
  [ "$mode" = positive ] || f=primitive_mut.sv
  set +e
  yosys -Q -T -p "read_verilog -sv $f miter.sv; hierarchy -top miter; setattr -mod -unset keep_hierarchy; flatten; opt_clean; select -module miter; sat -verify -prove eq 1 -show-inputs -show-outputs" > "$mode.log" 2>&1
  r=$?
  set -e
  echo "$r" > "$mode.rc"
  if [ "$mode" = positive ]; then
    [ "$r" = 0 ] && grep -q SUCCESS "$mode.log"
  else
    [ "$r" != 0 ] && grep -q 'proof did fail' "$mode.log"
  fi
done
printf 'LOCAL_POP_EXACT_PASS positive_rc=%s mutant_rc=%s\n' "$(cat positive.rc)" "$(cat mutant.rc)"
