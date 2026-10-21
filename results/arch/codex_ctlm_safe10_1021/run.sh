#!/bin/bash
set -euo pipefail
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version
verilator --binary --timing -j 8 -Wno-fatal --top-module tb_qfd_tt_ctlm_dv_lpf_lp -f safe10.f --Mdir obj > build.log 2>&1 || { tail -n 30 build.log; exit 3; }
X=obj/Vtb_qfd_tt_ctlm_dv_lpf_lp
$X +MUT=0 +SEED=5 +CALRDIR=2 +CALR_ROM_DIR=calr10 > tok_rel.log 2>&1
grep -q 'LP_LOCKSTEP PASS.*calrdir=2' tok_rel.log
grep -q 'TLOAD_PRODUCER PASS' tok_rel.log
$X +MUT=0 +SEED=5 +CALRDIR=2 +CALR_ROM_DIR=calr10n > tok_norel.log 2>&1 || true
grep -q 'TLOAD_PRODUCER FAIL' tok_norel.log
$X +MUT=0 +SEED=5 +CALRDIR=2 +CALR_ROM_DIR=calr10a > tok_abs1.log 2>&1 || true
grep -q 'TLOAD_PRODUCER FAIL' tok_abs1.log
verilator --binary --timing -j 8 -Wno-fatal --top-module tb_qfd_tt_ctlm_dv_lpf_lp -GCALMUT=35 -f safe10.f --Mdir obj_drop17 > build_drop17.log 2>&1 || { tail -n 30 build_drop17.log; exit 3; }
obj_drop17/Vtb_qfd_tt_ctlm_dv_lpf_lp +MUT=0 +SEED=5 +CALRDIR=2 +CALR_ROM_DIR=calr10 > tok_drop17.log 2>&1 || true
grep -q 'TLOAD_PRODUCER FAIL' tok_drop17.log
printf 'SAFE10_MIN_PRODUCER PASS tok_rel norel_caught abs1_caught drop17_caught\n'
