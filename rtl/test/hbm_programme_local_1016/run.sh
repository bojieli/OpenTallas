#!/usr/bin/env bash
set -euo pipefail
src=${1:?source snapshot}
cand=${2:?candidate source directory}
out=${3:?output directory}
prod=${4:-0}
rows=282; [[ "$prod" == 0 ]] || rows=7137
mkdir -p "$out"
for mut in 0 1 2 4; do
  iverilog -g2012 -s tb_programme_local -Ptb_programme_local.MUT="$mut" -Ptb_programme_local.PRODUCTION="$prod" -o "$out/m$mut.vvp" \
    "$src/physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v" \
    "$src/rtl/hbm_accel/generic/adapters/static_su/programme/ot_hbm_su_programme.sv" \
    "$cand/ot_hbm_su_programme_local.sv" "$cand/tb.sv" > "$out/m$mut.compile.log" 2>&1
  set +e
  vvp "$out/m$mut.vvp" > "$out/m$mut.log" 2>&1
  rc=$?
  set -e
  if [[ "$mut" == 0 ]]; then
    [[ "$rc" == 0 ]] && grep -q "^PROGRAMME_LOCAL_PASS rows=$rows runs=3 extra_edges=2 II=1" "$out/m0.log" || { cat "$out/m0.log"; exit 1; }
  else
    [[ "$rc" != 0 ]] && grep -q 'local mismatch\|local nonzero\|missing completion' "$out/m$mut.log" || { cat "$out/m$mut.log"; exit 1; }
  fi
  printf 'PROGRAMME_LOCAL_MUT_%s rc=%s\n' "$mut" "$rc"
done
