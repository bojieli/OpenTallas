#!/bin/bash
set -euo pipefail
ROOT=$(git rev-parse --show-toplevel);HERE=$ROOT/results/hbm_fused_boot_1351_1027;OUT=${1:?out}
mkdir -p "$OUT/source";cp "$HERE/tb_status_endpoint.sv" "$HERE/actual_post_jobs.mem" "$ROOT/rtl/hbm_next/fused/ot_hnx_fused_job217_provider.sv" "$ROOT/results/hbm_fused_provider_1027/sram256.v" "$OUT/source/"
cd "$OUT/source";export PATH=$HOME/.local/opentallas-tools/bin:$PATH
verilator --binary --timing -O1 -j 1 -Wno-fatal --top-module tb_status_endpoint -Mdir "$OUT/obj" -o native tb_status_endpoint.sv ot_hnx_fused_job217_provider.sv sram256.v > "$OUT/build.log" 2>&1
"$OUT/obj/native" > "$OUT/positive.log" 2>&1;cat "$OUT/positive.log"
if "$OUT/obj/native" +MUT_OLD_STATUS1 > "$OUT/old_status1.log" 2>&1;then echo OLD_STATUS1_ESCAPED;exit 1;else echo OLD_STATUS1_CAUGHT;fi
