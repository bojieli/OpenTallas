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
sha256sum "$R/bin/Vtb" "$T/tools/qwen_layerbench/dv_lower_mat.py" "$bench" > "$W/source.sha256"
echo 'STG MAT REPAIR: qkv/gu/od PASS and missing-last-k FAIL; STN/VM cut only, no upstream MAC/full-token claim'
