#!/bin/bash
# usage: io_budget.sh <orfs dir> <out prefix> [SKEW_PS=150] [WIRE_PS=100]: per corner, measure L (mid of the rise
# latency range) then time the IO against it (io_budget.tcl).  Prints OT_L / OT_IO_IN / OT_IO_OUT per corner.
set -euo pipefail
D=$(cd "$1" && pwd); O=$2; S=${3:-150}; W=${4:-100}; H=$(cd "$(dirname "$0")" && pwd)
for c in ss ff; do
  docker run --rm -e CORNER=$c -v $D:/work -v $H:/t openroad/orfs:latest bash -lc "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /t/clock_latency.tcl" > ${O}_lat_$c.log 2>&1
  L=$(awk '/rise -> rise/{f=1} f && /[0-9] latency$/{print ($1+$2)/2; exit}' ${O}_lat_$c.log)
  test -n "$L" || { echo "missing $c clock insertion" >&2; exit 1; }
  docker run --rm -e CORNER=$c -e L_PS=$L -e SKEW_PS=$S -e WIRE_PS=$W -v $D:/work -v $H:/t openroad/orfs:latest bash -lc "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /t/io_budget.tcl" > ${O}_io_$c.log 2>&1
  echo "$c OT_L $L $(grep -E '^OT_IO' ${O}_io_$c.log | tr '\n' ' ')"
done
