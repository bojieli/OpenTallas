#!/bin/bash
set -euo pipefail
out=${1:?output directory required};mkdir -p "$out"
tile=${TILED_RTL_DIR:-physical/hbm_accel_die_views/su/rtl_tile_xl}
srcs=(tests/rtl/hub_reset/tb_su_tile_cg.sv "$tile/hfd_su_tile_xl.sv" "$tile/ot_su12_light_simstub.sv" rtl/hbm_accel/cg/ot_cg_tile.sv rtl/hdc/ot_hdc_cg.sv)
for sign in pos neg mutant; do
 args=();[ "$sign" != neg ] || args+=(-Ptb_su_tile_cg.SKEW=-0.1)
 [ "$sign" != mutant ] || args+=(-DOT_HUB_CG_MUT_LATE)
 iverilog -g2012 -Ptb_su_tile_cg.W=${WCT:-448} "${args[@]}" -o "$out/$sign.sim" "${srcs[@]}"
 vvp -n "$out/$sign.sim" > "$out/$sign.log"
 if [ "$sign" = mutant ];then grep -q 'TILE_CG FAIL mismatches=' "$out/$sign.log";else grep -q 'TILE_CG PASS checks=336' "$out/$sign.log";fi
 rm "$out/$sign.sim"
done
