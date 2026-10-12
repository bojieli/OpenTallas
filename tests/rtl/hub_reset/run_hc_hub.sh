#!/bin/bash
# conservative-1011 TWO-LEVEL: run_hc_hub.sh OUT pos|neg|mut -> HC_HUB PASS / FAIL.  Hardened composition of hfd_hc
# (hfd_hc_hub + die-level head relays + 88 hfd_hc_tile_xl) against the generator's reference (tb_hfd_hc).
# neg = composition with chain 0 bit 0 inverted; mut = hub mutant OT_HC_HUB_MUT (chain 1 fold bit 0 inverted); both must FAIL.
set -u
cd "$(dirname "$0")/../../.."
OUT=${1:?}; K=${2:-pos}; mkdir -p "$OUT"; D=physical/hbm_accel_die_views/hcp/rtl_hub
M=$D/hfd_hc.sv; DEF=""; [ "$K" = neg ] && M=$D/hfd_hc_neg.sv; [ "$K" = mut ] && DEF="-DOT_HC_HUB_MUT"
cp $D/tb_in.mem $D/tb_out.mem "$OUT/"
iverilog -g2012 $DEF -s tb -o "$OUT/q.vvp" $D/tb_hfd_hc.sv $M $D/hfd_hc_hub.sv physical/hbm_accel_die_views/hcp/rtl_tile_xl/hfd_hc_tile_xl.sv $D/ot_dsrom_su_hcpost_lane_pr_simstub.sv || { echo "HC_HUB BUILD_FAIL"; exit 3; }
(cd "$OUT" && vvp -n q.vvp) > "$OUT/run.log" 2>&1; rc=$?
tail -2 "$OUT/run.log"
if [ $rc = 0 ] && grep -q "mismatches=0" "$OUT/run.log" && ! grep -q FATAL "$OUT/run.log"; then echo "HC_HUB PASS"; else echo "HC_HUB FAIL"; exit 1; fi
