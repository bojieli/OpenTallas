#!/bin/bash
# Only controller/storage mechanisms, never an actual SU datapath or full layer.
set -eu
out=$1
mode=$2
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
rtl=rtl/physical/ot_qfd_native59_retained_partition_candidate.sv
extra=()
mkdir -p "$out"
if [ "$mode" = rank ]; then
    extra=(-GRANKMUT=1)
elif [ "$mode" = late ]; then
    python3 - "$rtl" "$out/late_bank.sv" <<'PY'
from pathlib import Path
import sys
s=Path(sys.argv[1]).read_text()
s=s.replace('    reg [63:0] rows [0:63];', '    reg [63:0] rows [0:63];\n    reg late_valid; reg [11:0] late_addr;\n    always @(posedge clk) begin late_valid <= read_valid; late_addr <= read_addr; end')
old='if (read_valid) read_data <= (read_addr < 64) ? rows[read_addr[5:0]] : 64\'d0;'
assert s.count(old)==1
s=s.replace(old, 'if (late_valid) read_data <= (late_addr < 64) ? rows[late_addr[5:0]] : 64\'d0;')
Path(sys.argv[2]).write_text(s)
PY
    rtl=$out/late_bank.sv
else
    test "$mode" = positive
fi
src=(rtl/test/tb_qfd_native59_retained_partition.sv "$rtl"
    rtl/physical/ot_qfd_seq_su_bi_native8_tag59_candidate.sv
    rtl/physical/ot_qwen_tp_seq_w12_vrl_native59.sv
    rtl/physical/ot_qfd_stage_gate_native_epoch.sv
    rtl/qwen_sys/redesign_qwen/ot_qfd_seq_su_bi.sv rtl/rom/ot_qwen_tp_seq_w12.sv
    rtl/rom/ot_rom_pkg_link.sv rtl/rom/ot_rom_pkg_ctrl.sv
    rtl/qwen_sys/missing_masters_20261007/ot_qfd_spine_masters.sv
    rtl/qwen_sys/missing_masters_20261007/ot_qfd_split_exact.sv
    rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_dyn_ttiles.sv
    rtl/hdc/ot_hdc_qwen_int8_embed_decode.sv rtl/hdc/ot_hdc_cg.sv
    physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v)
"$vl" --binary --timing -j 4 -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD \
    -CFLAGS -O1 --x-assign fast --x-initial fast --top-module tb_qfd_native59_retained_partition \
    -GARCOV=1 -GMINRD=50 -GMINVW=100 "${extra[@]}" --Mdir "$out/obj" "${src[@]}" >"$out/build.log" 2>&1
"$out/obj/Vtb_qfd_native59_retained_partition" >"$out/run.log" 2>&1
if [ "$mode" = positive ]; then
    grep -q '^PASS seq_su_bi_psram' "$out/run.log"
else
    grep -q '^FAIL seq_su_bi_psram' "$out/run.log"
fi
grep -E '^(PASS|FAIL|POSTED_ABI|RANK_ABI)' "$out/run.log"
sha256sum "$rtl" "$out/obj/Vtb_qfd_native59_retained_partition" >"$out/hashes.sha256"
