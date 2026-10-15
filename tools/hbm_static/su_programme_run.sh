#!/usr/bin/env bash
# Run through ot-run. OUT contains su_programme_compile.py products.
set -euo pipefail
ulimit -c 0
out=$(realpath "$1")
root=$(cd "$(dirname "$0")/../.." && pwd)
vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$vl" --binary --timing -O1 -j "${PROGRAMME_JOBS:-4}" -Wno-fatal --top-module tb --Mdir "$out/obj" \
 "$root/rtl/hbm_accel/generic/adapters/static_su/programme/ot_hbm_su_programme.sv" \
 "$root/physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v" \
 "$out/tb.sv" > "$out/build.log" 2>&1
"$out/obj/Vtb" +DIR="$out" > "$out/positive.log" 2>&1
grep -q 'SU_PROGRAMME PASS' "$out/positive.log"
for mut in DATA ADDR PHASE; do
 set +e
 "$out/obj/Vtb" +DIR="$out" +MUT_$mut > "$out/mut_$mut.log" 2>&1
 rc=$?
 set -e
 if [ "$rc" = 0 ] || ! grep -q 'SU_PROGRAMME FAIL' "$out/mut_$mut.log"; then exit 1; fi
done
echo SU_PROGRAMME_GATE_PASS
