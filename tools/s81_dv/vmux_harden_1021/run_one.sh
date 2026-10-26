#!/usr/bin/env bash
set -euo pipefail
O=$(realpath -m "$1"); M=${2:-0}; mkdir -p "$O"
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$VL" --binary --timing -j "${J:-4}" -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -DVM_MUT="$M" -DDL_MUT=0 --top-module tb_dsdv_idx_vmux_n32 physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v rtl/dsrom_sys/s81_dv/idx/dsdv_idx_tree.sv rtl/dsrom_sys/s81_dv/idx/dsdv_idx_vmux_n32.sv rtl/dsrom_sys/s81_dv/idx/test/tb_dsdv_idx_vmux_n32.sv -Mdir "$O/obj" > "$O/build.log" 2>&1
"$O/obj/Vtb_dsdv_idx_vmux_n32" +SEED=7 > "$O/run.log" 2>&1
cat "$O/run.log"
grep -q 'VMUX_N32 PASS nerr 0' "$O/run.log"
