#!/usr/bin/env bash
set -euo pipefail
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
E=rtl/dsrom_sys/s81_dv/eng
H=rtl/hdc
SRC=("$H/ot_hdc_fastfp.sv" "$H/ot_hdc_prefix.sv" "$H/ot_hdc_fp32_f12.sv" "$E/ot_s81sl_ve_fp.sv" "$E/test/tb_s81sl_ve_fp.sv")
"$VL" --version > tool.txt
for m in 0 1 2; do
 "$VL" --binary --timing -j 4 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -DOT_S81_VE_LOADSAFE5 --top-module tb_s81sl_ve_fp -GMUT=$m --Mdir obj_$m "${SRC[@]}" > build_$m.log 2>&1
 set +e
 ./obj_$m/Vtb_s81sl_ve_fp +n=300000 +verilator+seed+17 +verilator+rand+reset+2 > run_$m.log 2>&1
 rc=$?
 set -e
 if [ "$m" = 0 ]; then [ "$rc" = 0 ]; else [ "$rc" != 0 ]; fi
 echo "UNIT m=$m rc=$rc"
done
