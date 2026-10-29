#!/bin/bash
set -euo pipefail
O=${1:?fresh output root}
mkdir -p "$O"
for c in positive zeroextend reverse_alias;do
 mut=0;case "$c" in zeroextend)mut=1;;reverse_alias)mut=2;;esac
 iverilog -g2012 -s tb_vm_r2048_fields -Ptb_vm_r2048_fields.MUT=$mut -o "$O/$c.vvp" rtl/hbm_accel/generic/vm/static/faces_q0_r2048/ot_vms_legacy_r2048_fields.sv tools/hbm_static/vm_r2048/tb_fields.sv >"$O/$c.build.log" 2>&1
 rc=0;vvp "$O/$c.vvp" >"$O/$c.log" 2>&1||rc=$?
 if [ "$c" = positive ];then test "$rc" = 0;grep 'VM_FIELDS_R2048 PASS' "$O/$c.log";else test "$rc" != 0;grep -q FATAL "$O/$c.log";echo "FIELDS_MUTANT_CAUGHT $c";fi
done
verilator --lint-only --timing -Wno-fatal -Werror-WIDTH -Werror-SELRANGE --top-module ot_vms_legacy_r2048_fields rtl/hbm_accel/generic/vm/static/faces_q0_r2048/ot_vms_legacy_r2048_fields.sv >"$O/lint.log" 2>&1
echo 'FIELDS_WIDTH_SELRANGE_PASS'
