#!/bin/bash
set -euo pipefail
O=${1:?fresh output root}
mkdir -p "$O"
for c in packed fp32 alias;do
 fp=1;mut=0;case "$c" in packed)fp=0;;alias)mut=4;;esac
 iverilog -g2012 -s tb_vm_reader_r2048 -Ptb_vm_reader_r2048.WFP32=$fp -Ptb_vm_reader_r2048.MUT=$mut -o "$O/$c.vvp" rtl/lib/ot_rst_relay.sv rtl/hbm_next/idx/ot_hnx_idx_vm_static_r2048.sv rtl/hbm_next/idx/ot_hnx_idx_vm_query_static_n12_r2048.sv tools/hbm_static/vm_r2048/reader_golden/*.sv tools/hbm_static/vm_r2048/tb_reader.sv >"$O/$c.build.log" 2>&1
 rc=0;vvp "$O/$c.vvp" >"$O/$c.log" 2>&1||rc=$?
 if [ "$c" = alias ];then test "$rc" != 0;grep -q FATAL "$O/$c.log";echo "READER_MUTANT_CAUGHT high_regular_bit";else test "$rc" = 0;grep 'VM_READER_R2048 PASS' "$O/$c.log";fi
done
verilator --lint-only --timing -Wno-fatal -Werror-WIDTH -Werror-SELRANGE --top-module ot_hnx_idx_vm_query_static_n12_r2048 rtl/lib/ot_rst_relay.sv rtl/hbm_next/idx/ot_hnx_idx_vm_static_r2048.sv rtl/hbm_next/idx/ot_hnx_idx_vm_query_static_n12_r2048.sv >"$O/lint.log" 2>&1
echo 'READER_WIDTH_SELRANGE_PASS'
