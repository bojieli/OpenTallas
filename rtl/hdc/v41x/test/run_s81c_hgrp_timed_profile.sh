#!/bin/bash
# Run via ot-run from repo root. Actual connected four-head output+reset contract.
set -euo pipefail
out=$1
runner=rtl/hdc/v41x/test/run_s81c_hgrp_load_stage.sh
mkdir -p "$out"
rtl=rtl/hdc/v41x/ot_s81c_attn_hcore.sv
tb=rtl/hdc/v41x/test/tb_s81c_hcore_reset_timed.sv
iverilog -g2012 -s tb -DOT_S81C_HCORE_RST_TIMED -o "$out/reset.vvp" "$tb" "$rtl"
vvp "$out/reset.vvp" > "$out/reset.log"
iverilog -g2012 -s tb -DOT_S81C_HCORE_RSTE -o "$out/reset_mut.vvp" "$tb" "$rtl"
if vvp "$out/reset_mut.vvp" > "$out/reset_mut.log" 2>&1; then echo 'async mutant escaped';exit 1;fi
grep -q 'bad=0' "$out/reset.log"
grep -Eq 'bad=[1-9][0-9]*' "$out/reset_mut.log"
bash "$runner" "$out/pass" 1 OT_S81C_HCORE_CTLA OT_S81C_HCORE_RST_TIMED OT_TB_RST_TIMED > "$out/pass.log" 2>&1
[ "$(grep -c 'S81C_HGRP_BENCH PASS' "$out/pass.log")" = 3 ]
! grep -q 'S81C_HGRP_BENCH FAIL' "$out/pass.log"
bash "$runner" "$out/async_mutant" 1 OT_S81C_HCORE_CTLA OT_S81C_HCORE_RSTE OT_TB_RST_TIMED > "$out/async_mutant.log" 2>&1
[ "$(grep -c 'S81C_HGRP_BENCH FAIL' "$out/async_mutant.log")" = 3 ]
[ "$(grep -Ec 'reset_bad=[1-9][0-9]*' "$out/async_mutant.log")" = 3 ]
echo 'HCORE_TIMED_PROFILE PASS; legacy async assertion mutant CAUGHT'
