#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch2/claude/codex-hbm-hcol-head5-sourceproof-0205
mkdir -p out
sha256sum tb.sv head5.sv native/*.sv > out/sources.sha256
vl=$HOME/.local/opentallas-tools/bin/verilator
[ -x "$vl" ] || vl=verilator
"$vl" --binary --timing -j 2 -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_hcol_regional_equiv --Mdir "$PWD/out/obj" tb.sv head5.sv native/*.sv > out/build.log 2>&1
out/obj/Vtb_hcol_regional_equiv +MUT=0 > out/positive.log 2>&1
set +e
out/obj/Vtb_hcol_regional_equiv +MUT=1 > out/mutant.log 2>&1
rc=$?
set -e
[ "$rc" -ne 0 ]
grep 'HCOL_REGIONAL_EQ PASS' out/positive.log
grep 'HCOL_REGIONAL_EQ FAIL' out/mutant.log
