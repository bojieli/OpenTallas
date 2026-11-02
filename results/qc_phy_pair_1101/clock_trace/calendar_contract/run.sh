#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 derive.py
mkdir -p run
iverilog -g2012 -s tb_calendar_slot -o run/native.vvp inputs/ot_coll_static_linkcal.sv tb_calendar_slot.sv > run/compile.log 2>&1
vvp run/native.vvp +SLOT_EDGE=100 > run/eligible_positive.log 2>&1
set +e
vvp run/native.vvp +SLOT_EDGE=101 > run/unqualified_phase_FAIL.log 2>&1
bad_phase=$?
set -e
test "$bad_phase" -ne 0
grep -q FDI_SLOT_SAMPLE_MISSED run/unqualified_phase_FAIL.log
iverilog -g2012 -s tb_calendar_slot -o run/mutant.vvp generated/mutant_zero_calendar_slot.sv tb_calendar_slot.sv > run/mutant_compile.log 2>&1
set +e
vvp run/mutant.vvp +SLOT_EDGE=100 > run/mutant_zero_slot_FAIL.log 2>&1
mutant=$?
set -e
test "$mutant" -ne 0
grep -q FDI_SLOT_SAMPLE_MISSED run/mutant_zero_slot_FAIL.log
printf 'FDI_CALENDAR_CONTRACT_DIAGNOSTIC: eligible positive PASS; actual unqualified phase FAIL retained; zero-slot mutant rejected\n'
