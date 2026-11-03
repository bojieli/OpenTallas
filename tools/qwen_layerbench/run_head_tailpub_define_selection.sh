#!/usr/bin/env bash
# Codex B-pilot bench, rc16 PART1, canonical-event selection +define+OT_QWEN_HEAD_TAILPUB:
# tile0 (q0, nout768) must PASS unchanged; tile639 (q4, nout560) now publishes only slots 0..2 of each K, so the
# unchanged raw-64 bench (which counts published words as raw ordinals) must fail at published word 3 with the
# value of raw ordinal 8 (K1 slot0, genuine nonzero) where it expects raw ordinal 3 (slot3, padding zero).
set -euo pipefail
cd "$(dirname "$0")"
sha256sum -c SHA256SUMS > hash_guard.log
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$VL" --binary --timing -O0 -finline --output-groups 16 -j 4 --build-jobs 4 -CFLAGS '-O0 -w -fno-var-tracking' \
 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD +define+OT_QWEN_HEAD_TAILPUB --top-module tb_native_head_B_pilot \
 -f source.f native_head_rom_return_cut.sv tb_native_head_B_pilot.sv --Mdir objd > build_define.log 2>&1
(cd contexts/tile0 && ../../objd/Vtb_native_head_B_pilot +TILE=0 > define_tile0.log 2>&1; grep -q 'PASS_NATIVE_B_PILOT tile=0 ' define_tile0.log)
set +e
(cd contexts/tile639 && ../../objd/Vtb_native_head_B_pilot +TILE=639 > define_tile639.log 2>&1); rc=$?
set -e
test "$rc" -ne 0
act=$(sed -n 's/.*PART1_RAW mismatch tile=639 ordinal=3 actual=\([0-9a-f]*\) expected=.*/\1/p' contexts/tile639/define_tile639.log)
test -n "$act"; test "$act" = "$(sed -n 9p contexts/tile639/raw_prefix_expected.hex)"
test "$(sed -n 4p contexts/tile639/raw_prefix_expected.hex | tr -d 0)" = ""
echo PASS_DEFINE_SELECTION tile0_unchanged tile639_published_word3_is_raw_ordinal8
