#!/bin/bash
# run_r3.sh KIT NICK : 3_3 place (pushdown islands) -> 3_place -> CTS (plan-built H-tree) -> GRT, then TT/FF latency probe
# (GRT RC, setRC_rcx), trunk probe and clock render.  No route here (route after GEOM PASS).
set -uo pipefail
K=$(cd "$1" && pwd); DZ=$2; IMAGE=openroad/orfs:asap7lock; R=$(dirname $(readlink -f $0)); B=run/results/asap7/$DZ/base
docker run --rm --name qcsl3-$(basename $K)-$$ --cpus=8 --memory=28g --memory-swap=28g -v "$K":/work -w /OpenROAD-flow-scripts/flow $IMAGE \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; rc=0; for t in do-3_3_place_gp do-3_4_place_resized do-3_5_place_dp do-3_place do-cts do-5_1_grt; do make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 \$t || { rc=\$?; echo STAGE_FAIL \$t rc \$rc; break; }; done; exit \$rc" > "$K/run_r3.log" 2>&1
rc=$?
docker run --rm -v "$K":/work $IMAGE chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
echo "place/cts/grt rc $rc $(date -Is)" >> "$K/image.txt"
grep -h "OT_PUSHDOWN\|OT_MSCTS_BUILD\|OT_MSCTS H\|OT_MSCTS_WINDOW\|OT_MSCTS_TAP \|OT_MSCTS_MACRO " "$K"/run/logs/asap7/$DZ/base/{3_3*,4_1_cts,5_1_grt}.log > "$K/taps.txt" 2>/dev/null
[ $rc = 0 ] || exit $rc
RC=/work/cf/main/setRC_rcx_asap7.tcl; [ -f $K/cf/main/setRC_rcx_asap7.tcl ] || RC=/OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
for c in TT FF; do lc=$(echo $c | tr A-Z a-z); LIBS=$(ls $K/macros/*_${lc}.lib | sed "s#$K#/work#" | tr "\n" " ")
 docker run --rm --name qcsl3-lat-$(basename $K)-$c-$$ --memory=16g --memory-swap=16g --cpus=2 -v $K:/work -v $R:/out:ro $IMAGE bash -c \
  "P_ODB=/work/$B/5_1_grt.odb P_SDC=/work/$B/5_1_grt.sdc P_LIBS='$LIBS' P_CORNER=$c P_RC=$RC P_OUT=/work/lat_$c.tsv /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /out/lat_probe.tcl" > $K/lat_$c.log 2>&1 &
 docker run --rm --name qcsl3-tr-$(basename $K)-$c-$$ --memory=12g --memory-swap=12g --cpus=2 -v $K:/work -v $R:/s:ro $IMAGE bash -c \
  "P_ODB=/work/$B/5_1_grt.odb P_SDC=/work/$B/5_1_grt.sdc P_LIBS='$LIBS' P_CORNER=$c P_RC=$RC /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /s/trunk_probe.tcl" 2>&1 | grep TRUNK > $K/trunk_$c.txt &
done
docker run --rm --memory=8g --cpus=1 -v $K:/work -v $R:/s:ro $IMAGE bash -c "P_ODB=/work/$B/4_cts.odb P_OUT=/work/r3_clk.csv /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /s/clk_dump.tcl" > $K/r3_render.log 2>&1 &
docker run --rm --memory=8g --cpus=1 -v $K:/work -v $R:/s:ro $IMAGE bash -c "P_ODB=/work/$B/3_place.odb P_OUT=/work/geo_r3.txt P_IX=0 P_IY=0 P_IS=0 /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /s/geo_dump.tcl" > $K/geo_r3.log 2>&1 &
wait
docker run --rm -v "$K":/work $IMAGE chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
python3 $R/clk_render.py $K/r3_clk.csv $K/r3_cts.png "$(basename $K) R3 H-tree CTS" >> $K/r3_render.log 2>&1
python3 $R/summ.py $K | tee -a $K/image.txt
