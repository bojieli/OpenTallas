#!/bin/bash
set -euo pipefail
O=$1
M=${2:-0}
mkdir -p "$O"
V=$HOME/.local/opentallas-tools/bin/verilator
"$V" --binary --timing --top-module tb_mif_group -GMUT=$M -Wno-fatal -j 8 --x-assign 0 --x-initial 0 \
 rtl/test/qwen_dv/s5/sram_models_nofatal.sv rtl/qwen_dv/s5/qfd_dv_s5_vm8x.sv rtl/qwen_dv/s5/qfd_dv_s5_vm8out.sv \
 rtl/qwen_dv/s5/s8/qfd_dv_s8_crh_rp1.sv rtl/qwen_dv/s5/s8/qfd_dv_s8_vm8q_rp1.sv tools/qwen_dv/mif1309/tb_mif_group.sv \
 -Mdir "$O/obj" > "$O/build.log" 2>&1
set +e
"$O/obj/Vtb_mif_group" > "$O/run.log" 2>&1
rc=$?
set -e
if [ "$M" = 0 ]; then test "$rc" = 0; else test "$rc" != 0; grep -q "MIF_GROUP FAIL" "$O/run.log"; fi
cat "$O/run.log"
