#!/bin/bash
set -eu
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
verilator --version
for m in 0 1 2 3; do
 verilator --binary --timing -Wno-fatal --top-module tb -GMUT=$m --Mdir v3_build$m -j 4 results/rtl/kv_hroot_safe32_1020/tb.sv results/rtl/kv_hroot_safe32_1020/reference.sv rtl/qwen_sys/static_kv_die_20261017/qkd_kv_hroot_safe32.sv >v3_build$m.log 2>&1
 set +e
 ./v3_build$m/Vtb >v3_bench$m.log 2>&1
 rc=$?
 set -e
 if [ "$m" = 0 ]; then grep '^SAFE32 PASS' v3_bench$m.log; test "$rc" = 0; else grep '^SAFE32 FAIL' v3_bench$m.log; test "$rc" != 0; fi
done
yosys -Q -s results/rtl/kv_hroot_safe32_1020/synth.ys >v3_synth.log 2>&1
