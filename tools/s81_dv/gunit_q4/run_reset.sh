#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../../.."
mkdir -p out
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
sha256sum tools/s81_dv/gunit_q4/{reset_candidate,tb_reset}.sv > out/reset_sources.sha256
"$V" --binary --timing -j 4 -Wno-fatal --top-module tb_reset --Mdir "$PWD/out/reset_obj" -o tb tools/s81_dv/gunit_q4/reset_candidate.sv tools/s81_dv/gunit_q4/tb_reset.sv > out/reset_build.log 2>&1
out/reset_obj/tb | tee out/reset_positive.log
