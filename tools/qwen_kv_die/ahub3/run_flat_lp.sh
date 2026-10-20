#!/bin/bash
# run_flat_lp.sh OUT (KV-AHUB3 10-19, FLEET only): lp.py lockstep bench (Verilator 5.050) + the fallback flat bench
# (FLAT=1) MUT 0 / 1 / 11 / 12 / 13 / 14 in parallel.  OUT/summary.txt; exit 0 iff MUT 0 PASS and every mutant FAILS.
set -u
O=$(realpath -m "$1"); mkdir -p "$O"
export VERILATOR=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
( SIM=verilator VL_JOBS=4 LP_ROOT=$PWD bash rtl/hdc/nearhbm/lp/qkd_ahub_static_dw_g2_lp_bench.sh "$O/lp" > "$O/lp_bench.log" 2>&1; echo "LP_BENCH rc=$?" >> "$O/lp_bench.log" ) &
echo 0 1 11 12 13 14 | tr ' ' '\n' | xargs -P 6 -I{} bash -c 'FLAT=1 bash tools/qwen_kv_die/ahub3/g2_bench.sh "'"$O"'/flat" {} > "'"$O"'/flat_m{}.out" 2>&1; echo "rc=$?" >> "'"$O"'/flat_m{}.out"'
wait
rc=0
{ grep -E "AUDIT|MUT [0-9]+:|BENCH_EXIT" "$O/lp_bench.log"; grep -q "BENCH_EXIT 0" "$O/lp_bench.log" || rc=1
  for m in 0 1 11 12 13 14; do
    v=$(grep -E "^AHUB_DW (PASS|FAIL)" "$O/flat_m$m.out" | tail -1); echo "FLAT MUT $m: ${v:-NO_VERDICT}"
    if [ $m = 0 ]; then case "$v" in "AHUB_DW PASS"*) ;; *) rc=1;; esac
    else case "$v" in "AHUB_DW FAIL"*) ;; *) rc=1;; esac; fi
  done; echo "RUN_FLAT_LP rc=$rc"; } > "$O/summary.txt"
cat "$O/summary.txt"; exit $rc
