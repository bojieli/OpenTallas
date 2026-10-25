#!/bin/bash
R=/srv/opentallas-scratch2/claude/kv-cores-1025r/ectlk; export PATH=/srv/opentallas-scratch2/claude/kv-cores-1025r/bin:$PATH
for m in nom mut; do
  python3 $R/miter_prep.py $m && python3 $R/sram_models.py $R/miter/$m && cp $R/tb.sv $R/miter/$m/ || exit 1
  cd $R/miter/$m && verilator --binary --timing -j 8 -MAKEFLAGS "OBJCACHE=" -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -DSYNTHESIS -Io -In --top-module tb --Mdir obj -f files.f sram_models.sv tb.sv > build.log 2>&1 || { echo BUILD FAIL $m; grep -m 10 -i error build.log; continue; }
  docker run --rm --memory=16g -u $(id -u):$(id -g) -v $R:$R -w $R/miter/$m --entrypoint ./obj/Vtb verilator/verilator:v5.032 > sim.log 2>&1
  echo "== $m"; grep -E "MITER|MISMATCH" sim.log | head -6; /usr/bin/tail -n 2 sim.log
done
