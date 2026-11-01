#!/bin/bash
set -euo pipefail
WT=${1:?worktree};OUT=${2:?fresh output};REF=${3:?candidate source commit}
[ ! -e "$OUT" ] || { echo 'output must be fresh' >&2; exit 2; }
python3 "$WT/tools/hbm_next/raw_copy/convert_golden.py" "$OUT"
git -C "$WT" show "$REF:rtl/hbm_accel/loader/service_native/split/ot_hbm_svc_vmdel_lane_load_static.sv" > "$OUT/source.sv"
cd "$OUT"
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
verilator --binary --timing -j "${OT_J:-2}" -Wno-fatal --top-module tb_convert_golden source.sv tb_convert_golden.sv --Mdir obj > build.log 2>&1
./obj/Vtb_convert_golden > golden.log 2>&1
set +e
./obj/Vtb_convert_golden +MUT=1 > mutant.log 2>&1
rc=$?
[ "$rc" != 0 ] && grep -q CONVERT_GOLDEN_MISMATCH mutant.log || exit 2
printf 'PASS CONVERT_GOLDEN_816 MUTANT_CAUGHT\n' > status
