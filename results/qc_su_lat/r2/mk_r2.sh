#!/bin/bash
# mk_r2.sh SRC DST SPEC IX IY PINX PREGPL KIND   (QC-SU-LAT-R2 centre-entry structured-clock kit from a GEOM-reviewed kit)
# Keeps synth/floorplan/3_1/3_2 of SRC; re-places from 3_3 with the island; structured clock per SPEC; no padding (ITERS 0).
set -euo pipefail
S=$1; D=$2; SPEC=$3; IX=$4; IY=$5; PX=$6; PG=$7; KIND=$8; R=$(dirname $(readlink -f $0))
mkdir -p $D
rsync -a --exclude 'run/results/*/*/base/3_3*' --exclude 'run/results/*/*/base/3_4*' --exclude 'run/results/*/*/base/3_5*' --exclude 'run/results/*/*/base/3_place*' \
  --exclude 'run/results/*/*/base/4_*' --exclude 'run/results/*/*/base/5_*' --exclude 'run/results/*/*/base/6_*' --exclude 'run/results/*/*/base/*.guide' \
  --exclude 'run/results/*/*/base/*.lef' --exclude 'run/results/*/*/base/*.lib' --exclude 'run/logs' --exclude 'run/reports' --exclude 'run/objects/*/*/base/*.odb' \
  --exclude 'hold_checkpoints' --exclude 'signoff' --exclude 'so_exact' --exclude 'f6_*' --exclude 'lat_*' --exclude 'geo*.txt*' --exclude '*.log' $S/ $D/
cd $D
cp $R/island.tcl island.tcl; cp $SPEC mscts_spec.tcl
mkdir -p cf; [ -f cf/mscts_core.tcl ] || cp $R/mscts_core_base.tcl cf/mscts_core.tcl
python3 $R/patch_core.py cf/mscts_core.tcl
grep -q 'source /work/island.tcl' $PG || sed -i '1i source /work/island.tcl' $PG
if [ $KIND = band ]; then grep -v 'source /work/cf/mscts_band.tcl' pre_cts_b3.tcl > pre_cts_r2.tcl; fi
if [ $KIND = rp1 ]; then cp $R/rp1_M/cts_pre_ms.tcl $R/rp1_M/cts_post_ms.tcl $R/rp1_M/grt_post_ms.tcl .; fi
sed -i '/^export OT_MSCTS_CORR/d; /^export OT_MSCTS_PROJECTION/d; /^export OT_MSCTS_ITERS/d' config.mk
cat >> config.mk <<EOC

# ---- QC-SU-LAT-R2 $(date '+%Y-%m-%d %H:%M %Z'): METHODOLOGY 12.8 centre clock entry + structured clock (from $S) ----
# island 8.64 um at ($IX, $IY) (top-owned clock/reset hole, M9->M5 stack, ck = M5 interior pin); star of identical
# equal-stage chains (OT_MSCTS_EXPLICIT) to equal-load leaf clusters; NO tap/macro padding (ITERS 0 = measure only).
export OT_ISLAND = $IX $IY 8.64
export OT_CK_PIN_X = $PX
export OT_MSCTS_SPEC = /work/mscts_spec.tcl
export OT_MSCTS_EXPLICIT = 1
export OT_MSCTS_ITERS = 0
export OT_MSCTS_PROJECTION = 0
export OT_MSCTS_TRUNK_CELL = BUFx16f_ASAP7_75t_R
EOC
[ $KIND = band ] && echo 'export PRE_CTS_TCL = /work/pre_cts_r2.tcl' >> config.mk
[ $KIND = rp1 ] && printf 'export PRE_CTS_TCL = /work/cts_pre_ms.tcl\nexport POST_CTS_TCL = /work/cts_post_ms.tcl\nexport POST_GLOBAL_ROUTE_TCL = /work/grt_post_ms.tcl\n' >> config.mk
echo "R2 kit from $S $(date -Is)" > image.txt
ls run/results/asap7/*/base/
