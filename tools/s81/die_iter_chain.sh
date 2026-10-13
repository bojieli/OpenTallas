#!/bin/bash
# s81-die-iter (2026-10-12) die chain, from ds-1010/s81die chain_efs.sh (EPYC1 s81die2): 
#   die_iter_chain.sh <src snapshot> <recipe .opts (repo path)> <run dir> <tag> [threads] [die kind override: layer1|layer1e]
# + IR (irm: real abstracts + pdngen + PSM) on the spine (hub column) and field windows, in parallel with the clock plan.
# GEN -> own clock plan (clock-only CTS, tools/budgets/clock_plan.py) -> balanced kit (die_sta, --cfifo-colck binds the colck
# cfifo) || PLACE -> FULL-die GRT -> estimate_parasitics -global_routing SPEF -> STA TT / FF / SS.  Containers dieev_/de2_.
set -uo pipefail
S=$(readlink -f $1); R=$2; M=$3; TAG=$4; T=${5:-24}; KO=${6:-}
[ -e "$M/STATUS.log" ] && { echo "refusing to overwrite $M" >&2; exit 2; }
mkdir -p $M; M=$(readlink -f $M); cd $S
export OT_S81_CTRL_GATE_WARN=phys OT_S81_Q_LEF=physical/s81_die_views/q_elem_qs5f_efs/q_elem.lef.gz
A="$(cat $S/$R) --cfifo-colck"; [ -n "$KO" ] && A="$(echo "$A" | sed "s/--die [a-z0-9]*/--die $KO/")"; echo "$A" > $M/options.txt
KIND=$(echo "$A" | grep -o -- '--die [a-z0-9]*' | awk '{print $2}'); AK=$(echo "$A" | sed "s/--die $KIND//")
st(){ echo "$(date -u +%FT%TZ) $*" >> $M/STATUS.log; }
st "start src $(cat $S/SOURCE_SHA) recipe $R kind $KIND"
/srv/opentallas-scratch/admit.sh 40 -- python3 tools/dsrom_s81_fulldie.py real $A --work $M/a_real > $M/real_gen.log 2>&1 || { st "GEN_FAIL $(grep -a 'OT_HOP_GATE\|hop gate' $M/real_gen.log | tail -1)"; exit 1; }
st "GEN_DONE $(grep -a OT_HOP_GATE $M/real_gen.log | tail -1) $(grep -a OT_VIEW_BINDING $M/real_gen.log | tail -1)"
( for w in spine field; do
    I=$M/ir_$w; /srv/opentallas-scratch/admit.sh 40 -- python3 tools/dsrom_s81_fulldie.py irm $A --work $I --window $w > $M/ir_gen_$w.log 2>&1 || { st IR_GEN_FAIL $w; continue; }
    /srv/opentallas-scratch/admit.sh 60 -- docker run --rm --name dieit_${TAG}_ir_$w --cpus=16 --memory=120g -v $I:/work -w /work openroad/orfs:asap7lock \
      bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 16 -no_init -exit /work/run.tcl > /work/run.log 2>&1; chmod -R a+rwX /work"
    st "IR $w $(grep -h 'OT_IR_INNER\|Worstcase IR drop\|OT_IR ' $I/run.log | tr '\n' ' ')"
  done ) &
C=$M/clock; mkdir -p $C
( /srv/opentallas-scratch/admit.sh 40 -- python3 tools/budgets/extract_die.py --src $S --die s81r8_$KIND --s81-opts "$AK" --out $C/model.json.gz > $C/extract.log 2>&1 || { st CLOCK_EXTRACT_FAIL; exit 1; }
  pids=()
  for g in htop hreg region; do
    python3 tools/budgets/clock_plan.py emit --die-model $C/model.json.gz --group $g --name ${TAG}_$g --out $C/$g > $C/emit_$g.log 2>&1
    (cd $C/$g && /srv/opentallas-scratch/admit.sh 24 -- bash run.sh > run.out 2>&1) & pids+=("$!")
  done
  for p in "${pids[@]}"; do wait "$p" || { st CLOCK_CTS_FAIL; exit 1; }; done
  python3 tools/budgets/clock_plan.py record --die-model $C/model.json.gz --case $C/htop --case $C/hreg --case $C/region --out $C/plan.json > $C/record.log 2>&1 || { st CLOCK_RECORD_FAIL; exit 1; }
  gzip -kf $C/plan.json; st "CLOCK_PLAN $(test -s $C/plan.json.gz && echo done || echo failed)"
  rm -rf $M/kit; mkdir -p $M/kit
  /srv/opentallas-scratch/admit.sh 60 -- python3 tools/s81/die_sta.py kit --gen-root $S --views-root $S --s81-opts "$AK" --die $KIND \
      --out $M/kit --clock-plan $C/plan.json.gz --index-out $M/kit/index.json > $M/kit/kit.log 2>&1; echo $? > $M/kit/kit.exit
  echo $S > $M/kit/src_root; st "KIT rc=$(cat $M/kit/kit.exit) $(python3 -c "import json,sys;d=json.load(open('$M/kit/clock_delivery.json'));print('CLOCK_DELIVERY common',d['masters_common'],'early_tap',d['masters_early_tap'],'deep_pins',d['deep_clock_pins'],'estimated_R',len(d['estimated_R']),'spread_defects',len(d['spread_defects']))" 2>/dev/null)"; [ "$(cat $M/kit/kit.exit)" = 0 ] ) &
CK=$!
D=$M/a_real; date -u +%FT%TZ > $D/run.log.start
/srv/opentallas-scratch/admit.sh 40 -- docker run --rm --name dieit_${TAG}_place --cpus=$T --memory=60g -v $D:/work -w /work openroad/orfs:asap7lock \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads $T -no_init -exit /work/run.tcl > /work/run.log 2>&1; rc=\$?; chmod -R a+rwX /work; exit \$rc"
echo $? > $D/run.log.exit; date -u +%FT%TZ > $D/run.log.end; st "PLACE rc=$(cat $D/run.log.exit)"
wait $CK || { st CLOCK_OR_KIT_FAIL; exit 1; }
[ "$(cat $D/run.log.exit)" = 0 ] || { st PLACE_FAIL; exit 1; }
sed -e "s/--name s81_grt_/--name dieit_grt_/" -e "s/--name s81_sta_/--name dieit_sta_/" $S/physical/s81_die_views/dietop/dietop_grt_sta.sh > $M/dietop_grt_sta.sh; chmod +x $M/dietop_grt_sta.sh
# OT_GRT_ITERS (s81-die v16): global_route -congestion_iterations (default 30; the v16 release case runs 12)
cd $M && /srv/opentallas-scratch/admit.sh 120 -- $M/dietop_grt_sta.sh a_real grt kit 48 400 9.6 ${OT_GRT_ITERS:-30} || { st GRT_STA_FAIL; exit 1; }
grep -q OT_SPEF $M/grt/sta_tt.log || { st STA_NO_SPEF; exit 1; }
for c in tt ff ss; do echo "$c $(grep -E "^(worst slack|tns)" $M/grt/sta_$c.log | tr "\n" " ")"; done > $M/grt/summary.txt
st "CHAIN_DONE $(tr '\n' ' ' < $M/grt/summary.txt)"
# post-GRT (2026-10-12 s81-die-iter): relay/station clock-pin check, OCV bound, GRT-vs-DRT cap error bar (x1.40 / x2.44),
# region DRT staged when the die GRT has 0 overflow
bash $S/tools/s81/die_sens.sh $M $S $TAG; st "SENS_DONE"
