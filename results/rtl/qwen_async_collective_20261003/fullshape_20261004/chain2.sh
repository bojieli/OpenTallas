#!/bin/bash
# r2 of the fused+cut-through (imgFC) jobs: r1 failed at file-open (stage list paths doubled by chain.sh's sed); r1 records kept.
R=/srv/opentallas-scratch/claude/qwen-async-full
LP=/srv/opentallas-scratch/claude/layer-parallel-sim
RM=/srv/opentallas-scratch/claude/realmem
S=$R/src
T="python3 $S/tools/qwen_rom_layer_parallel_sim.py"
cd $R
st() { echo "$(date -u +%FT%TZ) $*" >> $R/chain.log; }
waitall() { until [ "$(ls $R/runs/$(basename $1)/*/exit.json 2>/dev/null | wc -l)" -ge "$(python3 -c "import json;print(len(json.load(open('$1/plan.json'))['jobs']))")" ]; do sleep 60; done; }
sed "s#$R/$R/#$R/#g" imgFC/stages.txt > stages_fc.txt
{ head -1 $RM/stages_E_L0_L2.txt; grep -E '^L[012] ' stages_fc.txt; } > stages_rm_imgFC_r2.txt
st "r2 start (fixed stage paths)"
(
  cd $S; RMA="--groups 6144 --su-width 64 --lv 7 --smin 7 --smax 11 --tcut 7 --bd 41 --xvm 1 --nws 5 --tws 38 --ord 7 --mem-extra 1 --code-banks 5 --tp 4 --coll-lat 339 --coll-depth 256 --enable-ar256 --async-coll --real-mem"
  run_one() { st "B START $1"
    /srv/opentallas-scratch/admit.sh 16 -- python3 tools/qwen_rom_rt_token_w12_rm_async.py --workdir $R/rm/$1 --build-dir $R/rmbuild --stages $5 --oracle $3 --pos $2 --token $4 $RMA --threads 12 --result $R/res/$1.json > $R/logs/$1.log 2>&1
    rc=$?; echo $rc > $R/exit/$1.rc; st "B END $1 rc=$rc"; }
  run_one rm_imgFC_p0_r2 0 $RM/gold/tok0/P0 0 $R/stages_rm_imgFC_r2.txt &
  run_one rm_imgFC_p255_r2 255 $RM/gold/prompt/P255 6280 $R/stages_rm_imgFC_r2.txt &
  run_one rm_imgFC_p1023_r2 1023 $RM/gold/prompt_big/P1023 1796 $R/stages_rm_imgFC_r2.txt &
  wait
) &
PRE="--oracle $LP/data/oracle_tp4 --preload $LP/data/qrom-observer-L0-review-f5-20261003-r1/preload.hex --fleet fleet.json"
$T --plan --plan-dir plans/fc-r2 $PRE --stages stages_fc.txt >> chain.log 2>&1
$T --plan --plan-dir plans/fc-poison-r2 $PRE --stages stages_fc.txt --poison 7fbadbad >> chain.log 2>&1
for p in fc-r2 fc-poison-r2; do until $T --launch --fill --plan-dir plans/$p >> logs/launch.log 2>&1; do sleep 60; done; st "A launched $p"; done
for p in fc-r2 fc-poison-r2; do waitall plans/$p; $T --collect --plan-dir plans/$p > /dev/null 2>&1; $T --verify --plan-dir plans/$p > logs/verify-$p.out 2>&1; st "A verified $p rc=$?"; done
$T --verify --plan-dir plans/fc-r2 --poison-verdict plans/fc-poison-r2/verdict.json --result plans/fc-r2/verdict.with-poison.json > logs/verify-fc-r2-final.out 2>&1
st "A fc-r2 final verdict with poison rc=$?"
wait; echo 0 > chain2.rc; st "chain2 done"
