#!/bin/bash
set -eu
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
for m in 0 1 2;do
 verilator --binary --timing -Wno-fatal --top-module tb_reset -GMUT=$m --Mdir reset_build$m -j 4 rtl/lib/ot_rst_relay.sv rtl/lib/ot_rst_relay_bounded32.sv results/rtl/kv_qkh_nc_safe32_1020/tb_reset.sv >reset_build$m.log 2>&1
 set +e
 ./reset_build$m/Vtb_reset >reset_bench$m.log 2>&1
 rc=$?
 set -e
 if [ "$m" = 0 ];then grep '^BOUNDED_RESET PASS' reset_bench$m.log;test "$rc" = 0;else grep '^BOUNDED_RESET FAIL' reset_bench$m.log;test "$rc" != 0;fi
done
