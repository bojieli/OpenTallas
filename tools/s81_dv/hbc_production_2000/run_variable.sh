#!/usr/bin/env bash
set -euo pipefail
out=${1:?output};mkdir -p "$out"
v="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
python3 -I tools/s81_dv/hbc_production_2000/gen_variable.py "$out/vec" >"$out/gen.log"
H=rtl/dsrom_sys/s81_dv/hostb
"$v" --binary --timing -O1 -Wno-fatal -Wno-WIDTH --top-module tb_hostb_variable --Mdir "$out/obj" --build-jobs 4 \
 rtl/lib/ot_reset_sync.sv $H/dsdv_hostb_hold.sv $H/dsdv_hostb_crc512.sv $H/dsdv_hostb_rx.sv $H/dsdv_hostb_tx.sv \
 $H/dsdv_hostb_stage.sv $H/dsdv_hbc1_loader.sv $H/dsdv_hbc1_affine_book.sv $H/dsdv_hostb_stage_hbc.sv $H/dsdv_hostb_return.sv \
 tools/s81_dv/hbc_production_2000/tb_hostb_variable.sv >"$out/build.log" 2>&1
for n in 33 515;do "$out/obj/Vtb_hostb_variable" +COUNT="$n" +VEC="$out/vec" >"$out/w$n.log" 2>&1;cat "$out/w$n.log";done
