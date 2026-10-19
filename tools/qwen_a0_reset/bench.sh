#!/bin/bash
set -euo pipefail
python3 make_bench.py
mkdir -p numeric
V="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
mapfile -t SRC < <(python3 - <<'PY'
import json
for p in json.load(open('tools/ref_tile/specs_q_tile_repack/qfd_tile_nk_rp1_a1.json'))['sources']:
 if not p.endswith('_bb.v'):print(p)
PY
)
EXTRA=(rtl/lib/ot_rst_relay.sv rtl/physical/ot_qwen_tile_lsl_fp1.sv rtl/physical/ot_qwen_tile_node.sv rtl/physical/ot_qwen_tile_romleaf.sv physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v native/candidate.v native/native_cells.v native/tb_numeric.sv)
sha256sum "${SRC[@]}" "${EXTRA[@]}" make_bench.py bench.sh > numeric/source.sha256
"$V" --version > numeric/verilator.txt
"$V" --binary --timing -j 8 -O2 -Wno-fatal -Wno-PINMISSING -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN +define+OT_QWEN_LSL_FP1 --top-module tb_qwen_a0_reset_native -Mdir numeric/obj "${SRC[@]}" "${EXTRA[@]}" > numeric/build.log 2>&1
numeric/obj/Vtb_qwen_a0_reset_native +MUT=0 | tee numeric/run_0.log
grep -q '^A0_RESET_NATIVE_NUMERIC_PASS ' numeric/run_0.log
for mut in 41 42; do
 set +e
 numeric/obj/Vtb_qwen_a0_reset_native +MUT="$mut" > "numeric/run_$mut.log" 2>&1
 rc=$?
 set -e
 [[ "$rc" != 0 ]]
 grep -q 'A0_RESET_TRACE_FAIL\|ROMLEAF_PARENT_NK_NATIVE_FAIL' "numeric/run_$mut.log"
done
printf 'A0_RESET_ALL_PROOFS_PASS\n'
