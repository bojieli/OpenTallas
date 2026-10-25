#!/bin/bash
set -euo pipefail
O=$1;mkdir -p "$O"
$HOME/.local/opentallas-tools/bin/verilator --binary --timing -j 8 -Wno-fatal -Wno-lint --x-assign 0 --x-initial 0 --top-module tb_mif_fetch \
rtl/test/qwen_dv/s5/sram_models_nofatal.sv rtl/qwen_dv/s5/qfd_dv_s5_vm8x.sv rtl/qwen_dv/s5/qfd_dv_s5_vm8out.sv \
rtl/qwen_dv/s5/s8/qfd_dv_s8_crh_rp1.sv rtl/qwen_dv/s5/s8/qfd_dv_s8_vm8q_rp1.sv rtl/qwen_dv/s5/s8/qfd_dv_s8_suvm_rp1.sv \
rtl/qwen_dv/s5/qfd_dv_s5_su8.sv rtl/qwen_dv/s5/qfd_dv_s5_su8_rst3.sv tools/qwen_dv/mif1309/tb_mif_fetch.sv \
-Mdir "$O/obj" >"$O/build.log" 2>&1
"$O/obj/Vtb_mif_fetch" >"$O/run.log" 2>&1
cat "$O/run.log"
grep -q 'MIF_FETCH PASS' "$O/run.log"
