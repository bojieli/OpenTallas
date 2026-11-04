#!/usr/bin/env bash
# Review packet only until explicit normal resource release.
set -euo pipefail
cd "$(dirname "$0")"
sha256sum -c SHA256SUMS > hash_guard.log
VL=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
"$VL" --version | tee compiler_version.log
grep -q 'Verilator 5.050' compiler_version.log
export CXX=g++
"$CXX" --version >> compiler_version.log
/usr/bin/time -v "$VL" --binary --timing -O0 -finline --output-groups 16 -j 1 --build-jobs 1 \
 -CFLAGS '-O0 -w -fno-var-tracking' -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD \
 --top-module tb_qwen_native_head_tail_control -f files.f --Mdir obj > build.log 2>&1
exe=./obj/Vtb_qwen_native_head_tail_control
for which in raw8 round16 keep3;do
 /usr/bin/time -v "$exe" +INPUT=inputs +CASE="$which" > "$which.log" 2>&1
 grep -q "PASS_NATIVE_TAIL_CONTROL case=$which " "$which.log"
done
for which in bad3 cfg_between;do
 set +e
 /usr/bin/time -v "$exe" +INPUT=inputs +CASE="$which" > "$which.log" 2>&1
 rc=$?
 set -e
 test "$rc" -ne 0
 if [ "$which" = bad3 ];then
  grep -q 'TAIL_COUNTER_BUG accepted64 selected21_22_23_45_46_47 outputs3' "$which.log"
  grep -q 'EXPECTED_NATIVE_RAW64_NWORDS3_FAULT' "$which.log"
 else
  grep -q 'EXPECTED_NATIVE_CONTIGUOUS_ROUND_CFG_FAULT' "$which.log"
 fi
 printf 'EXPECTED_NATIVE_CONTRACT_FAIL case=%s rc=%s\n' "$which" "$rc"
done
set +e
/usr/bin/time -v "$exe" +INPUT=inputs +CASE=keep3 +MUT_KEEP=1 > wrong_keep_model.log 2>&1
rc=$?
set -e
test "$rc" -ne 0
grep -q 'TAIL_SELECTION mismatch' wrong_keep_model.log
printf 'PASS_NATIVE_TAIL_CONTROL_GATE counter_cfg_witness_and_external_contract_model\n'
