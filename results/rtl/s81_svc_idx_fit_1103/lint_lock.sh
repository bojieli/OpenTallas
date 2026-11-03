#!/usr/bin/env bash
# lint-only of the lockstep bench (same sources as run_lock.sh); usage: lint_lock.sh OUT
P=results/rtl/s81_svc_idx_fit_1103
sed '/^if \[ ! -x/,$d' $P/run_lock.sh > "$1/gen.sh"
source "$1/gen.sh" "$1"
"$VL" --lint-only -Wno-fatal -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-TIMESCALEMOD -Wno-BLKSEQ -Wno-INITIALDLY \
  --top-module tb_dsdv_idx_rg3 +define+S81CTRL_NATIVE32 -GSRAM_MACRO=1 "${SRC[@]}" > "$1/lint.log" 2>&1
grep -E '%Error|%Warning-(PINMISSING|IMPLICIT|SELRANGE|PINNOTFOUND)' "$1/lint.log" | head -20; echo LINT_DONE
