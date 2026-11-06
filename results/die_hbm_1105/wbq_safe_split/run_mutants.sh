#!/usr/bin/env bash
set -eu
R=$(realpath "${1:?repo}"); O=$(realpath -m "${2:?out}")
P=results/die_hbm_1105/wbq_safe_split
for m in bitflip overwrite; do
 SW_SRC=$P/mut_${m}.sv RUNS="$m:FAIL:" bash "$R/$P/run_eq.sh" "$R" "${O}_${m}"
done
