#!/usr/bin/env bash
# usage: OUT [MUT=0]  KV-EMB4 10-19: wiring lockstep of qkd_kvs_emb_ctx (OT_KV_EMB_CTX kvs_emb body) against the
# generated die-bound qkd_kvs_emb + a reference qkd_embedding_ctx_start (tb_qkd_kvs_emb_ctx_lockstep.sv).
# MUT (applied to a copy of qkd_kvs_emb_ctx.sv; must FAIL): 1 = ctx_start row_open disconnected (overlap veto lost);
# 2 = join4_cal start from the raw record valid; 3 = emb_fault drops the row_tx fault; 4 = row_tx fill_token from the epoch.
# Exit 0 only on "KVS_EMB_CTX PASS".  Verilator 5.050 (the closure daemon's version).
set -euo pipefail
cd "$(dirname "$0")/../..";out=${1:?out};m=${2:-0};mkdir -p "$out";out=$(cd "$out"&&pwd);export TMPDIR="$out"
v=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
E=rtl/qwen_sys/static_embedding_20261014
cp $E/qkd_kvs_emb_ctx.sv "$out/qkd_kvs_emb_ctx.sv"
case $m in
 0) ;;
 1) sed -i 's/\.row_open(row_open), \.ctx_v/.row_open(1'"'"'b0), .ctx_v/' "$out/qkd_kvs_emb_ctx.sv";;
 2) sed -i 's/\.start(st), \.cfg_we/.start(i_ctx[98]), .cfg_we/' "$out/qkd_kvs_emb_ctx.sv";;
 3) sed -i 's/assign emb_fault = cf | jf | rf;/assign emb_fault = cf | jf;/' "$out/qkd_kvs_emb_ctx.sv";;
 4) sed -i 's/\.fill_token(tok)/.fill_token({2'"'"'b0, tep})/' "$out/qkd_kvs_emb_ctx.sv";;
esac
[[ $m == 0 ]] || ! cmp -s $E/qkd_kvs_emb_ctx.sv "$out/qkd_kvs_emb_ctx.sv" || { echo "KVS_EMB_CTX FAIL mutant $m not applied"; exit 3; }
"$v" --version
"$v" --binary --timing -O1 -j 8 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-PINMISSING -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-MODMISSING \
  --top-module tb_qkd_kvs_emb_ctx_lockstep --Mdir "$out/obj" \
  physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v \
  $E/qkd_embedding_static_join.sv $E/qkd_embedding_static_join4.sv $E/qkd_embedding_static_join4_cal.sv \
  $E/qkd_embedding_row_tx.sv $E/qkd_embedding_row_tx_ctx.sv $E/qkd_embedding_ctx_start.sv "$out/qkd_kvs_emb_ctx.sv" \
  rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k.sv $E/test/tb_qkd_kvs_emb_ctx_lockstep.sv > "$out/build.log" 2>&1 \
  || { tail -30 "$out/build.log"; echo "KVS_EMB_CTX FAIL build mut=$m"; exit 2; }
"$out/obj/Vtb_qkd_kvs_emb_ctx_lockstep" > "$out/m$m.log" 2>&1 || true
grep -E '^(MISMATCH|COVER|FAIL|KVS_EMB_CTX|INFO)' "$out/m$m.log" | head -8
grep -q '^KVS_EMB_CTX PASS' "$out/m$m.log"
