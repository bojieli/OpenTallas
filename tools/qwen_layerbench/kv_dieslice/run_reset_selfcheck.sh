#!/bin/bash
# run_reset_selfcheck.sh GENERATED_SOURCE.sv OUT; builds via the caller's ot-run.
set -eu
S=$(readlink -f "$1"); O=$(mkdir -p "$2" && readlink -f "$2")
H=$(cd "$(dirname "$0")" && pwd); R=$(cd "$H/../../.." && pwd)
mkdir -p "$O/original" "$O/patched"
cp "$S" "$O/original/qkd_kv_ctl_nc32_face.sv"
cp "$S" "$O/patched/qkd_kv_ctl_nc32_face.sv"
python3 "$H/reset_selfcheck_guard.py" "$O/patched"
python3 "$H/reset_selfcheck_guard.py" "$O/patched" # idempotence
cd "$O"
for mode in original patched; do
 for m in 0 1; do
  if [ "$mode" = original ] && [ "$m" = 1 ]; then continue; fi
  verilator --binary --timing --x-initial unique -Wno-fatal --top-module tb_nc32_reset_selfcheck -GMUT=$m --Mdir "${mode}_m${m}" -j 1 "$mode/qkd_kv_ctl_nc32_face.sv" "$R/rtl/test/qwen_static_kv/tb_nc32_reset_selfcheck.sv" > "${mode}_m${m}.build.log" 2>&1
  set +e
  "./${mode}_m${m}/Vtb_nc32_reset_selfcheck" +verilator+rand+reset+2 > "${mode}_m${m}.run.log" 2>&1
  status=$?
  set -e
  cat "${mode}_m${m}.run.log"
  if [ "$mode" = patched ] && [ "$m" = 0 ]; then test "$status" = 0
  else test "$status" != 0; grep -q 'E-face copy differs' "${mode}_m${m}.run.log"; fi
 done
done
