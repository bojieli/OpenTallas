#!/bin/bash
set -eu
R=/srv/opentallas-scratch/codex/kv-ahub6
B=/srv/opentallas-scratch/claude/ref_gate/qkd_ahub_g4a-20261019-215713/src
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
mkdir -p "$R/io_behavior_v3"
cp "$R/qkd_ahub6_controls.sv" "$R/io_behavior_v3/controls.sv"
"$V" --version
for m in 0 1;do
F="$R/io_behavior_v3/controls.sv"
if [ "$m" = 1 ];then sed 's/assign q=value;/assign q=(ID==5)?~value:value;/' "$F" > "$R/io_behavior_v3/mut.sv";F="$R/io_behavior_v3/mut.sv";fi
"$V" --binary --timing -O1 -Wno-fatal -Wno-lint -Wno-style --build-jobs 2 --top-module tb_io_copy --Mdir "$R/io_behavior_v3/obj$m" "$R/tb_io_copy.sv" "$B/rtl/hdc/nearhbm/qkd_ahub_static_dw_safe.sv" "$F" > "$R/io_behavior_v3/build$m.log" 2>&1
set +e
"$R/io_behavior_v3/obj$m/Vtb_io_copy" > "$R/io_behavior_v3/run$m.log" 2>&1
rc=$?
set -e
if [ "$m" = 0 ];then grep AHUB6_IO_PASS "$R/io_behavior_v3/run$m.log";test "$rc" = 0;else grep AHUB6_IO_FAIL "$R/io_behavior_v3/run$m.log";test "$rc" != 0;fi
done
echo AHUB6_IO_SUITE_PASS
