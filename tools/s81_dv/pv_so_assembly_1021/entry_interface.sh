#!/usr/bin/env bash
set -euo pipefail
out=${1:?out};mkdir -p "$out"
D=rtl/dsrom_sys/s81_dv/pv_so
"$HOME/.local/opentallas-tools/bin/verilator" --lint-only --timing -Wno-fatal -Werror-SELRANGE -Werror-PINMISSING -Werror-PINCONNECTEMPTY -Werror-WIDTH \
 -DOT_SVC_H8 --top-module dsdv_svc_rs_pvso_entry -GH=8 -GPVSO_ENABLE=1 \
 tools/s81_dv/pv_so_assembly_1021/entry_interface_only.sv \
 "$D/dsdv_pv_so_program.sv" "$D/dsdv_pv_so_program_h8.sv" "$D/dsdv_pv_half_join.sv" "$D/dsdv_pv_half_join_h8.sv" \
 "$D/dsdv_pv_so_ingress.sv" "$D/dsdv_pv_so_ingress_h8.sv" "$D/dsdv_svc_rs_pvso_entry.sv" \
 physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1.v > "$out/lint.log" 2>&1
printf '%s\n' 'H8_ENTRY_INTERFACE_PASS explicitSVCtestdouble,actualPVSOmodules,SizedPins,WIDTH,SELRANGE;notarithmetic'
