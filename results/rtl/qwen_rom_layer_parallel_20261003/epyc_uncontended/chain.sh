#!/bin/bash
# Detached chain for the layer-parallel Qwen TP4 stream on ot-epyc1tb. Survives the agent; see STATUS.md.
S=/srv/opentallas-scratch/claude/layer-parallel-sim
T="python3 $S/tool/qwen_rom_layer_parallel_sim.py"
cd $S
st() { echo "$(date -u +%FT%TZ) $*" >> $S/chain.log; }
fleet() { # binary
cat <<J
{"hosts": [{"name": "epyc1tb", "ssh": null, "binary": "$1", "workroot": "$S/runs", "path_map": {"/home/ubuntu/w12/": "$S/data/"},
 "slots": 80, "threads": 1, "env": {"RT_PROGRESS": "500"}, "mem_per_job_gb": 2.0, "mem_reserve_gb": 32.0, "max_load_per_core": 1.0,
 "capacity_note": "128 threads, 1.1 TB; one thread per job (measured best throughput/job on agidock128)"}]}
J
}
waitall() { # plan
  until [ "$(ls $S/runs/$(basename $1)/*/exit.json 2>/dev/null | wc -l)" -ge "$(python3 -c "import json;print(len(json.load(open('$1/plan.json'))['jobs']))")" ]; do sleep 60; done
}
st "chain start"
until [ -e $S/data/.xfer_done ]; do sleep 30; done
(cd $S/data && sha256sum -c --quiet $S/imgcheck.txt) > $S/imgcheck.out 2>&1 && st "740 image pins OK" || { st "IMAGE PIN FAIL"; echo 2 > $S/chain.rc; exit 2; }
sed "s#/home/ubuntu/w12/#$S/data/#g" data/st_tp4_sw64/stages.txt > stages-epyc.txt
python3 tool/qwen_rom_ar256_stage_images.py --stages stages-epyc.txt --out img256 > img256.log 2>&1 && sed -i "s#img256/#$S/img256/#g" img256/stages.txt && st "img256 derived" || { st "img256 FAIL"; echo 3 > $S/chain.rc; exit 3; }
fleet $S/build/qwen_rom_rt_lp > fleet-base.json; fleet $S/build-ar256/qwen_rom_rt_lp > fleet-ar256.json
mkdir -p plans
$T --plan --plan-dir plans/base-epyc-r1 --stages data/st_tp4_sw64/stages.txt --oracle data/oracle_tp4 --preload data/qrom-observer-L0-review-f5-20261003-r1/preload.hex --fleet fleet-base.json --reference original_terminal.json --pairs L18,head >> chain.log 2>&1
$T --plan --plan-dir plans/ar256-epyc-r1 --stages img256/stages.txt --oracle data/oracle_tp4 --preload data/qrom-observer-L0-review-f5-20261003-r1/preload.hex --fleet fleet-ar256.json >> chain.log 2>&1
$T --plan --plan-dir plans/ar256-poison-epyc-r1 --stages img256/stages.txt --oracle data/oracle_tp4 --preload data/qrom-observer-L0-review-f5-20261003-r1/preload.hex --fleet fleet-ar256.json --poison 7fbadbad >> chain.log 2>&1
st "stage 1: launch baseline (39) + AR256 (37)"
until $T --launch --fill --plan-dir plans/base-epyc-r1 >> launch.log 2>&1; do sleep 60; done
until $T --launch --fill --plan-dir plans/ar256-epyc-r1 >> launch.log 2>&1; do sleep 60; done
st "stage 1 launched"
waitall plans/base-epyc-r1; $T --collect --plan-dir plans/base-epyc-r1 > /dev/null 2>&1
$T --verify --plan-dir plans/base-epyc-r1 > verify-base.out 2>&1; st "baseline verified rc=$?"
st "stage 2: AR256 poison (37) as soon as capacity allows"
until $T --launch --fill --plan-dir plans/ar256-poison-epyc-r1 >> launch.log 2>&1; do sleep 60; done
waitall plans/ar256-epyc-r1; $T --collect --plan-dir plans/ar256-epyc-r1 > /dev/null 2>&1
$T --verify --plan-dir plans/ar256-epyc-r1 > verify-ar256.out 2>&1; st "ar256 verified (no poison) rc=$?"
waitall plans/ar256-poison-epyc-r1; $T --collect --plan-dir plans/ar256-poison-epyc-r1 > /dev/null 2>&1
$T --verify --plan-dir plans/ar256-poison-epyc-r1 > verify-ar256-poison.out 2>&1; st "ar256 poison verified rc=$?"
$T --verify --plan-dir plans/ar256-epyc-r1 --poison-verdict plans/ar256-poison-epyc-r1/verdict.json --result plans/ar256-epyc-r1/verdict.with-poison.json > verify-ar256-final.out 2>&1
rc=$?; st "ar256 final verdict with poison rc=$rc"
echo 0 > $S/chain.rc; st "chain done"
