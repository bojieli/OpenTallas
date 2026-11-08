#!/usr/bin/env bash
set -euo pipefail
cd "${1:?}"
mkdir -p out
verilator --binary --timing -j 4 -Wno-fatal -Wno-WIDTH --top-module tb --Mdir out/obj -o tb *.sv >out/build.log 2>&1
out/obj/tb >out/run.log 2>&1
cat out/run.log
