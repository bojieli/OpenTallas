#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
packet=$PWD
sha256sum -c SHA256SUMS > hash_guard.log
for tile in 0 639;do
 for col in 0 1;do
  test "$(readlink "contexts/tile$tile/mask_c$col.viamap.hex")" = "qtile_t${tile}_b4_c${col}.viamap.hex"
 done
done
VL=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
"$VL" --version | tee compiler_version.log
grep -q 'Verilator 5.050' compiler_version.log
export CXX=g++
"$CXX" --version >> compiler_version.log
/usr/bin/time -v "$VL" --binary --timing -O0 -finline --output-groups 16 -j 1 --build-jobs 1 -CFLAGS '-O0 -w -fno-var-tracking' \
 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_native_head_B_pilot \
 -f source.f native_head_rom_return_cut.sv tb_native_head_B_pilot.sv --Mdir obj > build.log 2>&1
for tile in 0 639;do
 (
  cd "contexts/tile$tile"
  /usr/bin/time -v "$packet/obj/Vtb_native_head_B_pilot" +TILE="$tile" > baseline.log 2>&1
  grep -q "PASS_NATIVE_B_PILOT tile=$tile " baseline.log
  sha256sum actual_ROM_transcript_baseline.tsv > actual_ROM_transcript_baseline.sha256
 )
done
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
printf 'PASS_NATIVE_B_PILOT_GATE two_fresh_contexts_and_same_ELF_protocol_controls\n'
