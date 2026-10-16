#!/bin/bash
# Full-shape production bench of the pin-registered IDX tiles (H-NETLIST/idxreg 2026-10-16): compiler programme ->
# calendar SRAM -> ot_hbm_idx_scheduled_static parent (vm_query/query/4 scorers/selector/topk link), real VM banks.
# PASS: registered programme at GAP 100 (the compiler default) and GAP 4, exact scores/records/flits AND the exact
# compiled timeline (first key and first TX edge = compiler prediction + the calendar's start->issue 3 edges).
# Mutants that must FAIL: 1 query index, 2 key bit, 3 link flush one edge early, PINS0 = the historical
# unregistered programme (--pins none) on the registered tiles.
# Usage: run_scheduled.sh OUT
set -euo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd)
cd "$root"
out=$(realpath -m "${1:-/tmp/hbm-idx-scheduled-proof}")
mkdir -p "$out/vec"
OPENBLAS_NUM_THREADS=1 python3 tools/hbm_idx_static_parent_vectors.py "$out/vec" > "$out/vectors.log"
for c in reg100:registered:100 reg4:registered:4 none100:none:100; do
 IFS=: read -r tag pins gap <<< "$c"
 python3 tools/hbm_idx_static_calendar.py "$out/cal_$tag" --pins "$pins" --gap "$gap" > "$out/cal_$tag.log"
done
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
[ -x "$vl" ]||vl=verilator
src=(rtl/hbm_accel/index/ot_hbm_idx_scheduled_static.sv rtl/hbm_accel/index/ot_hbm_idx_calendar_static.sv
 rtl/hbm_accel/index/ot_hbm_idx_parent_static.sv rtl/hbm_accel/index/ot_hbm_idx_vm_query_static.sv rtl/hbm_accel/index/ot_hbm_idx_vm_static.sv
 rtl/hbm_accel/index/hidx_meta_w25_d123_r0.sv rtl/hdc/ot_hdc_delay_rf.sv rtl/hbm_accel/index/ot_hbm_idx_score_static.sv rtl/hbm_accel/index/ot_hbm_idx_engine_static.sv rtl/hbm_accel/index/ot_hbm_idx_selector_static.sv rtl/hbm_accel/index/ot_hbm_idx_topk_link_static.sv
 rtl/hbm_accel/index/ot_hbm_idx_query_static.sv rtl/hbm_accel/index/ot_hbm_idx_query_owned_native.sv rtl/hbm_accel/index/ot_hbm_idx_actquant_owned_native.sv
 rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv
 rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/v41x/ot_hbm_idx_owned_native.sv rtl/hdc/v41x/ot_hdc_v41x_idx_hslice.sv
 rtl/lib/ot_rst_relay.sv rtl/hdc/v41x/ot_hdc_v41x_idx_lat.sv rtl/hdc/v41x/ot_hdc_v41x_idx_arith_lat.sv rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv
 rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
 physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
 physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v
 rtl/test/hbm_idx_static/tb_idx_scheduled_static.sv rtl/test/hbm_idx_static/parent.vlt)
sha256sum "${src[@]}" tools/hbm_idx_static_calendar.py tools/hbm_idx_static_parent_vectors.py rtl/test/hbm_idx_static/run_scheduled.sh > "$out/sources.sha256"
"$vl" --hierarchical --binary --timing -j 8 -O1 -Wno-fatal -Wno-lint -Wno-style --top-module tb_idx_scheduled_static --Mdir "$out/obj" "${src[@]}" > "$out/build.log" 2>&1
pred(){ python3 -c 'import json,sys;p=json.load(open(sys.argv[1]))["predicted"];print(p["first_key_instruction"]+3,p["first_tx_from_instruction0"]+3)' "$1/calendar.json"; }
len(){ python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["length"])' "$1/calendar.json"; }
run(){ # tag caldir mut expect(pass|fail)
 local tag=$1 cal=$2 mut=$3 want=$4 rc
 read -r ek et <<< "$(pred "$cal")"
 mkdir -p "$out/run_$tag"; cp "$out"/vec/*.hex "$out/run_$tag/"; cp "$cal/calendar_instructions.hex" "$out/run_$tag/"
 set +e
 (cd "$out/run_$tag" && "$out/obj/Vtb_idx_scheduled_static" +N="$(len "$cal")" +MUT="$mut" +EXP_KEY="$ek" +EXP_TX="$et") > "$out/run_$tag.log" 2>&1
 rc=$?
 set -e
 grep -E "IDX_SCHEDULED_STATIC|TIMELINE|SCOREBAD|TXBAD|DIAG|fatal|Error" "$out/run_$tag.log" | head -12 | sed "s/^/[$tag] /"
 if [ "$want" = pass ]; then [ "$rc" = 0 ] || { echo "RUN $tag FAILED (expected PASS)"; return 1; }
 else [ "$rc" != 0 ] || { echo "MUTANT $tag SURVIVED"; return 1; }; echo "[$tag] mutant rejected"; fi
}
run pos_gap100 "$out/cal_reg100" 0 pass
run pos_gap4 "$out/cal_reg4" 0 pass
run mut1_query "$out/cal_reg100" 1 fail
run mut2_key "$out/cal_reg100" 2 fail
run mut3_flush "$out/cal_reg100" 3 fail
run mut_pins0 "$out/cal_none100" 0 fail
echo IDX_SCHEDULED_GATE_PASS
