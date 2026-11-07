#!/bin/bash
# Usage: bash run.sh CANDIDATE_CA YOUR_OWN_REPO
# Alternative exported baseline: BASELINE_ROOT=/source@93c... bash run.sh CANDIDATE_CA
# All compilation/simulation must be invoked through ot-run, e.g. --mem8 --threads4.
set -uo pipefail
cd "$(dirname "$0")" || exit 90
CANDIDATE_CA=${1:-patched_ca.sv}
if test -n "${BASELINE_ROOT:-}"; then
  python3 -I prepare_reference.py --baseline-root "$BASELINE_ROOT" --candidate "$CANDIDATE_CA" || exit $?
else
  test -n "${2:-}" || { echo "Pass your own git repo as argument2, or set BASELINE_ROOT" >&2; exit 89; }
  python3 -I prepare_reference.py --repo "$2" --candidate "$CANDIDATE_CA" || exit $?
fi
run_case() {
  local tag=$1 bench=$2 mutant=$3
  docker run --rm --memory=8g --cpus=4 -v "$PWD:/proof" -w /proof verilator/verilator:v5.032 \
    --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb \
    --Mdir "obj_${tag}_pass" -o tbx "$bench" patched_ca.sv rtl/ca_reference.sv \
    rtl/ot_meso_fifo.sv rtl/ot_dp_clk_landing.sv > "${tag}_build_pass.log" 2>&1 || return $?
  stdbuf -oL -eL "./obj_${tag}_pass/tbx" +seed=11 +n=120 > "${tag}_pass.log" 2>&1 || return $?
  grep -q ' PASS$' "${tag}_pass.log" || return 93
  docker run --rm --memory=8g --cpus=4 -v "$PWD:/proof" -w /proof verilator/verilator:v5.032 \
    --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style "+define+$mutant" --top-module tb \
    --Mdir "obj_${tag}_mutant" -o tbx "$bench" patched_ca.sv rtl/ca_reference.sv \
    rtl/ot_meso_fifo.sv rtl/ot_dp_clk_landing.sv > "${tag}_build_mutant.log" 2>&1 || return $?
  stdbuf -oL -eL "./obj_${tag}_mutant/tbx" +seed=11 +n=120 > "${tag}_mutant.log" 2>&1
  local rc=$?
  test "$rc" != 0 || { echo "$tag MUTANT SURVIVED"; return 94; }
  if grep -q 'DIFF mode=' "${tag}_mutant.log"; then
    echo "$tag PASS + MUTANT_CAUGHT_OUTPUT_DIFF"
  elif test "$tag" = freg && grep -q 'ready_checks=0 errors=0 zero_delay_diffs=0 FAIL' "${tag}_mutant.log"; then
    # FREG mutant corrupts its start frame: never ready, violating the directed
    # legal-window cases. Baseline PASS above requires positive ready coverage.
    echo "$tag PASS + MUTANT_CAUGHT_READY_LOSS"
  else
    echo "$tag mutant failed without an expected observable cause"; return 95
  fi
  tail -n 5 "${tag}_pass.log"
  tail -n 7 "${tag}_mutant.log"
}
run_case chunk tb.sv OT_MESO_CA_MUTANT_WREG || exit $?
run_case freg tb_freg.sv OT_MESO_CA_MUTANT_FREG || exit $?
echo "WRITER_CHUNK_AND_PIN_CYCLE_PROOF PASS"
