#!/bin/bash
set -eu
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
for m in 0 3;do
 verilator --binary --timing -Wno-fatal --top-module tb -GMUT=$m --Mdir off_build$m -j 4 results/rtl/kv_hroot_safe32_1020/tb_offphase.sv results/rtl/kv_hroot_safe32_1020/reference.sv rtl/qwen_sys/static_kv_die_20261017/qkd_kv_hroot_safe32.sv >off_build$m.log 2>&1
 set +e
 ./off_build$m/Vtb >off_bench$m.log 2>&1
 rc=$?
 set -e
 cat off_bench$m.log
 if [ "$m" = 0 ];then grep '^SAFE32 PASS' off_bench$m.log;test "$rc" = 0;else grep '^SAFE32 FAIL' off_bench$m.log;test "$rc" != 0;fi
done
