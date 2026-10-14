#!/bin/bash
set -euo pipefail
P=/srv/opentallas-scratch/codex/s81-gather-leaf-v18/ad50382d0/src/rtl/dsrom_sys/s81_ph
sha256sum "$P/ot_s81ph_ret_root_s.sv" "$P/test/tb_s81ph_candidate_reset.sv" > sources.sha256
iverilog -g2012 -s tb_s81ph_candidate_reset -o positive "$P/ot_s81ph_ret_root_s.sv" "$P/test/tb_s81ph_candidate_reset.sv" > build_positive.log 2>&1
vvp positive > run_positive.log 2>&1
grep 'CANDIDATE_RESET PASS6' run_positive.log
iverilog -g2012 -DS81PH_MUT_SELECT_RESET_PHASE -s tb_s81ph_candidate_reset -o mutant "$P/ot_s81ph_ret_root_s.sv" "$P/test/tb_s81ph_candidate_reset.sv" > build_mutant.log 2>&1
if vvp mutant > run_mutant.log 2>&1; then echo 'SELECT_RESET_MUTANT NOT_DETECTED';exit 1;fi
grep 'short async reset missed' run_mutant.log
echo 'SELECT_RESET_MUTANT FAIL_AS_REQUIRED'
