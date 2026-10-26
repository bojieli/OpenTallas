#!/bin/bash
# qfd_sp_res_ser (TP8 slot cell, assembled cluster) through the die ports: bit-exact bench, mutants, coverage refusal.
#   bench.sh OUT_DIR [mut 0|1|2] [profile 0|1|2] [bursts 360]
# bursts 40 = coverage-refusal control: rc 1 "FAIL res_ser coverage ..." (exact beats, floors not reached).
# rc 0 "PASS res_ser ..."; mutant: rc 1 "FAIL res_ser mutant detected" when the scoreboard caught it, rc 2 when missed.
set -eu
out=$(mkdir -p "$1" && realpath "$1");mut=${2:-0};profile=${3:-0};bursts=${4:-360}
R=$(cd "$(dirname "$0")/../.." && pwd);cd "$R"
v=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
[ -x "$v" ] || v=verilator
"$v" --binary --timing -j 8 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --top-module tb_sp_res_ser -GMUT="$mut" -GPROFILE="$profile" -GBURSTS="$bursts" -Mdir "$out/obj" rtl/test/res_ser/tb_sp_res_ser.sv rtl/qwen_sys/vm_me_20261008/qfd_sp_res_ser.sv rtl/qwen_sys/vm_me_20261008/ot_qfd_res_tiles.sv rtl/qwen_sys/vm_me_20261008/ot_qfd_res_path.sv rtl/lib/ot_rst_relay.sv physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v > "$out/build.log" 2>&1 || { tail -20 "$out/build.log"; echo "FAIL res_ser build"; exit 3; }
set +e
"$out/obj/Vtb_sp_res_ser" > "$out/run.log" 2>&1
rc=$?
cat "$out/run.log"
if [ "$mut" != 0 ]; then
 if grep -q "MISMATCH" "$out/run.log"; then echo "FAIL res_ser mutant detected"; exit 1; fi
 echo "NEGATIVE_CONTROL_MISSED_OR_CRASHED"; exit 2
fi
grep -q "^PASS res_ser" "$out/run.log" || { grep -q "^FAIL res_ser coverage" "$out/run.log" && echo "COVERAGE_REFUSED" || echo "FAIL res_ser no PASS line (rc $rc)"; exit 1; }
exit "$rc"
