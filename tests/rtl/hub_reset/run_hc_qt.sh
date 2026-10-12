#!/bin/bash
# conservative-1011 [B hfd_hc]: run_hc_qt.sh OUT pos|neg -> HC_QT PASS / FAIL.  Tiled hfd_hc quarter (88 closed
# hfd_hc_tile_xl on the R25GQ 8 x 11 grid, 16 split roots) against the generator's reference (tb_hfd_hc); neg = the
# generator's negative netlist (chain 0 bit 0 inverted) which must FAIL.
set -u
cd "$(dirname "$0")/../../.."
OUT=${1:?}; K=${2:-pos}; mkdir -p "$OUT"; D=physical/hbm_accel_die_views/hcp/rtl_qt
M=$D/hfd_hc.sv; [ "$K" = neg ] && M=$D/hfd_hc_neg.sv
cp $D/tb_in.mem $D/tb_out.mem "$OUT/"
iverilog -g2012 -s tb -o "$OUT/q.vvp" $D/tb_hfd_hc.sv $M physical/hbm_accel_die_views/hcp/rtl_tile_xl/hfd_hc_tile_xl.sv $D/ot_dsrom_su_hcpost_lane_pr_simstub.sv || { echo "HC_QT BUILD_FAIL"; exit 3; }
(cd "$OUT" && vvp -n q.vvp) > "$OUT/run.log" 2>&1; rc=$?
tail -2 "$OUT/run.log"
if [ $rc = 0 ] && grep -q "mismatches=0" "$OUT/run.log" && ! grep -q FATAL "$OUT/run.log"; then echo "HC_QT PASS"; else echo "HC_QT FAIL"; exit 1; fi
