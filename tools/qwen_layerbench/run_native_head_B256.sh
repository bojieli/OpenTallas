#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
packet=$PWD
sha256sum -c SHA256SUMS > hash_guard.log
for tile in {0..127} {512..639};do
 for col in 0 1;do
  test "$(readlink "contexts/tile$tile/mask_c$col.viamap.hex")" = "qtile_t${tile}_b4_c${col}.viamap.hex"
 done
done
VL=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
"$VL" --version | tee compiler_version.log
grep -q 'Verilator 5.050' compiler_version.log
export CXX=g++
"$CXX" --version >> compiler_version.log
# Optional immutable terminal cache is never the live/protected pilot directory.
# Exact manifest, toolchain, make configuration and transitive deps gate copying.
# Missing/rejected reuse leaves normal make to perform the ordinary build.
/usr/bin/time -v "$VL" --cc --exe --main --timing -O0 -finline --output-groups 16 -j 1 --build-jobs 1 -CFLAGS '-O0 -w -fno-var-tracking' \
 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_native_head_B_pilot \
 -f source.f native_head_rom_return_cut.sv tb_native_head_B_pilot.sv --Mdir obj > generation.log 2>&1
if [[ -n "${NATIVE_HEAD_TERMINAL_CACHE:-}" ]];then
 python3 reuse_terminal_objects.py --cache "$NATIVE_HEAD_TERMINAL_CACHE" --obj obj --compiler-log compiler_version.log > cache_reuse.log
fi
/usr/bin/time -v make -C obj -f Vtb_native_head_B_pilot.mk -j 1 > build.log 2>&1
for tile in {0..127} {512..639};do
 (
  cd "contexts/tile$tile"
  /usr/bin/time -v "$packet/obj/Vtb_native_head_B_pilot" +TILE="$tile" > baseline.log 2>&1
  grep -q "PASS_NATIVE_B256_CONTEXT tile=$tile " baseline.log
  sha256sum actual_ROM_RAW_transcript_baseline.tsv > actual_ROM_RAW_transcript_baseline.sha256
 )
done
python3 check_capture.py . > capture_check.log
for control in wrongAddress wrongCycle;do
 (
  cd contexts/tile0
  set +e
  /usr/bin/time -v "$packet/obj/Vtb_native_head_B_pilot" +TILE=0 +CONTROL="$control" > "$control.log" 2>&1
  rc=$?
  set -e
  test "$rc" -ne 0
  grep -q 'ROM_RESPONSE_CONTEXT_ADDRESS_CYCLE mismatch' "$control.log"
  printf 'EXPECTED_FAIL control=%s rc=%s\n' "$control" "$rc"
 )
done
printf 'PASS_NATIVE_B256_GATE 256_fresh_contexts_16384_actual_ROM_RAW_records_and_same_ELF_controls\n'
