#!/bin/bash
# TYPE-REDUCE-3/HBM: build + run one gen_bench.py bench dir (Verilator 5.032 docker, the lane version).  Heavy: ot-run.
#   run_bench.sh BENCHDIR MEM_GB
B=$(cd "$1" && pwd -P); MEM=${2:-24}; IMG=verilator/verilator:v5.032
docker image inspect $IMG >/dev/null 2>&1 || docker pull -q $IMG >/dev/null || { echo "NO IMAGE $IMG"; exit 4; }
docker run --rm --memory=${MEM}g --memory-swap=${MEM}g -u $(id -u):$(id -g) -e HOME=/b -e CCACHE_DISABLE=1 -v "$B":/b -w /b --entrypoint bash $IMG -c \
  "verilator --version; verilator --binary --timing -j 8 -O1 -DSYNTHESIS -Irtl -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-BLKANDNBLK --top-module tb -Mdir obj -f files.f tb.sv > build.log 2>&1; rc=\$?; tail -3 build.log; [ \$rc = 0 ] || exit 5; ./obj/Vtb | tee sim.log | tail -8"
rc=$?; grep -h RESULT "$B/sim.log" 2>/dev/null; exit $rc
