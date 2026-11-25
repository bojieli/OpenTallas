#!/bin/bash
# QC-RC97-BT2 11-24: rc97 registered-read btab bench (pass: safe_r == safe delayed 1; nodelay: must FAIL).
set -euo pipefail
O=$1; mkdir -p "$O"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --version > "$O/verilator.version"
for kind in pass nodelay;do
 D=(-DOT_BTAB_S4R); [ "$kind" = pass ] || D+=(-DTB_NO_DELAY)
 "$V" --binary -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style "${D[@]}" --top-module tb_btab_safe_r rtl/qwen_dv/s5/qfd_dv_s5_btab_safe.sv rtl/qwen_dv/s5/qfd_dv_s5_btab_s4.sv rtl/test/qwen_dv/s5/tb_btab_safe_r.sv rtl/test/full_sm_service/sram_models.sv -Mdir "$O/obj_$kind" > "$O/build_$kind.log" 2>&1
 set +e; "$O/obj_$kind/Vtb_btab_safe_r" > "$O/run_$kind.log" 2>&1; rc=$?; set -e
 echo "$kind exit=$rc"; cat "$O/run_$kind.log" | head -n 3
 if [ "$kind" = pass ];then grep -q 'BTABR_EQ PASS' "$O/run_$kind.log";else grep -q 'BTABR_EQ FAIL' "$O/run_$kind.log";test "$rc" -ne 0;fi
done
echo BTABR_BENCH_OK
