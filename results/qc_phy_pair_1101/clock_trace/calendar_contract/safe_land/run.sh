#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p run
iverilog -g2012 -s tb_safe_land -o run/native.vvp ../inputs/ot_coll_static_linkcal.sv tb_safe_land.sv > run/compile.log 2>&1
vvp run/native.vvp +SLOT_EDGE=100 > run/eligible_positive.log 2>&1
vvp run/native.vvp +SLOT_EDGE=100 +RESET_CUT > run/reset_cancel_positive.log 2>&1
set +e
vvp run/native.vvp +SLOT_EDGE=115 > run/different_rate_overwrite_FAIL.log 2>&1
miss=$?
set -e
test "$miss" -ne 0
grep -q SAFE_LAND_EVENT_LOST run/different_rate_overwrite_FAIL.log
iverilog -g2012 -DOT_COLL_MUT_LAND_UNLANDED -s tb_safe_land -o run/mutant.vvp ../inputs/ot_coll_static_linkcal.sv tb_safe_land.sv > run/mutant_compile.log 2>&1
set +e
vvp run/mutant.vvp +SLOT_EDGE=100 > run/unlanded_mutant_FAIL.log 2>&1
mutant=$?
set -e
test "$mutant" -ne 0
grep -q SAFE_LAND_LATENCY_MUTANT run/unlanded_mutant_FAIL.log
printf 'SAFE_LAND_DIAGNOSTIC: eligible and reset PASS; actual different-rate miss FAIL retained; unlanded mutant rejected\n'
