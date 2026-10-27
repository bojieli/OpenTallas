#!/bin/bash
# QC-SU-F4G chain (COORD RULING QC-SU-F4F RP1 21:28): structural successor of F4F on the SAME post-hold GRT DB
# (F4F 5_1_grt.odb copied, sha recorded; spec/CTS/GRT/hold unchanged, so no new CTS/GRT and no model input changes):
#  1 tree M5V/M6H guide rewrite (unchanged guide_tree_m56.py)
#  2 CLOCK FIRST: all 113/1xx clock nets detail-routed alone, tree nets with NDR OT_CK_M6_2S (1W, 2x M6 spacing) (a)+(b)
#  3 ONE signal DRT on that DB: clock pre-routed + locked, M6 obstructed except the locked tree M6 (b) -- no strip loop
#  4 gates: clock wire sha unchanged by step 3 (LOCK), DRC 0, M6 census 0 non-tree nets
#  5 unchanged F4E tail: finish/RCX -> per-shape M6 abstract -> meas -> signoff.py -> lec.py; (c) per-island GRT->RCX shift
# usage: f4g_chain.sh KIT   (env OT_F4G_LOCK = fixed|dnt|none, default none; the lock is measured by clkdiff.py, not assumed)
set -uo pipefail
K=$(cd "$1" && pwd); H=$(cd "$(dirname "$0")" && pwd); M=$H/main_sofix/tools/die_plan; IMG=openroad/orfs:asap7lock
LOCK=${OT_F4G_LOCK:-none}   # probe 10-26 21:5x: FIXED wire type and dont_touch do NOT stop DRT rip-up (same 3/113 local pin-area re-routes as none)
HB=$(ls -d $K/run/results/asap7/*/base); B=/work/run/results/asap7/$(basename $(dirname $HB))/base
LB=$(ls -d $K/run/logs/asap7/*/base)
st() { echo "F4G_STAGE $1 $(date -Is)" | tee -a $K/f4g_chain.txt; }
own() { docker run --rm -v "$K":/work $IMG chown -R $(id -u):$(id -g) /work >/dev/null 2>&1; }
orp() { local nm=$1 mem=$2 cpu=$3; shift 3; docker run --rm --name f4g-$nm-$(basename $K)-$$ --memory=$mem --memory-swap=$mem --cpus=$cpu -v $K:/work -w /work "$@"; }
pyo() { local odb=$1 s=$2; shift 2; orp py 8g 2 -e ODB=$odb "$@" $IMG bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -python -exit /work/$s" 2>&1; }
cp $H/f4g_m6_strip.py $H/clkdiff.py $H/f4g_guides.tcl $H/f4g_clock_route.tcl $H/f4g_pre_drt_sig.tcl $H/f4g_post_drt.tcl $H/m6_strip.py $H/wfp.py $H/treelay.py $H/m6_census.py $K/
[ -e $HB/5_1_grt_f4f_posthold.odb ] || cp -p $HB/5_1_grt.odb $HB/5_1_grt_f4f_posthold.odb
st "F4G chain start lock $LOCK input 5_1_grt_f4f_posthold.odb sha256 $(sha256sum $HB/5_1_grt_f4f_posthold.odb | cut -c1-16)"
# 1 guides
orp gd 8g 2 -e IN=$B/5_1_grt_f4f_posthold.odb -e OUT0=$B/route_grt_final.guide -e OUT1=$B/route_tree_m56.guide -e JSON=$B/guide_m56.json $IMG bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit -no_splash /work/f4g_guides.tcl" > $K/f4g_guides.log 2>&1
grep -q F4G_GUIDES $K/f4g_guides.log || { st "F4G guides FAIL"; exit 7; }
# 2 clock first
orp clk 24g 16 -e IN=$B/5_1_grt_f4f_posthold.odb -e G1=$B/route_tree_m56.guide -e OUT=$B/5_1_grt_f4g_clk.odb -e DRC=/work/f4g_clk_drc.rpt $IMG bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 16 -exit -no_splash /work/f4g_clock_route.tcl" > $K/f4g_clock_route.log 2>&1; r=$?; own
grep -E "F4G_NDR|F4G_B1" $K/f4g_clock_route.log >> $K/f4g_chain.txt
v=$(grep "Number of violations" $K/f4g_clock_route.log | tail -n 1)
echo "F4G_B1_DRC $v" >> $K/f4g_chain.txt
{ [ $r = 0 ] && grep -q F4G_B1_DONE $K/f4g_clock_route.log && echo "$v" | grep -q "= 0\.$"; } || { st "F4G clock-first route FAIL rc $r"; exit 7; }
echo "F4G_B1_WFP $(pyo $B/5_1_grt_f4g_clk.odb wfp.py | grep WFP)" >> $K/f4g_chain.txt
echo "F4G_B1_TREE $(pyo $B/5_1_grt_f4g_clk.odb treelay.py | grep TL_TOTAL)" >> $K/f4g_chain.txt
pyo $B/5_1_grt_f4g_clk.odb treelay.py -e V=1 | grep "^TL" > $K/f4g_tree_layers_clk.txt
# 3 one signal route on the clock-routed DB
# try 5 (side 64, NDR cleared) 22:30 STOPPED: 380+ tree-vs-obstruction spacing-table markers the locked tree cannot fix.
# try 6: NDR KEPT in the signal route + f4g_m6_strip.py side 128 / end 192 (see its header).
# strip side 64 (try 4 rp1 22:18 FAIL with 80): the NDR puts parallel trunks 160 dbu apart; two 80-dbu openings then
# merge into one 384-dbu open channel and 11 signal nets took M6 between Q0/Q4 trunks. side < 80 keeps an obstruction
# between every NDR pair, side >= 32 keeps the (locked, pre-routed) tree DRC-clean against it; open gap 64 < 96 = no signal fits.
orp st 8g 2 -e REF=$B/5_1_grt_f4g_clk.odb -e OUT=/work/m6_strip_f4g.txt -e SIDE=${F4G_SIDE:-128} -e END=${F4G_END:-192} $IMG bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -python -exit /work/f4g_m6_strip.py" > $K/m6_strip_f4g.log 2>&1
grep M6_STRIP $K/m6_strip_f4g.log >> $K/f4g_chain.txt || { st "F4G strip FAIL"; exit 7; }
cp -p $HB/5_1_grt_f4g_clk.odb $HB/5_1_grt.odb
rm -f $LB/5_2_route.json
st "F4G signal DRT start (5_1_grt.odb := 5_1_grt_f4g_clk.odb)"
orp drt 40g 16 -w /OpenROAD-flow-scripts/flow -e OT_F4G_G1=$B/route_tree_m56.guide -e OT_M6_STRIP=/work/m6_strip_f4g.txt -e OT_F4G_LOCK=$LOCK $IMG bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=16 PRE_DETAIL_ROUTE_TCL=/work/f4g_pre_drt_sig.tcl POST_DETAIL_ROUTE_TCL=/work/f4g_post_drt.tcl do-5_2_route" > $K/f4g_drt.log 2>&1; r=$?; own
[ $r = 0 ] || { st "F4G signal DRT FAIL rc $r"; exit 7; }
grep -E "F4G_SIG_PRE|F4G_SIG_POST" $K/f4g_drt.log >> $K/f4g_chain.txt
d=$(grep -o '"detailedroute__route__drc_errors"[^,]*' $LB/5_2_route.json)
w1=$(pyo $B/5_1_grt_f4g_clk.odb wfp.py | grep WFP); w2=$(pyo $B/5_2_route.odb wfp.py | grep WFP); c=$(pyo $B/5_2_route.odb m6_census.py | grep M6_CENSUS | tail -n 1)
echo "F4G_B2 $d $c" >> $K/f4g_chain.txt; echo "F4G_B2_WFP $w2" >> $K/f4g_chain.txt
cdf=$(orp cd 8g 2 -e A=$B/5_1_grt_f4g_clk.odb -e B=$B/5_2_route.odb $IMG bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -python -exit /work/clkdiff.py" 2>&1 | grep CLKDIFF)
if echo "$cdf" | grep -q "changed_nets 0 of"; then echo "F4G_LOCK PASS every clock-net shape set identical before/after the signal route ($(echo "$cdf" | head -n 1))" >> $K/f4g_chain.txt
else echo "F4G_LOCK FAIL clock shapes changed by the signal route:" >> $K/f4g_chain.txt; echo "$cdf" | cut -c1-300 >> $K/f4g_chain.txt; fi
echo "F4G_B2_TREE $(pyo $B/5_2_route.odb treelay.py | grep TL_TOTAL)" >> $K/f4g_chain.txt
pyo $B/5_2_route.odb treelay.py -e V=1 | grep "^TL" > $K/f4g_tree_layers_final.txt
echo "$c" | grep -q "'other'" && { st "F4G LAYER_SEP FAIL: non-tree net on M6 after the one signal route"; exit 7; }
echo "$d" | grep -q ': 0' || { st "F4G DRC FAIL after the one signal route"; exit 7; }
st "F4G LAYER_SEP PASS in ONE signal route: 0 non-tree M6 nets, DRC 0"
# 5 unchanged F4E tail
bash $H/finish_f4a.sh $K || { st "finish FAIL"; exit 8; }
TOP=$(sed -n 's/^export DESIGN_NAME = //p' $K/config.mk)
docker run --rm --memory=8g --memory-swap=8g --cpus=2 -v $K:/work -v $H/abstract_m6.tcl:/a.tcl:ro $IMG bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; ODB=$B/6_final.odb OUT=$B/${TOP}_pershape.lef openroad -exit -no_splash /a.tcl" > $K/abstract_m6.log 2>&1
own
cp $HB/$TOP.lef $HB/${TOP}_bloated.lef
python3 -I $H/abstract_m6.py $HB/${TOP}_bloated.lef $HB/${TOP}_pershape.lef $HB/$TOP.lef $K/abstract_m6.json >> $K/f4g_chain.txt 2>&1 || st "abstract_m6 FAIL"
bash $H/meas_all.sh $(basename $K) prehold run/results/asap7/$(basename $(dirname $HB))/base >> $K/f4g_chain.txt 2>&1
for c in grt_TT grt_FF rcx_TT_prehold rcx_FF_prehold; do echo "F4G_LEAF $c $(python3 -I $H/leaf_stats.py $K/meas/$c.tsv | tail -n 1)" >> $K/f4g_chain.txt; done
python3 -I $H/island_shift.py $(basename $K) $K/meas/grt_TT.tsv $K/meas/rcx_TT_prehold.tsv $K/meas/grt_FF.tsv $K/meas/rcx_FF_prehold.tsv > $K/island_shift.json 2>> $K/f4g_chain.txt
SIGNOFF_DOCKER=docker python3 -I $M/signoff.py run --run-dir $K/run --kit $K --corners tt,ff --ff-vclk auto --out $K/signoff_main --image $IMG > $K/signoff_main.log 2>&1; so=$?
docker run --rm --memory=24g --memory-swap=24g --cpus=8 -v $K:/work -v $M:/m:ro $IMG bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /m/lec.py /work --netlist $B/6_final.v --out /work/lec_final" > $K/lec_final.log 2>&1; lr=$?
own
grep -E '^SIGNOFF' $K/signoff_main.log >> $K/f4g_chain.txt; tail -n 1 $K/lec_final.log >> $K/f4g_chain.txt
st "F4G CHAIN_DONE signoff rc $so lec rc $lr"
exit $so
