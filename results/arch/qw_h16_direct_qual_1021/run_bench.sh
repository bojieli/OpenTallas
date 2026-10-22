#!/bin/bash
set -euo pipefail
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
python3 qualification/prepare_bench.py --native-dir candidate
mkdir -p runs
bench=rtl/test/qwen_dv/tt_ctlm_prog_h16z_qualification.py
img=results/rtl/qlb_c4b_1018/lmh_cal/codex_r1
# Reuse one imgh build for its causal image mutant; keep old inputs/receipts immutable.
python3 "$bench" --decode 3 --hard 1 --segcal 1 --work runs/img0 --img "$img/img0" > runs/img0.out 2>&1
python3 "$bench" --decode 3 --hard 1 --segcal 1 --work runs/imgh --img "$img/imgh" > runs/imgh.out 2>&1
set +e
python3 "$bench" --decode 3 --hard 1 --segcal 1 --work runs/imgh --img "$img/imgh" --bmut 3 > runs/bmut3.out 2>&1
mut_rc=$?
set -e
test "$mut_rc" -eq 1
grep -q ': PASS 123/123' runs/img0.out
grep -q ': PASS 131/131' runs/imgh.out
grep -q ': FAIL 129/131' runs/bmut3.out
printf 'H16_FULL_IMAGE_SUITE PASS img0=123/123 imgh=131/131 bmut3=caught\n'
