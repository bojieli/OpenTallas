#!/bin/bash
# QC-STA-BTLAT3 11-25: request-leg register btab bench (pass: s4 RQ+S4R == safe delayed 2; one-delay: must FAIL).
set -euo pipefail
O=$1; mkdir -p "$O"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --version > "$O/verilator.version"
for kind in pass onedelay;do
 D=(-DOT_BTAB_S4R -DOT_BTAB_RQ); [ "$kind" = pass ] || D+=(-DTB_ONE_DELAY)
 "$V" --binary -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style "${D[@]}" --top-module tb_btab_rq rtl/qwen_dv/s5/qfd_dv_s5_btab_safe.sv rtl/qwen_dv/s5/qfd_dv_s5_btab_s4.sv rtl/test/qwen_dv/s5/tb_btab_rq.sv rtl/test/full_sm_service/sram_models.sv -Mdir "$O/obj_$kind" > "$O/build_$kind.log" 2>&1
 set +e; "$O/obj_$kind/Vtb_btab_rq" > "$O/run_$kind.log" 2>&1; rc=$?; set -e
 echo "$kind exit=$rc"; head -n 3 "$O/run_$kind.log"
 if [ "$kind" = pass ];then grep -q 'BTABRQ_EQ PASS' "$O/run_$kind.log";else grep -q 'BTABRQ_EQ FAIL' "$O/run_$kind.log";test "$rc" -ne 0;fi
done
echo BTABRQ_BENCH_OK
