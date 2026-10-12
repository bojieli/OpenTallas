#!/bin/bash
set -eu
cd "$(dirname "$0")/../../.."
OUT=${1:?}; MUT=${2:-0}; SKEW=${3:-0.1};mkdir -p "$OUT"
D=${TILED_RTL_DIR:-physical/hbm_accel_die_views/su/rtl_tile_xl}
DEF=();if [ "$MUT" = 1 ];then DEF=(-DOT_SU_TILE_MUT_NOLOCKUP);fi
iverilog -g2012 -Ptb_su_tile_xl.W=${WCT:-448} "${DEF[@]}" -Ptb_su_tile_xl.SKEW="$SKEW" -s tb_su_tile_xl -o "$OUT/tile.vvp" "$D/hfd_su_tile.sv" "$D/hfd_su_tile_xl.sv" "$D/ot_su12_light_simstub.sv" tests/rtl/hub_reset/tb_su_tile_xl.sv
vvp -n "$OUT/tile.vvp" | tee "$OUT/result.log"
grep -q '^TILE_XL PASS' "$OUT/result.log"
