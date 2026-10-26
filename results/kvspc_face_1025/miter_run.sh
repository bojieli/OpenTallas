#!/bin/bash
# KV-CORE-RTL/PC miter: build + run one prepared miter dir (heavy: via ot-run)
D=$1; export PATH=/srv/opentallas-scratch2/claude/kv-cores-1025r/bin:$PATH
cd $D || exit 2
verilator --binary --timing -j 8 -MAKEFLAGS "OBJCACHE=" -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-PINMISSING -DSYNTHESIS -Io -In --top-module tb --Mdir obj -f files.f tb.sv > build.log 2>&1 || { echo BUILD FAIL; grep -m 10 -i error build.log; exit 1; }
./obj/Vtb > sim.log 2>&1
grep -E "MITER|MISMATCH" sim.log | head -8
