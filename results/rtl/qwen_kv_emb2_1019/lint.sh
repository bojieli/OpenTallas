#!/bin/bash
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
D=$(cd "$(dirname "$0")" && pwd); S=$D/src/rtl/qwen_sys/static_embedding_20261014
"$VL" --lint-only -Wall -Wno-fatal -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Wno-PINCONNECTEMPTY --top-module qkd_kvs_emb_ctx \
  "$D/src/physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v" \
  $S/qkd_embedding_row_tx.sv $S/qkd_embedding_ctx_start.sv $S/qkd_embedding_static_join.sv $S/qkd_embedding_static_join4.sv \
  $S/qkd_embedding_static_join4_cal.sv $S/qkd_kvs_emb_ctx.sv 2>&1 | grep -v "^ " | grep -E "%(Error|Warning)" | grep -E "ctx" ; echo "lint rc=${PIPESTATUS[0]}"
