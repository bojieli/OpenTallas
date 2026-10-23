#!/usr/bin/env bash
# STW-S81c-TOK4-BAND 10-22: split X band lockstep (tb_dsdv_idx_rg3_bx_lsw).  usage: run_rg3_bx_lsw.sh WORKDIR [N] [MUTN]
# Prints BX_LSW PASS (MUTN 0) or BX_LSW MUTANT_CAUGHT (MUTN != 0) last; anything else is a failure.
set -u
I=$(cd "$(dirname "$0")/.." && pwd); R=$(cd "$I/../../../.." && pwd)
D=$(mkdir -p "$1" && cd "$1" && pwd); N=${2:-20000}; M=${3:-0}
VL=${VERILATOR:-verilator}
"$VL" --binary -j "${VL_J:-4}" -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-TIMESCALEMOD --top-module tb_dsdv_idx_rg3_bx_lsw \
    -GN=$N -GMUTN=$M --Mdir "$D/obj$M" "$R/rtl/lib/ot_rst_relay.sv" "$I/dsdv_idx_rg2.sv" \
    "$R/physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v" \
    "$I/dsdv_idx_rg3_band.sv" "$I/test/dsdv_idx_rg3_bx_ref.sv" "$I/test/tb_dsdv_idx_rg3_bx_lsw.sv" > "$D/build$M.log" 2>&1 \
    || { tail -20 "$D/build$M.log"; echo "BX_LSW ERROR build"; exit 2; }
"$D/obj$M/Vtb_dsdv_idx_rg3_bx_lsw" +SEED=${SEED:-7}
