#!/bin/bash
# mk_r3.sh SRC DST SPEC : QC-SU-LAT-R3 kit from the R2 kit (same synth/floorplan/3_1/3_2, GEOM-reviewed lineage).
# Re-places from 3_3 with PUSHDOWN islands (pushdown.tcl: no blockage, no OBS, FIRM drivers + ft ports) and the plan-built
# internal H-tree (cf/mscts_h.tcl + SPEC); TritonCTS off, no padding (ITERS 0).
set -euo pipefail
S=$1; D=$2; SPEC=$3; R=$(dirname $(readlink -f $0))
mkdir -p $D
rsync -a --exclude 'run/results/*/*/base/3_3*' --exclude 'run/results/*/*/base/3_4*' --exclude 'run/results/*/*/base/3_5*' --exclude 'run/results/*/*/base/3_place*' \
  --exclude 'run/results/*/*/base/4_*' --exclude 'run/results/*/*/base/5_*' --exclude 'run/results/*/*/base/6_*' --exclude 'run/results/*/*/base/*.guide' \
  --exclude 'run/logs' --exclude 'run/reports' --exclude 'run/objects/*/*/base/*.odb' --exclude 'lat_*' --exclude 'trunk_*' --exclude 'taps.txt' \
  --exclude 'r2_*' --exclude 'geo*' --exclude '*.log' --exclude 'island.tcl' $S/ $D/
cd $D
cp $R/pushdown.tcl pushdown.tcl; cp $R/mscts_h.tcl cf/mscts_h.tcl; cp $SPEC mscts_spec.tcl
PG=$(grep '^export PRE_GLOBAL_PLACE_TCL' config.mk | tail -n1 | awk '{print $4}' | sed 's#/work/##')
sed -i 's#^source /work/island.tcl#source /work/pushdown.tcl#' $PG
grep -q 'source /work/pushdown.tcl' $PG || sed -i '1i source /work/pushdown.tcl' $PG
P=$(grep '^export PRE_CTS_TCL' config.mk | tail -n1 | awk '{print $4}' | sed 's#/work/##')
sed -i '/source \/work\/cf\/mscts_tree.tcl/d; /source \/work\/cf\/mscts_h.tcl/d' $P
sed -i 's#^ot_ms_build#source /work/cf/mscts_h.tcl\not_ms_build#' $P
sed -i '/^export OT_ISLAND/d; /^export OT_MSCTS_ITERS/d; /^export OT_H_NO_TRITON/d' config.mk
cat >> config.mk <<EOC

# ---- QC-SU-LAT-R3 $(date '+%Y-%m-%d %H:%M %Z') (from $S): METHODOLOGY 12.2a1 pushdown islands (no hole/OBS) +
# 12.8b internal H-tree (entry -> 4 legs -> 4 equal-load leaf islands -> B/S -> leaves), plan-computed cells (12.8 d1),
# designed macro leaf stage, TritonCTS off, NO padding.  Spec: mscts_spec.tcl (mkspec_h.py).
export OT_MSCTS_SPEC = /work/mscts_spec.tcl
export OT_MSCTS_EXPLICIT = 1
export OT_MSCTS_ITERS = 0
export OT_H_NO_TRITON = 1
EOC
echo "R3 kit from $S $(date -Is) spec $(head -1 mscts_spec.tcl | cut -c1-80)" > image.txt
grep -n 'pushdown\|mscts_h\|ot_ms_build' $PG $P
