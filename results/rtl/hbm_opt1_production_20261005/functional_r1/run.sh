#!/bin/bash
set -eu
ulimit -t unlimited;ulimit -v unlimited;ulimit -f unlimited
J=/srv/opentallas/jobs-overflow/euclid-hbm-opt1-production-r1
cd /srv/opentallas/jobs-overflow/euclid-hbm-opt1-source-fa7e45395
export NUM_CORES=16 MAKEFLAGS=-j16 TMPDIR="$J/tmp" OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
trap 'rc=$?; echo "$rc" > "$J/exit"' EXIT
git rev-parse HEAD > "$J/source.commit"
git status --porcelain > "$J/source.dirty";test ! -s "$J/source.dirty"
mkdir "$J/pq"
for seq in stress ar_l20 wg other; do
 python3 tools/dshbm_sm_pq_production_seq.py run --seq "$seq" --nc 8 --active 1 --build-jobs 16 --out "$J/pq/${seq}_f1.json" --workdir "$J/work" > "$J/${seq}_f1.log" 2>&1
done
for seq in p6_stress p6_l20 p6_wg p6_other; do
 python3 tools/dshbm_sm_pq_production_seq.py run --seq "$seq" --nc 8 --active 6 --build-jobs 16 --out "$J/pq/${seq}_f6.json" --workdir "$J/work" > "$J/${seq}_f6.log" 2>&1
done
for seq in ar_l20 wg; do
 python3 tools/dshbm_sm_pq_production_seq.py run --seq "$seq" --nc 8 --active 1 --serial --build-jobs 16 --out "$J/pq/${seq}_f1s.json" --workdir "$J/work" > "$J/${seq}_f1s.log" 2>&1
done
for seq in p6_l20 p6_wg; do
 python3 tools/dshbm_sm_pq_production_seq.py run --seq "$seq" --nc 8 --active 6 --serial --build-jobs 16 --out "$J/pq/${seq}_f6s.json" --workdir "$J/work" > "$J/${seq}_f6s.log" 2>&1
done
python3 tools/dshbm_sm_pq_production_seq.py run --seq stress --nc 8 --active 1 --g1asb 1 --expect-fail --build-jobs 16 --out "$J/pq/stress_g1asb_negative.json" --workdir "$J/work" > "$J/negative.log" 2>&1
python3 tools/dshbm_hbm_opt_compose.py --rec "$J" > "$J/compose.log" 2>&1

