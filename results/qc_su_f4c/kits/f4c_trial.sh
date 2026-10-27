#!/bin/bash
# QC-SU-F4C TRIAL (plan model in band before build): F4A MIF0 placement (3_place.odb, unchanged) + F4C 8x8 equal-leaf
# sized spec (mscts_spec_f4c.tcl, OT_MSCTS_ITERS 0 = no CTS iteration) -> CTS -> GRT (standard layers) -> guide rewrite
# limited to the tree nets (M5 V / M6 H) -> DRT (top layer M6) -> tree/non-tree layer census -> fill/RCX/abstract ->
# meas_ck GRT + RCX TT/FF.  No hold repair, no pads/trims/ECOs (12.8).  usage: f4c_trial.sh KITDIR
set -uo pipefail
K=$(cd "$1" && pwd); H=$(cd "$(dirname "$0")" && pwd)
HB=$(ls -d $K/run/results/asap7/*/base); B=/work/run/results/asap7/$(basename $(dirname $HB))/base
mk() { local X=${2:-}; docker run --rm --name qcf4c-$1-$(basename $K)-$$ --cpus=16 --memory=40g --memory-swap=40g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=16 $X $1" > "$K/f4c_$1.log" 2>&1; r=$?; docker run --rm -v "$K":/work openroad/orfs:asap7lock chown -R $(id -u):$(id -g) /work/run; return $r; }
st() { echo "F4C_STAGE $1 $(date -Is)" | tee -a $K/f4c_trial.txt; }
st start
mk do-cts || { st "cts FAIL"; exit 3; }
mk do-5_1_grt || { st "grt FAIL"; exit 4; }
grep -h "S5_GRT_TT\|tap_window" $K/s5_grt_tt.txt 2>/dev/null | tail -2 >> $K/f4c_trial.txt
cp $HB/route.guide $HB/route_grt_orig.guide; cp $HB/5_1_grt.odb $HB/5_1_grt_f4c.odb
python3 -I $H/guide_tree_m56.py $HB/route_grt_orig.guide $HB/route.guide $K/guide_m56.json >> $K/f4c_trial.txt 2>&1 || { st "guide FAIL"; exit 5; }
rm -f $K/run/logs/asap7/*/base/5_2_route.json
mk do-5_2_route "MAX_ROUTING_LAYER=M6" || { st "drt FAIL"; exit 6; }
grep -o '"detailedroute__route__drc_errors"[^,]*' $K/run/logs/asap7/*/base/5_2_route.json >> $K/f4c_trial.txt
docker run --rm --memory=8g --memory-swap=8g --cpus=2 -v $K:/work -v $H/net_layers.py:/nl.py:ro -e ODB=$B/5_2_route.odb -e NETS=ALL openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -python -exit /nl.py' > $K/f4c_tree_layers.txt 2>&1
docker run --rm --memory=8g --memory-swap=8g --cpus=2 -v $K:/work -v $H/m6_census.py:/mc.py:ro -e ODB=$B/5_2_route.odb openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -python -exit /mc.py' > $K/f4c_m6_census.txt 2>&1
tail -3 $K/f4c_m6_census.txt >> $K/f4c_trial.txt
st drt_done
bash $H/finish_f4a.sh $K || { st "finish FAIL"; exit 7; }
cp $HB/5_1_grt_f4c.odb $HB/5_1_grt_prehold.odb
bash $H/meas_all.sh $(basename $K) prehold run/results/asap7/$(basename $(dirname $HB))/base >> $K/f4c_trial.txt 2>&1
st "CHAIN_DONE"
