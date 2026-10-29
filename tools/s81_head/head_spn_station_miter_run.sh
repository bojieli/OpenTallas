#!/bin/bash
# DIE-HEAD-28 10-29: build + run one miter variant inside verilator/verilator:v5.032 (docker, memory-capped by caller).
# usage: run_miter.sh DIR VARIANT   (VARIANT = base | <mutant name in DIR/mutants>)
set -u
D=$1; V=$2
REAL=$D/real.sv; [ "$V" != base ] && REAL=$D/mutants/$V.sv
O=$D/obj_$V; rm -rf "$O"; mkdir -p "$O"
verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT \
  --x-assign 0 --x-initial 0 --top-module tb -Mdir "$O" -o sim \
  -f "$D/files.f" "$D/ref.sv" "$REAL" "$D/stubs.sv" "$D/tb.sv" > "$O/build.log" 2>&1
rc=$?
if [ $rc -ne 0 ]; then echo "BUILD_FAIL $V rc=$rc"; tail -20 "$O/build.log"; exit 2; fi
"$O/sim" +verilator+seed+12345 > "$D/run_$V.log" 2>&1
echo "RUN $V rc=$?"; grep -E "MITER_RESULT" "$D/run_$V.log"
