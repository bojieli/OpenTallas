#!/bin/bash
set -u
mkdir -p logs_controls
sha256sum original.sv tb.sv mutant_*.sv run_controls.sh > logs_controls/inputs.sha256
for name in sticky_accept head_cause begin_active image_active reset_fault early_valid; do
  iverilog -g2012 -s tb -o control_sim original.sv "mutant_${name}.sv" tb.sv > "logs_controls/${name}.build.log" 2>&1 || exit $?
  vvp control_sim > "logs_controls/${name}.log" 2>&1
  rc=$?; echo "$rc" > "logs_controls/${name}.rc"
  if [ "$rc" -eq 0 ]; then echo "HOLLOW_CONTROL $name"; exit 3; fi
  if ! grep -q DUT_MISMATCH "logs_controls/${name}.log"; then echo "NO_DUT_WITNESS $name"; exit 4; fi
  head -1 "logs_controls/${name}.log"
done
