#!/bin/bash
# STEWARD-TOK-S81-G9SIM (10-21): lint/elab (--lint-only, same flags as run_dv_slice.sh) of a cut kit, then, only on a
# clean elaboration, the full build + idle run (+NCYC/+TRACE) via the kit's run_dv_slice.sh.  Run under ot-run.
#   g9sim_kit_run.sh <kit dir> <out dir> [plusargs...]      (LINT_ONLY=1: stop after the lint)
set -u
K=$(realpath $1); OUT=$(realpath -m $2); shift 2
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}; TOP=${TOP:-slice_top}
mkdir -p $OUT; cd $K
/usr/bin/time -v -o $OUT/lint.time $VL --lint-only --timing -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN \
  -Wno-UNOPTFLAT -Wno-PINMISSING -Wno-IMPLICIT -Wno-SELRANGE --top-module tb_$TOP -f kit.f tb/tb_$TOP.sv > $OUT/lint.log 2>&1
rc=$?; echo "lint rc $rc" > $OUT/lint.status
grep -c "%Error" $OUT/lint.log >> $OUT/lint.status; grep -m20 "%Error" $OUT/lint.log >> $OUT/lint.status
grep -h "Elapsed\|Maximum resident" $OUT/lint.time >> $OUT/lint.status
[ $rc -eq 0 ] || { cat $OUT/lint.status; exit 3; }
[ "${LINT_ONLY:-0}" = 1 ] && { cat $OUT/lint.status; exit 0; }
bash $K/run_dv_slice.sh $K $OUT "$@"
