#!/bin/bash
set -euo pipefail
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version
verilator --binary --timing -j 8 -Wno-fatal --top-module tb_qfd_tt_ctlm_dv_lpf_lp -f safe11.f --Mdir obj > build.log 2>&1 || { tail -n 30 build.log; exit 3; }
X=obj/Vtb_qfd_tt_ctlm_dv_lpf_lp
$X +MUT=0 +SEED=73521 > random_pass.log 2>&1
grep -q 'LP_LOCKSTEP PASS' random_pass.log
$X +MUT=1 +SEED=73521 > mutant_fail.log 2>&1 || true
grep -q 'LP_LOCKSTEP FAIL' mutant_fail.log
$X +MUT=0 +SEED=5 +CALRDIR=2 +CALR_ROM_DIR=calr10 > producer_pass.log 2>&1
grep -q 'LP_LOCKSTEP PASS' producer_pass.log
grep -q 'TLOAD_PRODUCER PASS' producer_pass.log
printf 'SAFE11_MIN_LOCKSTEP PASS random producer mutant_caught\n'
