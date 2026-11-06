#!/usr/bin/env bash
set -euo pipefail
mkdir -p logs
for mut in 0 1 2 3; do
  iverilog -g2012 -s tb_skid_head -Ptb_skid_head.MUT="$mut" -o "sim$mut" ot_svgr_rf1_skid_head.sv tb_skid_head.sv >"logs/build$mut.log" 2>&1
  if [[ "$mut" == 0 ]]; then
    /usr/bin/time -v vvp "sim$mut" >logs/positive.log 2>logs/positive.time
    grep 'SKID_HEAD PASS' logs/positive.log
  else
    if vvp "sim$mut" >"logs/mut$mut.log" 2>&1; then echo "MUTANT $mut SURVIVED"; exit 1; fi
    grep 'SKID_HEAD FAIL' "logs/mut$mut.log"
    echo "MUTANT $mut CAUGHT"
  fi
done
