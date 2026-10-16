#!/usr/bin/env bash
# Exact bench of the static SU pinned store bank leaf (6 real 128x256 SRAM models; read n -> n+2, write commit n+1).
# Usage: su_bank_run.sh OUT [coherence|return|clock_halt|rd_halt|ws_halt|reset]   (mutant: one replica misses writes / return one edge late -> FAIL)
set -euo pipefail
cd "$(dirname "$0")/../.."
out=$(realpath -m "$1"); mut=${2:-}
mc=0; mr=0; mz=0; [ "$mut" = coherence ] && mc=1; [ "$mut" = return ] && mr=1; [ "$mut" = reset ] && mz=1
mkdir -p "$out"
vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
S=rtl/hbm_accel/generic/adapters/static_su/data_store
"$vl" --binary --timing -O1 -j 2 -Wno-fatal -Wno-lint -Wno-style --top-module tb_hbm_su_static_pinned_bank \
 -GMUT_COHERENCE=$mc -GMUT_RETURN=$mr -GMUT_RESET=$mz --Mdir "$out/obj${mut:+_$mut}" $S/tb_hbm_su_static_pinned_bank.sv $S/ot_hbm_su_static_pinned_bank.sv $S/ot_hbm_su_static_bank6_clock_physical.sv \
 $S/ot_hbm_su_static_data_store.sv rtl/hbm_accel/generic/peers/ot_hgi_su_unit.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v > "$out/build${mut:+_$mut}.log" 2>&1
args=(); if [ "$mut" = clock_halt ]; then args+=(+MUT_CLOCK_HALT); fi; if [ "$mut" = rd_halt ]; then args+=(+MUT_RD_HALT); fi; if [ "$mut" = ws_halt ]; then args+=(+MUT_WS_HALT); fi
"$out/obj${mut:+_$mut}/Vtb_hbm_su_static_pinned_bank" "${args[@]}"
