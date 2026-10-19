#!/usr/bin/env bash
set -euo pipefail
verilator --version | tee version.log
verilator --version | grep -q 'Verilator 5.050'
verilator --binary --timing -j 2 -Wno-fatal --top-module tb_authority --Mdir obj_pass kva_authority_path.sv tb_authority.sv > build_pass.log 2>&1
./obj_pass/Vtb_authority > pass.log 2>&1
grep -q '^AUTHORITY_CONTROL_PASS paths=18 reset_modes=2 repeat_reset=1$' pass.log
verilator --binary --timing -j 2 -Wno-fatal --top-module tb_authority -GMUT=1 --Mdir obj_unguarded kva_authority_path.sv tb_authority.sv > build_unguarded.log 2>&1
set +e
./obj_unguarded/Vtb_authority > mutant_unguarded.log 2>&1
rc=$?
set -e
if [[ $rc -eq 0 ]] || ! grep -q 'CONTROL_FAIL arbitrary startup mutated transaction' mutant_unguarded.log; then exit 1; fi
sed 's/reg source_known=0;/reg source_known=1;/' kva_authority_path.sv > mutant_early.sv
verilator --binary --timing -j 2 -Wno-fatal --top-module tb_authority --Mdir obj_early mutant_early.sv tb_authority.sv > build_early.log 2>&1
set +e
./obj_early/Vtb_authority > mutant_early.log 2>&1
rc=$?
set -e
if [[ $rc -eq 0 ]] || ! grep -q 'CONTROL_FAIL old-D frontier' mutant_early.log; then exit 1; fi
sed "/reg sampled=0;/a\\ always @(negedge source_rst_n) if(source_known) knowledge = '0;" kva_authority_path.sv > mutant_repeat.sv
verilator --binary --timing -j 2 -Wno-fatal --top-module tb_authority --Mdir obj_repeat mutant_repeat.sv tb_authority.sv > build_repeat.log 2>&1
set +e
./obj_repeat/Vtb_authority > mutant_repeat.log 2>&1
rc=$?
set -e
if [[ $rc -eq 0 ]] || ! grep -Eq 'CONTROL_FAIL (reset erased knowledge|old-D frontier)' mutant_repeat.log; then exit 1; fi
printf '%s\n' 'AUTHORITY_SUITE_PASS healthy=36 guard_mutant=CAUGHT early_mutant=CAUGHT repeat_mutant=CAUGHT' | tee suite.log

iverilog -g2012 -s tb_authority -o four_state kva_authority_path.sv tb_authority.sv > build_four_state.log 2>&1
vvp four_state > four_state.log 2>&1
grep -q AUTHORITY_CONTROL_PASS four_state.log
iverilog -g2012 -s tb_unknown -o unknown kva_authority_path.sv tb_unknown.sv > build_unknown.log 2>&1
vvp unknown > unknown.log 2>&1
grep -q AUTHORITY_UNKNOWN_CONTROL_PASS unknown.log
sed "s/hops='1/hops='x/" tb_authority.sv > tb_xinit.sv
iverilog -g2012 -s tb_authority -o xinit kva_authority_path.sv tb_xinit.sv > build_xinit.log 2>&1
vvp xinit > xinit.log 2>&1
grep -q AUTHORITY_CONTROL_PASS xinit.log
printf '%s\n' 'AUTHORITY_FOUR_STATE_PASS xinit=36 authoritative_X=CAUGHT' | tee four_state_suite.log
