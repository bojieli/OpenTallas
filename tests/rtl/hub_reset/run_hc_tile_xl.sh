#!/bin/bash
# conservative-1011 [B hfd_hc]: run_hc_tile_xl.sh OUT MUT(0|1) SKEW [STUB(0|1)]  -> TILE_XL PASS / FAIL
set -eu
cd "$(dirname "$0")/../../.."
OUT=${1:?}; MUT=${2:-0}; SKEW=${3:-0.1}; STUB=${4:-0}; mkdir -p "$OUT"
D=${TILED_RTL_DIR:-physical/hbm_accel_die_views/hcp/rtl_tile_xl}
DEF=(); [ "$MUT" = 1 ] && DEF=(-DOT_HC_TILE_MUT_NOLOCKUP)
if [ "$STUB" = 1 ]; then LANE=("$D/ot_dsrom_su_hcpost_lane_pr_simstub.sv")
else LANE=(rtl/hdc/v41x/ot_dsrom_su_hcpost_lane_pr.sv rtl/hdc/v41x/ot_dsrom_su_hcpost.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/v41x/ot_dsrom_su_add6.sv); fi
iverilog -g2012 "${DEF[@]}" -Ptb_hc_tile_xl.SKEW="$SKEW" -s tb_hc_tile_xl -o "$OUT/tile.vvp" "$D/hfd_hc_tile.sv" "$D/hfd_hc_tile_xl.sv" "${LANE[@]}" tests/rtl/hub_reset/tb_hc_tile_xl.sv
vvp -n "$OUT/tile.vvp" | tee "$OUT/result.log" | tail -4
grep -q '^TILE_XL PASS' "$OUT/result.log"
