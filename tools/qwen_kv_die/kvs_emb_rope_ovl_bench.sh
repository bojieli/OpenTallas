#!/usr/bin/env bash
# usage: OUT [MUT=0]  SQ-KATTN2 10-21 (K.STA.EMB, kit qkd_kvs_emb_rope73_ovl): behavioural bench of the generated RoPE/OVL
# kvs_emb tile (qkd_kvs_emb_rope_ovl) against tb_qkd_kvs_emb_rope_ovl.sv.  MUT (applied to a copy of qkd_kvs_emb_ctx.sv;
# must FAIL): 1 = RoPE sweep one edge early (ROPE_DELAY-3); 2 = RoPE token base 151935; 3 = head-user check removed;
# 4 = KVN fault dropped from emb_fault; 5 = CONTEXT valid not qualified by the admission phase.
# Exit 0 only on "KVS_EMB_ROPE_OVL PASS".  Verilator 5.050 (the closure daemon's version).
set -euo pipefail
cd "$(dirname "$0")/../..";out=${1:?out};m=${2:-0};mkdir -p "$out";out=$(cd "$out"&&pwd);export TMPDIR="$out"
v=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
E=rtl/qwen_sys/static_embedding_20261014
cp $E/qkd_kvs_emb_ctx.sv "$out/qkd_kvs_emb_ctx.sv"
case $m in
 0) ;;
 1) sed -i "s/rope_count<=16'(ROPE_DELAY-2)/rope_count<=16'(ROPE_DELAY-3)/" "$out/qkd_kvs_emb_ctx.sv";;
 2) sed -i "s/18'd151936+{8'd0,accepted_owner/18'd151935+{8'd0,accepted_owner/" "$out/qkd_kvs_emb_ctx.sv";;
 3) sed -i "s/head_rx_user!=i_ctx\[44:43\])ovl_fault<=1/1'b0)ovl_fault<=1/" "$out/qkd_kvs_emb_ctx.sv";;
 4) sed -i "s/if(kvn_ctx_fault)ovl_fault<=1;//" "$out/qkd_kvs_emb_ctx.sv";;
 5) sed -i "s/\.ctx_v(i_ctx\[98\]&&(!OVL||ovl_adm_done))/.ctx_v(i_ctx[98])/; s/\.ctx_observed_v(i_ctx\[97\]&&(!OVL||ovl_adm_done))/.ctx_observed_v(i_ctx[97])/" "$out/qkd_kvs_emb_ctx.sv";;
esac
awk '/^module qkd_kvs_emb_rope_ovl /,/^endmodule/' rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k_hl_mu_ba_n32_pj_rope_ovl.sv > "$out/qkd_kvs_emb_rope_ovl.sv"
[[ $m == 0 ]] || ! cmp -s $E/qkd_kvs_emb_ctx.sv "$out/qkd_kvs_emb_ctx.sv" || { echo "KVS_EMB_ROPE_OVL FAIL mutant $m not applied"; exit 3; }
"$v" --version
"$v" --binary --timing -O1 -j 8 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-PINMISSING -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN \
  --top-module tb_qkd_kvs_emb_rope_ovl --Mdir "$out/obj" \
  physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v rtl/lib/ot_rst_relay.sv \
  $E/qkd_embedding_static_join.sv $E/qkd_embedding_static_join4.sv $E/qkd_embedding_static_join4_cal.sv \
  $E/qkd_embedding_static_join_fan32.sv $E/qkd_embedding_row_tx_rope.sv $E/qkd_embedding_ctx_start.sv "$out/qkd_kvs_emb_ctx.sv" \
  $E/test/tb_qkd_kvs_emb_rope_ovl.sv \
  "$out/qkd_kvs_emb_rope_ovl.sv" \
  > "$out/build.log" 2>&1 || { tail -30 "$out/build.log"; echo "KVS_EMB_ROPE_OVL FAIL build mut=$m"; exit 2; }
"$out/obj/Vtb_qkd_kvs_emb_rope_ovl" > "$out/m$m.log" 2>&1 || true
grep -E '^(MISMATCH|COVER|FAIL|KVS_EMB_ROPE_OVL|INFO)' "$out/m$m.log" | head -12
grep -q '^KVS_EMB_ROPE_OVL PASS' "$out/m$m.log"
