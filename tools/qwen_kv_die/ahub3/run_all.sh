#!/bin/bash
# run_all.sh OUT (KV-AHUB3 10-19, FLEET only via ot-run): lp.py lockstep bench (Verilator 5.050, MUT 0/1/2/4 + region
# audits) and the die-calendar bench g2_bench.sh MUT 0..16 in parallel.  Writes OUT/summary.txt; exit 0 iff every
# expectation holds (MUT 0 PASS, every mutant FAIL).
set -u
O=$(realpath -m "$1"); mkdir -p "$O"
export VERILATOR=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$VERILATOR" --version > "$O/verilator_version.log"
( SIM=verilator VL_JOBS=4 LP_ROOT=$PWD bash rtl/hdc/nearhbm/lp/qkd_ahub_static_dw_g2_lp_bench.sh "$O/lp" > "$O/lp_bench.log" 2>&1; echo "LP_BENCH rc=$?" >> "$O/lp_bench.log" ) &
seq 0 16 | xargs -P 9 -I{} bash -c 'bash tools/qwen_kv_die/ahub3/g2_bench.sh "'"$O"'/g2" {} > "'"$O"'/g2_m{}.out" 2>&1; echo "rc=$?" >> "'"$O"'/g2_m{}.out"'
wait
rc=0
{ grep -E "AUDIT|MUT [0-9]+:|BENCH_EXIT" "$O/lp_bench.log"; grep -q "BENCH_EXIT 0" "$O/lp_bench.log" || rc=1
  for m in $(seq 0 16); do
    v=$(grep -E "^AHUB_DW (PASS|FAIL)" "$O/g2_m$m.out" | tail -1); echo "G2 MUT $m: ${v:-NO_VERDICT}"
    if [ $m = 0 ]; then case "$v" in "AHUB_DW PASS"*) ;; *) rc=1;; esac
    else case "$v" in "AHUB_DW FAIL"*) ;; *) rc=1;; esac; fi
  done; echo "RUN_ALL rc=$rc"; } > "$O/summary.txt"
cat "$O/summary.txt"; exit $rc
