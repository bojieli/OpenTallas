#!/bin/bash
set -euo pipefail
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
cd /srv/opentallas-scratch3/claude/codex-kv-phy-proof
verilator --binary --timing -Wno-fatal -j 2 --top-module tb tb.sv >build.log 2>&1
./obj_dir/Vtb >bench.log 2>&1
verilator --binary --timing -Wno-fatal -j 2 --Mdir obj_mut --top-module tb +define+MUTANT tb.sv >build_mut.log 2>&1
set +e
./obj_mut/Vtb >mutant.log 2>&1
rc=$?
set -e
[ "$rc" != 0 ];grep -q MISMATCH mutant.log
echo PASS_MUTANT_BYPASS_CAUGHT
