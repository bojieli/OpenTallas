#!/usr/bin/env bash
# usage: OUT  SQ-KATTN2 10-21: cycle lockstep of qkd_embedding_row_tx_rope (registered is_hdr/is_rope selects, split
# fill_metadata, pre-compared RoPE token) against its pre-census text (test/qkd_embedding_row_tx_rope_ref.sv): 40 fills
# with 64+1+8 words, random slot schedule, a mid-run reset, then 3000 random edges.  Exit 0 only on "EQ PASS".
set -euo pipefail
cd "$(dirname "$0")/../..";out=${1:?out};mkdir -p "$out";out=$(cd "$out"&&pwd);export TMPDIR="$out"
v=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
E=rtl/qwen_sys/static_embedding_20261014
"$v" --binary --timing -O1 -j 8 -Wno-fatal -Wno-WIDTH -Wno-UNUSED --top-module tb_qkd_embedding_row_tx_rope_eq --Mdir "$out/obj" \
  physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v rtl/lib/ot_rst_relay.sv \
  $E/qkd_embedding_row_tx_rope.sv $E/test/qkd_embedding_row_tx_rope_ref.sv $E/test/tb_qkd_embedding_row_tx_rope_eq.sv > "$out/build.log" 2>&1 \
  || { tail -20 "$out/build.log"; echo "EQ FAIL build"; exit 2; }
"$out/obj/Vtb_qkd_embedding_row_tx_rope_eq" > "$out/eq.log" 2>&1 || true
grep -E '^(DIFF|EQ)' "$out/eq.log" | head -6
grep -q '^EQ PASS' "$out/eq.log"
