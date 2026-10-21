#!/usr/bin/env bash
set -euo pipefail
O=$(realpath -m "${1:?outdir}"); M=${2:-none}; S=${3:-1}; mkdir -p "$O"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
D=(); if [ "$M" != none ]; then D+=("+define+OT_S81SL_LEP_MUT_$M"); fi
mapfile -t SRCS < tools/s81_head/regional_reset_sources.f
for N in physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1 physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2; do SRCS+=("$N/$(basename "$N").v"); done
"$V" --version
"$V" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-lint -Wno-style "${D[@]}" -GSEED="$S" --top-module tb_s81sl_lepab_regional_r3r --Mdir "$O/obj" "${SRCS[@]}" rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_lepab_regional_r3r.sv --build-jobs "${J:-8}" -MAKEFLAGS 'OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0' > "$O/build.log" 2>&1 || { grep -m12 '%Error' "$O/build.log"; exit 3; }
"$O/obj/Vtb_s81sl_lepab_regional_r3r" > "$O/run.log" 2>&1
grep -E '^(PASS|FAIL|LANE|MISMATCH)' "$O/run.log" | head -15
grep -q '^PASS lepab_regional:' "$O/run.log"
