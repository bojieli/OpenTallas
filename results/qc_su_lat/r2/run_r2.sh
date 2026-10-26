#!/bin/bash
# run_r2.sh KIT DESIGN_NICK : re-place from 3_3 (island) -> CTS -> GRT, then latency probe TT/FF (GRT RC). No route.
set -uo pipefail
K=$(cd "$1" && pwd); DZ=$2; IMAGE=openroad/orfs:asap7lock; R=$(dirname $(readlink -f $0)); B=run/results/asap7/$DZ/base
docker run --rm --name qcsl2-$(basename $K)-$$ --cpus=8 --memory=28g --memory-swap=28g -v "$K":/work -w /OpenROAD-flow-scripts/flow $IMAGE \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; rc=0; for t in do-3_3_place_gp do-3_4_place_resized do-3_5_place_dp do-3_place do-cts do-5_1_grt; do make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 \$t || { rc=\$?; echo STAGE_FAIL \$t rc \$rc; break; }; done; exit \$rc" > "$K/run_r2.log" 2>&1
rc=$?
docker run --rm -v "$K":/work $IMAGE chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
echo "place/cts/grt rc $rc $(date -Is)" >> "$K/image.txt"
grep -h "OT_ISLAND\|OT_MSCTS_TRUNK\|OT_MSCTS_BUILD\|OT_MSCTS_WINDOW\|OT_MSCTS_TAP \|OT_MSCTS_MACRO \|OT_MSCTS_BAL" "$K"/run/logs/asap7/$DZ/base/{3_3*,4_1_cts,5_1_grt}.log > "$K/taps.txt" 2>/dev/null
[ $rc = 0 ] || exit $rc
RC=/work/cf/main/setRC_rcx_asap7.tcl; [ -f $K/cf/main/setRC_rcx_asap7.tcl ] || RC=/OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
for c in TT FF; do lc=$(echo $c | tr A-Z a-z); LIBS=$(ls $K/macros/*_${lc}.lib | sed "s#$K#/work#" | tr "\n" " ")
 docker run --rm --name qcsl2-lat-$(basename $K)-$c-$$ --memory=16g --memory-swap=16g --cpus=2 -v $K:/work -v $R:/out:ro $IMAGE bash -c \
  "P_ODB=/work/$B/5_1_grt.odb P_SDC=/work/$B/5_1_grt.sdc P_LIBS='$LIBS' P_CORNER=$c P_RC=$RC P_OUT=/work/lat_$c.tsv /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /out/lat_probe.tcl" > $K/lat_$c.log 2>&1 &
done; wait
docker run --rm -v "$K":/work $IMAGE chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
python3 $R/summ.py $K | tee -a $K/image.txt
