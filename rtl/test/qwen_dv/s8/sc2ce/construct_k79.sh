#!/usr/bin/env bash
# Staging (QC-P5-TIE): git archive 840685653 (claude/qw-s5-scred-1021: rtl/test/qwen_dv/s5_scred2/*, ctlsafe/*, tools/qwen_dv/bound_math_netlist.py,
# tools/textbook_lint.py, rtl/hdc/*, s5 leaves) + rtl/qwen_dv/s5/qfd_dv_s5_sc2_ce.sv; run in openroad/orfs:asap7lock (yosys 0.67) via ot-run.
# The census step needs tools/textbook_lint.py next to it (first run lacked it; re-run = finish step: census, prefix sed, sha).
# QC-P5-TIE: one k79-recipe construction inside openroad/orfs:asap7lock.  Usage: job.sh OUT TOP NAME CHPARAM MAP(0|1)
set -euo pipefail
O=$1; TOP=$2; NAME=$3; CHP=$4; MAP=$5; mkdir -p "$O"
HDC="rtl/hdc/ot_hdc_vreduce.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_sfu_q.sv"
COM="rtl/qwen_dv/s5/qfd_dv_s5_leaves.sv rtl/qwen_dv/s5/qfd_dv_s5_red2.sv rtl/qwen_dv/s5/qfd_dv_s5_red_ring32.sv rtl/qwen_dv/qfd_dv_reset_tree.sv $HDC"
SRC="rtl/qwen_dv/s5/qfd_dv_s5_sc2.sv rtl/qwen_dv/qfd_dv_scalar2.sv"
[[ $TOP == qfd_dv_s5_sc2 ]] || SRC="$SRC rtl/qwen_dv/s5/qfd_dv_s5_sc2_ce.sv"
export XF=--reuse-copies
if [[ $MAP == 1 ]]; then
  bash rtl/test/qwen_dv/s5_scred2/native_k.sh "$O" "$TOP" "$NAME" "$CHP" $SRC $COM
  gunzip -f "$O/mapped.v.gz" 2>/dev/null || true; rm -f "$O/mapped.v"
else
  export CFLAGS="--load-cap 8 --transparent-inverters --retain-mux --shared-helpers --retain-keep --reuse-copies"
  bash rtl/test/qwen_dv/s5_scred2/construct.sh "$O" "$TOP" "$NAME" "$CHP" "" $SRC $COM
fi
sed -i "s/qfd_bmath_/qfd_s2_bmath_/g" "$O/$NAME.sv" "$O/${NAME}_helpers.sv"
sha256sum "$O/$NAME.sv" "$O/${NAME}_helpers.sv" > "$O/final_sha256.txt"; cat "$O/final_sha256.txt"; echo JOB_DONE
