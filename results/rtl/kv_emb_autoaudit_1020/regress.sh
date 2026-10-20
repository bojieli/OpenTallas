#!/usr/bin/env bash
set -euo pipefail
out=${1:?OUT};group=${2:?GROUP};mkdir -p "$out"
v=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
E=rtl/qwen_sys/static_embedding_20261014;T=rtl/test/qwen_static_kv;A=results/rtl/kv_emb_autoaudit_1020
if [[ $group == premerge ]];then
 "$v" --binary --timing -O2 -j 4 -Wno-fatal --top-module tb_qkd_kvs_emb_ctx_lockstep --Mdir "$out/obj" rtl/lib/ot_rst_relay.sv   "$E/qkd_embedding_static_join.sv" "$E/qkd_embedding_static_join_fan32.sv" "$E/qkd_embedding_static_join4.sv" "$E/qkd_embedding_static_join4_cal.sv"   "$E/qkd_embedding_row_tx.sv" "$E/qkd_embedding_row_tx_ctx.sv" "$E/qkd_embedding_ctx_start.sv" "$E/qkd_kvs_emb_ctx.sv"   "$A/premerge/qkd_embedding_ctx_start.sv" "$A/premerge/qkd_embedding_static_join4.sv" "$A/premerge/qkd_embedding_static_join4_cal.sv"   "$A/premerge/qkd_kvs_tiles_hroot_ff_k.sv" "$A/tb_default_premerge.sv"   physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v > "$out/build.log" 2>&1
 "$out/obj/Vtb_qkd_kvs_emb_ctx_lockstep" > "$out/run.log" 2>&1
 grep '^KVS_EMB_CTX PASS' "$out/run.log"
elif [[ $group == ctx ]];then
 for m in 0 1 2 3 4;do bash tools/qwen_kv_die/kvs_emb_ctx_bench.sh "$out/m$m" "$m";done
elif [[ $group == calendar ]];then
 python3 tools/qwen_kv_die/kvjc3_pc_chain.py --ctrl-lat 92 --out "$out/model"
 S=rtl/qwen_sys/static_kv_20261014
 for m in 0 3 4 6;do
 "$v" --binary --timing -O1 -j 4 -Wno-fatal --top-module tb_kvjc3_emb_player -DOT_KVJC3_MUT=$m -DOT_KVJC3_DIR=\"$out/model\" --Mdir "$out/m$m-obj"   rtl/lib/ot_rst_relay.sv "$S/qkd_kv_es_fan_root.sv" "$E/qkd_kv_pc_chain_station.sv" "$E/qkd_embedding_static_map.sv" "$E/qkd_static_kv_pc_es_merge.sv"   "$E/qkd_embedding_static_return_head.sv" "$E/qkd_embedding_static_return_hop.sv" "$E/qkd_embedding_static_join.sv"   "$E/qkd_embedding_static_join4.sv" "$E/qkd_embedding_static_join4_cal.sv" "$T/tb_kvjc3_emb_player.sv" > "$out/m$m-build.log" 2>&1
 "$out/m$m-obj/Vtb_kvjc3_emb_player" > "$out/m$m.log" 2>&1 || true
 if [[ $m == 0 ]];then grep '^PASS' "$out/m$m.log";else grep '^FAIL' "$out/m$m.log";fi
 done
fi
