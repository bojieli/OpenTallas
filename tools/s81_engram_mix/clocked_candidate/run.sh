#!/usr/bin/env bash
set -euo pipefail
out=${1:?output directory required}
mkdir -p "$out"
sources=(tools/s81_engram_mix/clocked_candidate/tb.sv rtl/dsrom_sys/engram/mix/dsfd_engram_mix4_clocked_candidate.sv rtl/dsrom_sys/engram/mix/dsfd_engram_mix4_c.sv)
for mutant in 0 1; do
  iverilog -g2012 -s tb -Ptb.MUT="$mutant" -o "$out/m$mutant.vvp" "${sources[@]}"
  rc=0
  vvp "$out/m$mutant.vvp" > "$out/m$mutant.log" 2>&1 || rc=$?
  if [[ $mutant == 0 ]]; then
    [[ $rc == 0 ]]
    rg -q '^CLOCKED_RELAY_PASS checked=49092 depths=6 cycles=8192 resets=17$' "$out/m0.log"
  else
    [[ $rc != 0 ]]
    rg -q 'CLOCKED_RELAY_FAIL checked=49092 errors=8182 mutant=1' "$out/m1.log"
  fi
  cat "$out/m$mutant.log"
done
