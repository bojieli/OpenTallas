#!/usr/bin/env bash
# Q-FUNC join960 scale-ROM ABI: build once (positive + MUT), sweep the single fixed latency on rank0, then all ranks.
# usage (inside ot-run): run_join960_scale_abi.sh SRC_ROOT IMAGES(released_masks_v2) OUT
set -uo pipefail
src=${1:?}; img=${2:?}; out=${3:?}
v=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
mkdir -p "$out"
rtl=("$src/rtl/test/qwen_split/tb_join960_scale_abi.sv" "$src/rtl/qwen_split/qfd_port_tiles.sv" "$src/rtl/qwen_split/qfd_slab_result_half.sv"
 "$src/rtl/qwen_split/qfd_slab_word_half.sv" "$src/rtl/hdc/ot_hdc_prefix.sv" "$src/rtl/hdc/ot_hdc_fastfp.sv" "$src/rtl/hdc/ot_qwen_me_spine_h_w12.sv"
 "$src/rtl/physical/ot_qwen_slab_port_group.sv" "$src/rtl/hdc/ot_hdc_sfu.sv" "$src/rtl/hdc/ot_qwen_w12_matvec.sv" "$src/rtl/hdc/ot_qwen_w12_arith.sv"
 "$src/physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v")
sha256sum "${rtl[@]}" "$0" > "$out/source.sha256"
for mut in 0 1; do
 "$v" --binary --timing -j 16 -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -I$src/rtl/hdc --top-module tb_join960_scale_abi \
   -GMUT=$mut --Mdir "$out/obj$mut" "${rtl[@]}" > "$out/build$mut.log" 2>&1 || { tail -20 "$out/build$mut.log"; exit 1; }
done
B=$out/obj0/Vtb_join960_scale_abi
for lat in 7 8 9 10 11 12; do ( "$B" +OT_ROM_DIR=$img/rank0/masks +EXPECTED=$img/rank0/expected_scale_words.hex +LAT=$lat > "$out/sweep_lat$lat.log" 2>&1 ) & done; wait
grep -H -E "^(PASS|FAIL)" $out/sweep_lat*.log
L=$(grep -l "^PASS" $out/sweep_lat*.log | sed 's/.*lat\([0-9]*\).log/\1/' | head -1)
[ -n "$L" ] || { echo "NO fixed latency passes"; exit 1; }
echo "FIXED_LATENCY $L"
for r in 0 1 2 3 4 5 6 7; do ( "$B" +OT_ROM_DIR=$img/rank$r/masks +EXPECTED=$img/rank$r/expected_scale_words.hex +LAT=$L > "$out/rank$r.log" 2>&1 ) & done
( "$out/obj1/Vtb_join960_scale_abi" +OT_ROM_DIR=$img/rank0/masks +EXPECTED=$img/rank0/expected_scale_words.hex +LAT=$L > "$out/mut_slot_swap.log" 2>&1 ) &
( "$B" +OT_ROM_DIR=$img/rank1/masks +EXPECTED=$img/rank0/expected_scale_words.hex +LAT=$L > "$out/mut_wrong_rank_masks.log" 2>&1 ) &
wait
grep -H -E "^(PASS|FAIL)" $out/rank*.log $out/mut_*.log
ok=1; for r in 0 1 2 3 4 5 6 7; do grep -q "^PASS" $out/rank$r.log || ok=0; done
grep -q "^FAIL" $out/mut_slot_swap.log || ok=0; grep -q "^FAIL" $out/mut_wrong_rank_masks.log || ok=0
echo "ALL_OK $ok"; [ $ok = 1 ]
