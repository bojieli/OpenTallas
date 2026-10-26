#!/bin/bash
set -euo pipefail
work=$1; syn=${2:-0};mut=${3:-0}
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
mkdir -p "$work"
flags=();if [ "$syn" = 1 ];then flags=(-DSYNTHESIS);fi
verilator --binary --timing -j 4 -Wno-fatal "${flags[@]}" --top-module tb_land_epoch -GMUT="$mut" --Mdir "$work/obj_s${syn}_m${mut}" rtl/test/qwen_dv/safe_storage/tb_land_epoch.sv rtl/test/qwen_dv/safe_storage/land_epoch_reference.sv rtl/common/landed_parent/ot_pl_land.sv > "$work/build_s${syn}_m${mut}.log" 2>&1
"$work/obj_s${syn}_m${mut}/Vtb_land_epoch"
