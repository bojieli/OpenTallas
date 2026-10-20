#!/bin/bash
set -eu
R=/srv/opentallas-scratch/codex/kv-ahub6
B=/srv/opentallas-scratch/claude/ref_gate/qkd_ahub_g4a-20261019-215713/src
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
mkdir -p "$R/core_behavior_v7prod"
cp "$R/qkd_ahub6_controls_v7.sv" "$R/core_behavior_v7prod/controls.sv"
"$V" --version
for m in 0 1 2;do
F="$R/core_behavior_v7prod/controls.sv"
if [ "$m" = 1 ];then sed 's/assign q=value;/assign q=(ID==130)?~value:value;/' "$B/rtl/lib/ot_rst_pipe.sv" "$B/rtl/hdc/ot_hdc_delay.sv" "$B/rtl/common/landed_parent/ot_pl_land.sv" "$B/rtl/common/landed_parent/ot_pl_land_field_copies.sv" "$F" > "$R/core_behavior_v7prod/mut.sv";F="$R/core_behavior_v7prod/mut.sv";fi
if [ "$m" = 2 ];then sed 's/\.d(s1)/.d(d)/' "$R/core_behavior_v7prod/controls.sv" > "$R/core_behavior_v7prod/mut_reset.sv";F="$R/core_behavior_v7prod/mut_reset.sv";fi
"$V" --binary --timing -O1 -Wno-fatal -Wno-lint -Wno-style --build-jobs 2 --top-module tb_core_copy --Mdir "$R/core_behavior_v7prod/obj$m" "$R/tb_core_copy_production.sv" "$B/rtl/hdc/nearhbm/qkd_ahub_static_dw_safe.sv" "$B/rtl/lib/ot_rst_pipe.sv" "$B/rtl/hdc/ot_hdc_delay.sv" "$B/rtl/common/landed_parent/ot_pl_land.sv" "$B/rtl/common/landed_parent/ot_pl_land_field_copies.sv" "$F" > "$R/core_behavior_v7prod/build$m.log" 2>&1
set +e
"$R/core_behavior_v7prod/obj$m/Vtb_core_copy" > "$R/core_behavior_v7prod/run$m.log" 2>&1
rc=$?
set -e
if [ "$m" = 0 ];then grep AHUB6_CORE_PASS "$R/core_behavior_v7prod/run$m.log";test "$rc" = 0;else grep AHUB6_CORE_FAIL "$R/core_behavior_v7prod/run$m.log";test "$rc" != 0;fi
done
echo AHUB6_CORE_SUITE_PASS
