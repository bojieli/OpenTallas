#!/bin/bash
# Qwen TP4 async collective at full shape (claude/qwen-async-fullshape-20261004 @ src/SOURCE_COMMIT). Detached; see STATUS.md.
R=/srv/opentallas-scratch/claude/qwen-async-full
LP=/srv/opentallas-scratch/claude/layer-parallel-sim
RM=/srv/opentallas-scratch/claude/realmem
S=$R/src
T="python3 $S/tools/qwen_rom_layer_parallel_sim.py"
cd $R; mkdir -p plans runs res exit logs
st() { echo "$(date -u +%FT%TZ) $*" >> $R/chain.log; }
A='--tp 4 --groups 6144 --count-width 18 --su-width 64 --lv 7 --smin 7 --smax 11 --tcut 7 --bd 41 --xvm 1 --nws 5 --tws 38 --ord 7 --mem-extra 1 --scale-local 0 --code-banks 5 --coll-lat 339 --coll-depth 256 --enable-ar256 --async-coll'
fleet() { cat <<J
{"hosts": [{"name": "epyc1tb", "ssh": null, "binary": "$1", "workroot": "$R/runs", "path_map": {},
 "slots": 80, "threads": 1, "env": {"RT_PROGRESS": "500"}, "mem_per_job_gb": 2.0, "mem_reserve_gb": 150.0, "max_load_per_core": 1.0,
 "capacity_note": "128 threads, 1.1 TB; one thread per job"}]}
J
}
waitall() { until [ "$(ls $R/runs/$(basename $1)/*/exit.json 2>/dev/null | wc -l)" -ge "$(python3 -c "import json;print(len(json.load(open('$1/plan.json'))['jobs']))")" ]; do sleep 60; done; }
st "chain start src=$(cat $S/SOURCE_COMMIT)"
# ---- images: fused + cut-through from the one-stream img256 of the layer-parallel stream (36 layers + head)
python3 $S/tools/qwen_rom_async_coll.py --stages $LP/img256/stages.txt --out $R/imgFC --fuse --cut > logs/imgFC.log 2>&1 \
  && sed -i "s#imgFC/#$R/imgFC/#g" imgFC/stages.txt && st "imgFC derived" || { st "imgFC FAIL"; echo 2 > chain.rc; exit 2; }
# ---- REAL_MEM branch (B), in parallel with the layer-parallel branch
(
  st "B build start"
  cd $S; RMA="--groups 6144 --su-width 64 --lv 7 --smin 7 --smax 11 --tcut 7 --bd 41 --xvm 1 --nws 5 --tws 38 --ord 7 --mem-extra 1 --code-banks 5 --tp 4 --coll-lat 339 --coll-depth 256 --enable-ar256 --async-coll --real-mem"
  /srv/opentallas-scratch/admit.sh 64 -- python3 tools/qwen_rom_rt_token_w12_rm_async.py --workdir $R/rmbuild --build-dir $R/rmbuild --stages $RM/stages_dummy.txt --oracle /dev/null --pos 0 --token 0 $RMA --build-only --jobs 32 > $R/logs/rmbuild.log 2>&1
  rc=$?; echo $rc > $R/exit/rmbuild.rc; st "B build rc=$rc"; [ $rc = 0 ] || exit 1
  # E + L0-L2 stage lists: baseline one-stream (img256) and fused + cut-through (imgFC); E is the realmem embedding stage
  for v in img256:$LP/img256 imgFC:$R/imgFC; do n=${v%%:*}; f=${v#*:}
    { head -1 $RM/stages_E_L0_L2.txt; grep -E '^L[012] ' $f/stages.txt; } > $R/stages_rm_$n.txt; done
  run_one() { # name pos oracle token stages
    st "B START $1"
    /srv/opentallas-scratch/admit.sh 16 -- python3 tools/qwen_rom_rt_token_w12_rm_async.py --workdir $R/rm/$1 --build-dir $R/rmbuild --stages $5 --oracle $3 --pos $2 --token $4 $RMA --threads 12 --result $R/res/$1.json > $R/logs/$1.log 2>&1
    rc=$?; echo $rc > $R/exit/$1.rc; st "B END $1 rc=$rc"
  }
  for v in img256 imgFC; do
    run_one rm_${v}_p0 0 $RM/gold/tok0/P0 0 $R/stages_rm_$v.txt &
    run_one rm_${v}_p255 255 $RM/gold/prompt/P255 6280 $R/stages_rm_$v.txt &
    run_one rm_${v}_p1023 1023 $RM/gold/prompt_big/P1023 1796 $R/stages_rm_$v.txt &
  done
  wait; st "B done"
) &
# ---- layer-parallel branch (A): full token, ideal memory, ASYNC_COLL=1 binary
st "A build start"
/srv/opentallas-scratch/admit.sh 64 -- $T --build --workdir $R/lpbuild --source-root $S --driver tools/qwen_rom_rt_token_async_w12.py -- $A --jobs 32 > logs/lpbuild.log 2>&1
rc=$?; echo $rc > exit/lpbuild.rc; st "A build rc=$rc"; [ $rc = 0 ] || { wait; echo 3 > chain.rc; exit 3; }
fleet $R/lpbuild/qwen_rom_rt_lp > fleet.json
PRE="--oracle $LP/data/oracle_tp4 --preload $LP/data/qrom-observer-L0-review-f5-20261003-r1/preload.hex --fleet fleet.json"
$T --plan --plan-dir plans/fc $PRE --stages imgFC/stages.txt >> chain.log 2>&1
$T --plan --plan-dir plans/legacy $PRE --stages $LP/img256/stages.txt >> chain.log 2>&1
$T --plan --plan-dir plans/fc-poison $PRE --stages imgFC/stages.txt --poison 7fbadbad >> chain.log 2>&1
st "A launch fc, legacy, fc-poison"
for p in fc legacy fc-poison; do until $T --launch --fill --plan-dir plans/$p >> logs/launch.log 2>&1; do sleep 60; done; st "A launched $p"; done
for p in fc legacy fc-poison; do waitall plans/$p; $T --collect --plan-dir plans/$p > /dev/null 2>&1; $T --verify --plan-dir plans/$p > logs/verify-$p.out 2>&1; st "A verified $p rc=$?"; done
$T --verify --plan-dir plans/fc --poison-verdict plans/fc-poison/verdict.json --result plans/fc/verdict.with-poison.json > logs/verify-fc-final.out 2>&1
st "A fc final verdict with poison rc=$?"
wait
echo 0 > chain.rc; st "chain done"
