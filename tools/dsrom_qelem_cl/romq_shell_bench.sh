#!/usr/bin/env bash
# Interface-only proof; real split arithmetic remains covered by qxpq_split_bench.sh olat.
# Run under ot-run. Positive checks both output edges and default bypass, then four mutants.
set -euo pipefail
ulimit -c 0
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
OUT=$(realpath -m "${1:?output directory}")
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
for m in m0 TAG STATUS RESET OUTPUT; do
 mkdir -p "$OUT/$m"
 defs=()
 if [ "$m" != m0 ]; then defs+=("-DOT_ROMQ_SHELL_MUT_$m"); fi
 "$V" --binary --timing -j "${J:-2}" -Wno-fatal "${defs[@]}" --top-module tb_romq_shell --Mdir "$OUT/$m/obj" \
   "$ROOT/tools/dsrom_qelem_cl/fixtures/romq_split_interface_mock.sv" \
   "$ROOT/rtl/v41rom/ot_v41_rom_elem_q_qxpq_w10_gb_shell.sv" "$ROOT/tools/dsrom_qelem_cl/tb_romq_shell.sv" > "$OUT/$m/build.log" 2>&1
 set +e
 "$OUT/$m/obj/Vtb_romq_shell" > "$OUT/$m/run.log" 2>&1
 rc=$?
 set -e
 grep 'ROMQ_SHELL comparisons' "$OUT/$m/run.log"
 if [ "$m" = m0 ]; then
   test "$rc" = 0
   grep -q 'ROMQ_SHELL PASS' "$OUT/$m/run.log"
 else
   test "$rc" != 0
   grep -q 'ROMQ_SHELL FAIL' "$OUT/$m/run.log"
 fi
 echo "$m expected_result PASS (exit $rc)"
done
