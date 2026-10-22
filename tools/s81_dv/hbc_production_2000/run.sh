#!/usr/bin/env bash
set -euo pipefail
out=${1:?output};mkdir -p "$out"
v="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
"$v" --version >"$out/version.txt"
"$v" --binary --timing -O1 -Wno-fatal -Wno-WIDTH --top-module tb_hostb_source --Mdir "$out/obj" --build-jobs 4 \
 rtl/lib/ot_reset_sync.sv rtl/dsrom_sys/s81_dv/unit/dsdv_static_ks6.sv \
 rtl/dsrom_sys/s81_dv/hostb/dsdv_hostb_landing.sv rtl/dsrom_sys/s81_dv/hostb/dsdv_hostb_source.sv \
 tools/s81_dv/hbc_production_2000/tb_hostb_source.sv >"$out/build.log" 2>&1
for m in 0 1 2 3 4 5;do "$out/obj/Vtb_hostb_source" +MODE="$m" >"$out/mode$m.log" 2>&1;cat "$out/mode$m.log";done

H=rtl/dsrom_sys/s81_dv/hostb
python3 -I tools/s81_dv/hostctx_1021/gen_vectors.py "$out/vectors" >"$out/vectors.log"
"$v" --binary --timing -O1 -Wno-fatal -Wno-WIDTH --top-module tb_hostb_local_return --Mdir "$out/return_obj" --build-jobs 4 \
 rtl/lib/ot_reset_sync.sv $H/dsdv_hostb_hold.sv $H/dsdv_hostb_crc512.sv $H/dsdv_hostb_rx.sv $H/dsdv_hostb_tx.sv \
 $H/dsdv_hostb_stage.sv $H/dsdv_hbc1_loader.sv $H/dsdv_hbc1_affine_book.sv $H/dsdv_hostb_stage_hbc.sv $H/dsdv_hostb_return.sv \
 tools/s81_dv/hbc_production_2000/tb_hostb_local_return.sv >"$out/return_build.log" 2>&1
for m in 0 1;do "$out/return_obj/Vtb_hostb_local_return" +MODE="$m" +VEC="$out/vectors" >"$out/return$m.log" 2>&1;cat "$out/return$m.log";done
