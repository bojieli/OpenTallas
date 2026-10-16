#!/bin/bash
# H-NETLIST idxcoll 2026-10-15: IDX key staging through the stack's eight actual HBM service groups into the actual
# scorer over the die's key_lines wiring (tb_idx_key_service) + two mutants.
#   run_idx_key_service.sh <out> [contract.json]
# The wiring is generated from the v16 contract (default: generate it now with tools/hbm_die_v15/full_die_v16.py).
set -euo pipefail
ulimit -c 0
root=$(cd "$(dirname "$0")/../../.." && pwd); cd "$root"
out=$(realpath -m "${1:?out}"); mkdir -p "$out"
contract=${2:-}
if [ -z "$contract" ]; then python3 tools/hbm_die_v15/full_die_v16.py --out "$out/v16" > "$out/v16.log"; contract=$out/v16/contract.json; fi
python3 tools/hbm_die_v15/idx_key_wiring_2210.py "$contract" 0 "$out/idx_key_wiring.svh"
python3 tools/hbm_die_v15/idx_key_images_2210.py --stack 0 --rows 64 --out "$out/images" > "$out/images.json"
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; [ -x "$vl" ] || vl=verilator
d=rtl/hbm_accel/loader/service_native
src=(rtl/lib/ot_reset_sync.sv rtl/lib/ot_rst_relay.sv "$d/ot_hbm_svc_async_fifo.sv" "$d/ot_hbm_svc_prefetch_mapped4_owner.sv"
 "$d/ot_hbm_svc_prefetch_overlap_owner.sv" "$d/ot_hbm_svc_sm8_landing_bank.sv" "$d/ot_hbm_svc_sm4pc_cdc.sv" "$d/ot_hbm_svc_static_sm_packed136.sv"
 "$d/ot_hbm_svc_sm_feed_programmed.sv" "$d/ot_hbm_svc_sm_issuer.sv" "$d/ot_hbm_svc_sm_group.sv" rtl/hbm_accel/sm/static/ot_smh_static_feed.sv
 rtl/hbm_accel/sm/static/ot_smh_calendar_static.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
 physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc.sv
 "$d/ot_hbm_svc_pc_ctrl_leaf.sv" "$d/ot_hbm_svc_pc_ctrl_leaf_cfg.sv" rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc_strap.sv
 "$d/ot_hbm_svc_native_sector_pipeline_leaves.sv" "$d/tb_hbm_svc_command_dram_pipeline_fixture.sv"
 rtl/hbm_accel/index/ot_hbm_idx_score_static.sv rtl/hbm_accel/index/ot_hbm_idx_engine_static.sv rtl/hbm_accel/index/hidx_meta_w25_d123_r0.sv
 rtl/hdc/ot_hdc_delay_rf.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/v41x/ot_hbm_idx_owned_native.sv rtl/hdc/v41x/ot_hdc_v41x_idx_hslice.sv
 rtl/hdc/v41x/ot_hdc_v41x_idx_lat.sv rtl/hdc/v41x/ot_hdc_v41x_idx_arith_lat.sv rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv
 rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv
 rtl/test/hbm_idx_static/tb_idx_key_service.sv rtl/test/hbm_idx_static/engine.vlt)
build(){ "$vl" --hierarchical --binary --timing -j 16 -O1 -Wno-fatal -Wno-lint -Wno-style $1 -I"$out" --top-module tb_idx_key_service \
  --Mdir "$out/$2" -o sim "${src[@]}" > "$out/$2.build.log" 2>&1 || { tail -20 "$out/$2.build.log"; exit 2; }; }
build "" obj
"$out/obj/sim" +IMAGES="$out/images" > "$out/positive.log" 2>&1 || true
grep -E "KEY_SERVICE|TB_IDX" "$out/positive.log" | tail -10
grep -q '^TB_IDX_KEY_SERVICE PASS' "$out/positive.log"
"$out/obj/sim" +IMAGES="$out/images" +OLDTAG > "$out/oldtag_mutant.log" 2>&1 || true
grep -E "^KEY_SERVICE stack" "$out/oldtag_mutant.log" | tail -1
if grep -q '^TB_IDX_KEY_SERVICE PASS' "$out/oldtag_mutant.log"; then echo 'OLDTAG mutant survived'; exit 1; fi
grep -q 'scorer_fault=1' "$out/oldtag_mutant.log"
echo 'KEY_SERVICE_OLDTAG_MUTANT rejected (scorer fault)'
build "-DOT_KEYWIRE_MUT" obj_wire
"$out/obj_wire/sim" +IMAGES="$out/images" > "$out/keywire_mutant.log" 2>&1 || true
grep -E "^KEY_SERVICE stack" "$out/keywire_mutant.log" | tail -1
if grep -q '^TB_IDX_KEY_SERVICE PASS' "$out/keywire_mutant.log"; then echo 'KEYWIRE mutant survived'; exit 1; fi
grep -q 'scorer_fault=1' "$out/keywire_mutant.log"
echo 'KEY_SERVICE_KEYWIRE_MUTANT rejected (scorer fault)'
"$out/obj/sim" +IMAGES="$out/images" +EARLYGO > "$out/earlygo_mutant.log" 2>&1 || true
if grep -q '^TB_IDX_KEY_SERVICE PASS' "$out/earlygo_mutant.log"; then echo 'EARLYGO mutant survived'; exit 1; fi
grep -q 'KEY_SERVICE DUT fault' "$out/earlygo_mutant.log"
echo 'KEY_SERVICE_EARLYGO_MUTANT rejected (issuer missed go slot)'
build "-GFIXED_GO=0" obj_event
"$out/obj_event/sim" +IMAGES="$out/images" > "$out/eventgo_mutant.log" 2>&1 || true
grep -E "^KEY_SERVICE (port|stack)" "$out/eventgo_mutant.log" | tail -9
if grep -q '^TB_IDX_KEY_SERVICE PASS' "$out/eventgo_mutant.log"; then echo 'event-go issuer survived'; exit 1; fi
grep -q 'scorer_fault=1' "$out/eventgo_mutant.log"
echo 'KEY_SERVICE_EVENT_GO rejected (per-SM go skew, scorer fault): FIXED_GO=1 is required'
rm -rf "$out/obj" "$out/obj_wire" "$out/obj_event"
echo 'RUN_IDX_KEY_SERVICE PASS'
