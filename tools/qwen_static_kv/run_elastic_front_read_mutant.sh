#!/usr/bin/env bash
# Explicit negative physical-leaf bench: actual parent with front read-address mutant.
set -euo pipefail
out=${1:?fresh output directory}
PREP_ONLY=1 bash tools/qwen_static_kv/run_kv_hbm_elastic_boundary.sh "$out"
mapfile -t sources < <(rg --files "$out/source" -g '*.sv' | sort)
verilator --binary --timing -Wno-fatal -j "${JOBS:-2}" --top-module tb_kv_hbm_elastic_boundary -GFRONT_MUT=1 --Mdir "$out/obj_read_mutant" "${sources[@]}" > "$out/build_read_mutant.log" 2>&1
"$out/obj_read_mutant/Vtb_kv_hbm_elastic_boundary" +jit=16 +seed=2
