#!/bin/bash
set -euo pipefail
O=$1;M=${2:-0};mkdir -p "$O"
P=rtl/qwen_dv/s5/s8/qfd_dv_s8_suvm_rp1.sv
if [ "$M" != 0 ]; then sed 's/\.start(wf_st\[2+MIF\])/\.start(wf_st[2])/' "$P" > "$O/parent_mutant.sv";P=$O/parent_mutant.sv;fi
$HOME/.local/opentallas-tools/bin/verilator --binary --timing -j 8 -Wno-fatal -Wno-lint --x-assign 0 --x-initial 0 --top-module tb_mif_fetch \
rtl/test/qwen_dv/s5/sram_models_nofatal.sv rtl/qwen_dv/s5/qfd_dv_s5_vm8x.sv rtl/qwen_dv/s5/qfd_dv_s5_vm8out.sv \
rtl/qwen_dv/s5/s8/qfd_dv_s8_crh_rp1.sv rtl/qwen_dv/s5/s8/qfd_dv_s8_vm8q_rp1.sv "$P" \
rtl/qwen_dv/s5/qfd_dv_s5_su8.sv rtl/qwen_dv/s5/qfd_dv_s5_su8_rst3.sv tools/qwen_dv/mif1309/tb_mif_fetch.sv \
-Mdir "$O/obj" >"$O/build.log" 2>&1
set +e
"$O/obj/Vtb_mif_fetch" >"$O/run.log" 2>&1
rc=$?
set -e
if [ "$M" = 0 ];then test "$rc" = 0;else test "$rc" != 0;grep -q 'MIF_FETCH FAIL' "$O/run.log";fi
cat "$O/run.log"
if [ "$M" = 0 ];then grep -q 'MIF_FETCH PASS' "$O/run.log";fi
