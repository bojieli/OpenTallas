#!/usr/bin/env bash
set -euo pipefail
R=$(pwd);mkdir -p bench;cd src
J=8 bash tools/s81_slice/xgtxo_bench.sh "$R/bench/xgtxo" > "$R/bench/xgtxo.log" 2>&1
for m in base bank off qswap wcopy tpar exp; do
 args=(); [ "$m" = base ] || args=("$m")
 J=8 bash tools/s81_slice/xs4_equiv.sh "$R/bench/xs4_$m" "${args[@]}" > "$R/bench/xs4_$m.log" 2>&1
done
printf 'EXISTING_MECHANISMS_PASS\n'
