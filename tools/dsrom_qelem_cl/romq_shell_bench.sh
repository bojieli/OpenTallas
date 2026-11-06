#!/usr/bin/env bash
# Interface-only proof; real split arithmetic remains covered by qxpq_split_bench.sh olat.
# Run under ot-run. Positive checks both output edges and default bypass, then four mutants.
set -euo pipefail
ulimit -c 0
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
OUT=$(realpath -m "${1:?output directory}")
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
IN_STAGES=${IN_STAGES:-1}; OUT_STAGES=${OUT_STAGES:-1}; INPUT_PAIR=${INPUT_PAIR:-0}
[[ "$IN_STAGES" =~ ^[1-9][0-9]*$ && "$OUT_STAGES" =~ ^[1-9][0-9]*$ ]] || { echo "positive stage counts required" >&2; exit 2; }
(( IN_STAGES + OUT_STAGES < 16 )) || { echo "bench history supports total stages <16" >&2; exit 2; }
[[ "$INPUT_PAIR" = 0 || "$INPUT_PAIR" = 1 ]] || { echo "INPUT_PAIR must be0/1" >&2; exit 2; }
(( IN_STAGES > INPUT_PAIR )) || { echo "at least one outer rising stage required" >&2; exit 2; }
mutants="m0 TAG STATUS RESET OUTPUT"
if [ "$INPUT_PAIR" = 1 ]; then mutants="$mutants E_AGE E_NEG E_TAG"; fi
for m in $mutants; do
 mkdir -p "$OUT/$m"
 defs=()
 case "$m" in m0) ;; E_*) defs+=("-DOT_ROMQ_PAIR_MUT_$m");; *) defs+=("-DOT_ROMQ_SHELL_MUT_$m");; esac
 "$V" --binary --timing -j "${J:-2}" -Wno-fatal "${defs[@]}" -GPAIR_INPUT="$INPUT_PAIR" -GIN_STAGES="$IN_STAGES" -GOUT_STAGES="$OUT_STAGES" --top-module tb_romq_shell --Mdir "$OUT/$m/obj" \
   "$ROOT/tools/dsrom_qelem_cl/fixtures/romq_half_interface_mock.sv" \
   "$ROOT/rtl/v41rom/ot_v41_rom_elem_q_qxpq_w10_gb_split.sv" \
   "$ROOT/tools/dsrom_qelem_cl/fixtures/romq_split_reference.sv" \
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
