#!/usr/bin/env bash
set -euo pipefail
out=${1:?output};input=${2:?native programme JSON directory};mkdir -p "$out"
v="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
H=rtl/dsrom_sys/s81_dv/hostb;T=tools/s81_dv/hbc_production_2000
F="rtl/lib/ot_reset_sync.sv $H/dsdv_hostb_hold.sv $H/dsdv_hostb_crc512.sv $H/dsdv_hostb_rx.sv $H/dsdv_hostb_tx.sv $H/dsdv_hostb_stage.sv $H/dsdv_hbc1_loader.sv $H/dsdv_hbc1_affine_book.sv $H/dsdv_hostb_stage_hbc.sv $H/dsdv_hostb_return.sv"
python3 -I "$T/gen_reload.py" "$out/reload_vec" >"$out/reload_gen.log"
"$v" --binary --timing -O1 -Wno-fatal -Wno-WIDTH --top-module tb_hostb_reload --Mdir "$out/reload_obj" --build-jobs 4 $F "$T/tb_hostb_reload.sv" >"$out/reload_build.log" 2>&1
for m in 0 1 2 3 4;do "$out/reload_obj/Vtb_hostb_reload" +MODE="$m" +VEC="$out/reload_vec" >"$out/reload$m.log" 2>&1;cat "$out/reload$m.log";done
python3 -I "$T/gen_native.py" "$input" "$out/native_vec" >"$out/native_gen.log"
for stage in 0 1;do
 "$v" --binary --timing -O1 -Wno-fatal -Wno-WIDTH --top-module tb_hostb_native -GSTAGE="$stage" --Mdir "$out/native_obj$stage" --build-jobs 4 $F $H/dsdv_hostb_landing.sv $H/dsdv_hostb_source.sv rtl/dsrom_sys/s81_dv/unit/dsdv_static_ks6.sv "$T/tb_hostb_native.sv" >"$out/native_build$stage.log" 2>&1
 "$out/native_obj$stage/Vtb_hostb_native" +VEC="$out/native_vec" >"$out/native$stage.log" 2>&1;cat "$out/native$stage.log"
done
