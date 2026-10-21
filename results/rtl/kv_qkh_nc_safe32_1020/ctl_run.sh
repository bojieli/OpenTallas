#!/bin/bash
set -eu
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
for m in 0 1 2;do
 verilator --binary --timing -Wno-fatal --top-module tb_ctl -GMUT=$m --Mdir ctl_build$m -j 4 rtl/lib/ot_rst_relay.sv rtl/lib/ot_rst_relay_bounded32.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/nearhbm/ot_qkh_ctl_tree4.sv results/rtl/kv_qkh_nc_safe32_1020/tb_ctl.sv >ctl_build$m.log 2>&1
 set +e
 ./ctl_build$m/Vtb_ctl >ctl_bench$m.log 2>&1
 rc=$?
 set -e
 if [ "$m" = 0 ];then grep '^CTL_TREE4 PASS' ctl_bench$m.log;test "$rc" = 0;else grep '^CTL_TREE4 FAIL' ctl_bench$m.log;test "$rc" != 0;fi
done
