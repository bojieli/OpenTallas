#!/bin/bash
# SB_PIPE=4 (precomputed segment-end + registered 2:1 ready select): gate, in-context route (a0h/a1p recipe) through DRT + SS/FF STA,
# full-token layer-parallel (+poison), REAL_MEM P0/P255.  Pinned wt/ @ 324641d00.
M=4
R=/srv/opentallas-scratch/claude/qwen-async-segpre; S=$R/wt
P1=/srv/opentallas-scratch/claude/qwen-async-full; LP=/srv/opentallas-scratch/claude/layer-parallel-sim; RM=/srv/opentallas-scratch/claude/realmem
T="python3 $S/tools/qwen_rom_layer_parallel_sim.py"
cd $R; mkdir -p plans runs res exit logs out
st() { echo "$(date -u +%FT%TZ) $*" >> $R/chain.log; }
waitall() { until [ "$(ls $R/runs/$(basename $1)/*/exit.json 2>/dev/null | wc -l)" -ge "$(python3 -c "import json;print(len(json.load(open(\"$1/plan.json\"))[\"jobs\"]))")" ]; do sleep 60; done; }
st "run4 src=$(git -C $S rev-parse HEAD)"
( cd $S; python3 tools/qwen_tp4_async_coll_verilator_gate.py --work $R/vg4 --result $R/res/gate_sbpipe4.json --seeds 2 --sb-pipe 4 > $R/logs/gate4.log 2>&1; st "GATE m=4 rc=$?" ) &
(
  cd $S; export OT_ORFS_NUM_CORES=20
  COMMON="--view asap7 --top ot_qwen_tp_seq_async_ctx_w12 --source rtl/rom/ot_qwen_tp_seq_async_w12.sv --source rtl/rom/ot_qwen_tp_seq_async_ctx_w12.sv \
 --clock-period-ns 0.833333 --clock-uncertainty-ns 0.060 --clock-uncertainty-hold-ns 0.025 --corner TT --orfs-corner WC --hold-corners WC,BC \
 --max-transition-ns --max-fanout 32 --slew-margin-percent 30 --false-path-io --orfs-var ADDER_MAP_FILE= --keep-heavy-artifacts --hold-margin-ns 0.01 --die-area 0 0 130 130 --core-area 2.16 2.16 127.84 127.84"
  st "PHYS START route_f4"
  /srv/opentallas-scratch/admit.sh 24 -- python3 tools/run_abi3_physical.py $COMMON --param ASYNC_COLL=1 --param SB_PIPE=4 --stages synth,pnr \
    --nickname-tag qasp_f4 --keep-workdir $R/out/work_f4 --output $R/out/route_f4.json --force > $R/logs/route_f4.log 2>&1
  rc=$?; echo $rc > $R/exit/route_f4.rc; st "PHYS END route_f4 rc=$rc"
  python3 tools/qwen_async_seq_incontext_physical.py sta --workdir $R/out/work_f4 --nickname opentallas_ot_qwen_tp_seq_async_ctx_w12_asap7_qasp_f4 --out $R/out/sta_f4.json > $R/logs/sta_f4.log 2>&1
  st "PHYS STA f4 rc=$?"
) &
(
  cd $S; RMA="--groups 6144 --su-width 64 --lv 7 --smin 7 --smax 11 --tcut 7 --bd 41 --xvm 1 --nws 5 --tws 38 --ord 7 --mem-extra 1 --code-banks 5 --tp 4 --coll-lat 339 --coll-depth 256 --enable-ar256 --async-coll --sb-pipe $M --real-mem"
  /srv/opentallas-scratch/admit.sh 64 -- python3 tools/qwen_rom_rt_token_w12_rm_async.py --workdir $R/rmbuild$M --build-dir $R/rmbuild$M --stages $RM/stages_dummy.txt --oracle /dev/null --pos 0 --token 0 $RMA --build-only --jobs 32 > $R/logs/rmbuild$M.log 2>&1
  rc=$?; st "B$M build rc=$rc"; [ $rc = 0 ] || exit 1
  run_one() { st "B START $1"
    /srv/opentallas-scratch/admit.sh 16 -- python3 tools/qwen_rom_rt_token_w12_rm_async.py --workdir $R/rm/$1 --build-dir $R/rmbuild$M --stages $P1/stages_rm_imgFC_r2.txt --oracle $3 --pos $2 --token $4 $RMA --threads 12 --result $R/res/$1.json > $R/logs/$1.log 2>&1
    rc=$?; echo $rc > $R/exit/$1.rc; st "B END $1 rc=$rc"; }
  run_one rm_m${M}_p0 0 $RM/gold/tok0/P0 0 & run_one rm_m${M}_p255 255 $RM/gold/prompt/P255 6280 & wait
) &
A="--tp 4 --groups 6144 --count-width 18 --su-width 64 --lv 7 --smin 7 --smax 11 --tcut 7 --bd 41 --xvm 1 --nws 5 --tws 38 --ord 7 --mem-extra 1 --scale-local 0 --code-banks 5 --coll-lat 339 --coll-depth 256 --enable-ar256 --async-coll --sb-pipe $M"
/srv/opentallas-scratch/admit.sh 64 -- $T --build --workdir $R/lpbuild$M --source-root $S --driver tools/qwen_rom_rt_token_async_w12.py -- $A --jobs 32 > logs/lpbuild$M.log 2>&1
rc=$?; st "A$M build rc=$rc"; [ $rc = 0 ] || { wait; exit 3; }
sed "s#/srv/opentallas-scratch/claude/qwen-async-seqfix/runs#$R/runs#; s#/srv/opentallas-scratch/claude/qwen-async-seqfix/lpbuild#$R/lpbuild$M#" /srv/opentallas-scratch/claude/qwen-async-seqfix/fleet.json > fleet$M.json
PRE="--oracle $LP/data/oracle_tp4 --preload $LP/data/qrom-observer-L0-review-f5-20261003-r1/preload.hex --fleet fleet$M.json"
$T --plan --plan-dir plans/m$M $PRE --stages $P1/stages_fc.txt >> chain.log 2>&1
$T --plan --plan-dir plans/m$M-poison $PRE --stages $P1/stages_fc.txt --poison 7fbadbad >> chain.log 2>&1
for p in m$M m$M-poison; do until $T --launch --fill --plan-dir plans/$p >> logs/launch.log 2>&1; do sleep 60; done; st "A launched $p"; done
for p in m$M m$M-poison; do waitall plans/$p; $T --collect --plan-dir plans/$p > /dev/null 2>&1; $T --verify --plan-dir plans/$p > logs/verify-$p.out 2>&1; st "A verified $p rc=$?"; done
$T --verify --plan-dir plans/m$M --poison-verdict plans/m$M-poison/verdict.json --result plans/m$M/verdict.with-poison.json > logs/verify-m$M-final.out 2>&1
st "A m$M final verdict with poison rc=$?"
wait; st "run4 done"
