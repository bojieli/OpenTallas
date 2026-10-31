#!/bin/bash
# DIE-KV-50 ectl four-column miter at the KV bound params. usage: run.sh NAME COLS O_AGE O_LAT RL
R=$(cd $(dirname $0); pwd); N=$1; mkdir -p $R/$N; cd $R/$N
ls $R/src/rtl/*/*.sv $R/src/rtl/*/*/*.sv > files.f; echo $R/$2 >> files.f; echo $R/sram_models.sv >> files.f; echo $R/wrap_o.sv >> files.f; echo $R/tb.sv >> files.f
docker run --rm --memory=24g -u $(id -u):$(id -g) -v $R:$R -w $R/$N --entrypoint verilator verilator/verilator:v5.032 --binary --timing -j 8 \
  -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -DSYNTHESIS -DO_AGE=$3 -DO_LAT=$4 -DRLV=$5 --top-module tb --Mdir obj -f files.f > build.log 2>&1 || { echo "BUILD FAIL $N"; grep -m 10 -i error build.log; exit 1; }
docker run --rm --memory=16g -u $(id -u):$(id -g) -v $R:$R -w $R/$N --entrypoint ./obj/Vtb verilator/verilator:v5.032 > sim.log 2>&1
echo "== $N"; grep -E "MITER|MISMATCH" sim.log | head -6
