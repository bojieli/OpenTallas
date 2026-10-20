#!/bin/bash
set -uo pipefail
cd "$(dirname "$0")"
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
for mut in 0 1 2 3 4 5 6 7; do
 out=build_${mut};mkdir -p "$out"
 "$VL" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-PINMISSING -Wno-TIMESCALEMOD -Wno-LATCH -Wno-MULTIDRIVEN -Wno-BLKSEQ -Wno-UNOPTFLAT -j 2 -DMUT=$mut --top-module tb_qkd_embedding_ctx_owner_chain -Mdir "$out" -o tb inputs/sram.v inputs/qkd_embedding_row_tx_ctx.sv inputs/qkd_embedding_ctx_start.sv inputs/qkd_context_records.sv inputs/ot_qwen_tp8_token_epoch_allocator_mu.sv inputs/ot_qwen_tp8_token_epoch_allocator.sv inputs/tb_qkd_embedding_ctx_owner_chain.sv > "$out/build.log" 2>&1 || { tail -20 "$out/build.log"; exit 2; }
 "$out/tb" > "mut${mut}.log" 2>&1
 if test "$mut" = 0; then grep -q '^PASS tb_' "mut${mut}.log" && ! grep -q '^FAIL' "mut${mut}.log" || exit 3
 else grep -q '^FAIL' "mut${mut}.log" || exit 4;fi
 grep -E '^(PASS|FAIL)' "mut${mut}.log" | head -4
done
echo EMB3_OWNER_ROW_SUITE_PASS
