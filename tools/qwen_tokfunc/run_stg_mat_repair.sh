#!/bin/bash
# Necessary STG MAT producer-contract repair on an already built, source-pinned
# Vtb (MU_NU4 SU_LT1). ROOT is a private staged source/fixtures/binary bundle.
# No build is permitted here. Positive scope is STN/VM at the cluster-output cut.
set -euo pipefail
R=$(readlink -f "$1")
test -x "$R/bin/Vtb"
T=$R/tree
W=$R/run
mkdir "$W"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
export DV_LOWER_VFLAGS='-GMU_NU=4 -GSU_LT=1'
bench=$T/rtl/test/qwen_dv/dv_lower_mat_bench.py
job() {
  local name=$1; shift
  mkdir -p "$W/$name/obj_n12"
  ln -s "$R/bin/Vtb" "$W/$name/obj_n12/Vtb"
  python3 "$bench" --work "$W/$name" "$@" > "$W/$name/bench.out" 2>&1
}
mode=${2:-mat}
if [ "$mode" = lm ]; then
  ages=$R/ages.json  # exact calibrated receipt from the same source-pinned Vtb
  test -s "$ages"
  # Retain the positive failure receipt before returning; never run a negative
  # against an already failing positive or hide an outstanding source defect.
  set +e
  job lm --run lm --ages "$ages"
  lm_rc=$?
  set -e
  if [ "$lm_rc" -ne 0 ]; then
    python3 "$T/tools/qwen_tokfunc/collect_mat_repair.py" "$R" --lm-only
    exit "$lm_rc"
  fi
  if job amax_local --run lm --ages "$ages" --mutant amax_local; then
    echo 'UNEXPECTED PASS: local AMAX index instead of global owner index'
    exit 1
  fi
  grep -q '^DV_LOWER_MAT lm FAIL' "$W/amax_local/bench.out"
  python3 "$T/tools/qwen_tokfunc/collect_mat_repair.py" "$R" --lm-only
else
  job calibrate --calibrate
  grep -q '^CALIBRATE OK' "$W/calibrate/bench.out"
  ages=$W/calibrate/stn_ages.json
  for op in qkv gu od; do
    job "$op" --run "$op" --ages "$ages" --fixture "$R/fx/L0_mat_$op.npz"
  done
  if job drop_last_k --run qkv --ages "$ages" --fixture "$R/fx/L0_mat_qkv.npz" --mutant drop_last_k; then
    echo 'UNEXPECTED PASS: missing final k block'
    exit 1
  fi
  grep -q '^DV_LOWER_MAT qkv FAIL' "$W/drop_last_k/bench.out"
  python3 "$T/tools/qwen_tokfunc/collect_mat_repair.py" "$R"
fi
sha256sum "$R/bin/Vtb" "$T/tools/qwen_layerbench/dv_lower_mat.py" "$bench" > "$W/source.sha256"
echo 'STG MAT REPAIR completed; scoped STN/VM/AMAX cut, no upstream MAC/full-token claim'
