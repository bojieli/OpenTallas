#!/usr/bin/env bash
# Portable immutable packet runner. Source PREP only until parent admission.
set -euo pipefail
cd "$(dirname "$0")"
sha256sum -c SHA256SUMS > hash_guard.log
VL=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
"$VL" --version | tee compiler_version.log
grep -q 'Verilator 5.050' compiler_version.log
export CXX=g++
"$CXX" --version >> compiler_version.log
/usr/bin/time -v "$VL" --binary --timing --build-jobs 1 -j 1 -O0 -finline --output-groups 16 -CFLAGS '-O0 -w -fno-var-tracking' \
  -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD \
  --top-module tb_qwen_native_head_post_two_lane -f files.f --Mdir obj \
  > build.log 2>&1
exe=./obj/Vtb_qwen_native_head_post_two_lane
/usr/bin/time -v "$exe" +INPUT=inputs > baseline.log 2>&1
grep -q 'PASS_NATIVE_POST_COMPONENT_REFERENCE_BOUNDARY' baseline.log
for control in wrongBTAB noNeighbor; do
  set +e
  /usr/bin/time -v "$exe" +INPUT=inputs +CONTROL="$control" > "$control.log" 2>&1
  rc=$?
  set -e
  test "$rc" -ne 0
  if [ "$control" = wrongBTAB ]; then grep -q 'post mismatch' "$control.log"; fi
  if [ "$control" = noNeighbor ]; then grep -q 'watchdog' "$control.log"; fi
  printf 'EXPECTED_FAIL control=%s rc=%s\n' "$control" "$rc"
done
printf 'PASS_NATIVE_POST_GATE baseline_and_two_same_ELF_causal_controls\n'
