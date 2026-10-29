#!/bin/bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
export PATH=/home/ubuntu/.local/opentallas-tools/bin:$PATH
m=$1
opts=()
if [ "$m" = mut ]; then opts=(-DSOURCE_TAG_MUT -GMUT=1); fi
verilator --binary --timing -j 8 -MAKEFLAGS 'OBJCACHE=' -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -DSYNTHESIS -Io -In --top-module tb --Mdir "obj_$m" "${opts[@]}" -f files.f sram_models.sv tb.sv > "build_$m.log" 2>&1
"./obj_$m/Vtb" > "run_$m.log" 2>&1
cat "run_$m.log"
