#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 derive.py
mkdir -p run
base='read_verilog -formal -sv inputs/ot_rst_relay.sv generated/gold_view.sv'
prep='prep -top projection_miter; flatten; memory_map; opt; async2sync; dffunmap; opt_clean'
yosys -Q -T -p "$base generated/candidate_view.sv generated/projection_miter.sv; $prep; sat -seq 8 -tempinduct -maxsteps 20 -set-def-inputs -prove mismatch 0 -verify" > run/formal_projection.log 2>&1
grep -q 'Induction step proven: SUCCESS' run/formal_projection.log
set +e
yosys -Q -T -p "$base generated/mutant_view.sv generated/projection_miter.sv; $prep; sat -seq 12 -set-def-inputs -prove mismatch 0 -verify" > run/formal_retained_bit_mutant_FAIL.log 2>&1
formal_mutant=$?
set -e
test "$formal_mutant" -ne 0
grep -Eq 'proof did fail|model found: FAIL' run/formal_retained_bit_mutant_FAIL.log
iverilog -g2012 -s tb_projection -o run/lockstep.vvp inputs/ot_rst_relay.sv inputs/ot_hbm_obs_leaf.sv generated/ot_hbm_obs_leaf_fc136.sv generated/tb_projection.sv > run/compile.log 2>&1
vvp run/lockstep.vvp > run/lockstep.log 2>&1
iverilog -g2012 -s tb_projection -o run/mutant.vvp inputs/ot_rst_relay.sv inputs/ot_hbm_obs_leaf.sv generated/mutant_production.sv generated/tb_projection.sv > run/mutant_compile.log 2>&1
set +e
vvp run/mutant.vvp > run/lockstep_retained_bit_mutant_FAIL.log 2>&1
sim_mutant=$?
set -e
test "$sim_mutant" -ne 0
grep -q OBS136_PROJECTION_MISMATCH run/lockstep_retained_bit_mutant_FAIL.log
printf 'OBS136_FINITE_PROJECTION_PASS native_reset4 universal_DUT_initial_state retained136+logical144 induction+lockstep+retained_bit_mutants; producer_constant_lemmas_separate\n'
