#!/bin/bash
set -uo pipefail
cd "$(dirname "$0")"
iverilog -V 2>&1 | head -2
iverilog -g2012 -s tb_qkd_embedding_ctx_owner_chain -o fourstate.vvp inputs/sram.v inputs/qkd_embedding_row_tx_ctx.sv inputs/qkd_embedding_ctx_start.sv inputs/qkd_context_records.sv inputs/ot_qwen_tp8_token_epoch_allocator_mu.sv inputs/ot_qwen_tp8_token_epoch_allocator.sv inputs/tb_qkd_embedding_ctx_owner_chain.sv > fourstate.build.log 2>&1 || { tail -20 fourstate.build.log;exit 2; }
vvp fourstate.vvp > fourstate.log 2>&1
cat fourstate.log
grep -q '^PASS tb_' fourstate.log && ! grep -q '^FAIL' fourstate.log
