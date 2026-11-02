#!/usr/bin/env bash
set -euo pipefail
# Source-generation proposal only, held for current source/ABI capsule review.
[[ ${HG9_SOURCE_CAPSULE_REVIEWED:-0} == 1 ]] || { echo 'PREP ONLY: review current HG9 q1 capsule before GEN' >&2; exit 2; }
REPO=$(git rev-parse --show-toplevel)
P="$REPO/results/hg9_current_q1_1102"
python3 "$P/derive.py"
python3 "$REPO/physical/die_plan/qwen_kvsys/cores/harden/gen_core_kit_kv.py" \
  --core-json "$P/q1_current_core.json" --plan "$P/plan/plan_c.json" \
  --kit-rtl "$P/kit_rtl" --out "${1:?fresh owned source-generation output directory}" \
  --ectlk-face-ports --cts-setup-only --two-mode-grt --hold-ff-margin 10
