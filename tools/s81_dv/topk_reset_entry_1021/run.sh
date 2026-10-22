#!/usr/bin/env bash
set -euo pipefail
O=$(realpath -m "$1"); M=${2:-0}; mkdir -p "$O"
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
SRC=(rtl/dsrom_sys/s81_dv/idx/dsdv_bk_sel_vmtx_n32.sv rtl/dsrom_sys/s81_dv/idx/dsdv_idx_vmux_n32.sv rtl/lib/ot_rst_relay.sv physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v tools/s81_dv/topk_reset_entry_1021/tb_reset.sv)
sha256sum "${SRC[@]}" > "$O/sources.sha256"
"$VL" --version > "$O/verilator.version"
"$VL" --binary --timing -j "${J:-2}" -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -DRESET_MUT="$M" --top-module tb_topk_reset_entry "${SRC[@]}" --Mdir "$O/obj" > "$O/build.log" 2>&1
set +e
"$O/obj/Vtb_topk_reset_entry" > "$O/run.log" 2>&1
rc=$?
set -e
cat "$O/run.log"
exit "$rc"
