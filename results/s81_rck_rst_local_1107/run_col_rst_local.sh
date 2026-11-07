#!/usr/bin/env bash
set -euo pipefail
cd /
D=${1:?payload};O=${2:?output};mkdir -p "$O"
verilator --binary --timing -j 4 -Wno-fatal -Wno-WIDTH -Wno-UNOPTFLAT -Wno-MULTITOP \
 +incdir+"$D" +define+OT_S81_SERDES_COL_PIN +define+OT_S81_SERDES_COL_RST_LOCAL \
 +define+OT_S81_RCK_RELAY4 +define+OT_S81_RM_STAGED +define+OT_S81_KP4_AM_FACE3 \
 --top-module tb_col_rst_local --Mdir "$O/obj" -o tb \
 "$D/ot_s81_kp4_common.sv" "$D/ot_s81_kp4_enc.sv" "$D/ot_s81_kp4_bm.sv" \
 "$D/ot_s81_kp4_dsyn.sv" "$D/ot_s81_kp4_ddly.sv" "$D/ot_s81_kp4_dchn.sv" "$D/ot_s81_kp4_dout.sv" "$D/ot_s81_kp4_dec.sv" \
 "$D/ot_pdie_serdes.sv" "$D/ot_s81_kp4_dec_native_flat.sv" "$D/ot_s81_kp4_dec_native_flat_lp.sv" \
 "$D/ot_pl_land.sv" "$D/ot_meso_fifo.sv" "$D/ot_pdie_serdes_locksafe.sv" \
 "$D/col_gold.sv" "$D/ot_pdie_serdes_col.sv" "$D/col_mut.sv" \
 "$D/ot_sram_1r1w2c_64x546_m1.v" "$D/ot_sram_1r1w_32x546_m1.v" "$D/tb_col_rst_local.sv" > "$O/build.log" 2>&1
"$O/obj/tb" > "$O/run.log" 2>&1
cat "$O/run.log"
