#!/bin/bash
# QW-F16SUB port checks (from repo root, `verilator` = 5.050): CALR port bench MUT 0 / 34 / 2, mu_seq lockstep m0 (default
# CALENDAR_ROM 0 unchanged), CTLM lpf lint F16WTN=1 PRIVATE_CALR=1 and default.
set -uo pipefail
O=${1:?outdir}; mkdir -p $O
for m in 0 34 2; do ( bash rtl/test/qwen_dv/calr_port/run_calr_port.sh $O/calr_m$m $m > $O/calr_m$m.log 2>&1; echo "rc=$?" >> $O/calr_m$m.log ) & done
( python3 rtl/test/mu_qwen_seq/mu_seq_bench.py --work $O/mu_seq_m0 --mut 0 --jobs 8 > $O/mu_seq_m0.log 2>&1; echo "rc=$?" >> $O/mu_seq_m0.log ) &
F=$(cat rtl/test/qwen_dv/calr_port/ctlm_lpf_files.txt)
P="--lint-only -Wno-fatal -Wno-WIDTH -Wno-UNUSED --top-module qfd_tt_ctlm_dv_lpf -GXPF_TRANSPORT_EDGES=20 -GSTAGE_ME=1 -GLAST_STAGE=37 -GNU=4 -GOPSEG=1 -GCTX_SRC=1 -GFCTX=1 -GOPSEG_EXPANDED=1 -GINIT_U0=1 -GINIT_FIRST=52 -GINIT_CNT=3 -GOPSEG_PINREG=1"
( verilator $P -GPRIVATE_CALR=1 -GF16WTN=1 $F > $O/lint_f16calr.log 2>&1 && echo CTLM_F16_CALR_ELAB_PASS >> $O/lint_f16calr.log || echo CTLM_F16_CALR_ELAB_FAIL >> $O/lint_f16calr.log ) &
( verilator $P $F > $O/lint_default.log 2>&1 && echo CTLM_DEFAULT_ELAB_PASS >> $O/lint_default.log || echo CTLM_DEFAULT_ELAB_FAIL >> $O/lint_default.log ) &
wait
for f in $O/*.log; do echo "== $(basename $f)"; grep -E 'CALR_PORT_(PASS|FAIL|SUMMARY|EDGE_MISMATCH|BUILD_FAIL|TIMEOUT)|ELAB_(PASS|FAIL)|%Error|PASS|FAIL|rc=' $f | head -8; done
