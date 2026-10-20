#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
out=${1:?OUT};mut=${2:-0};mkdir -p "$out";out=$(cd "$out" && pwd)
v=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
e=rtl/qwen_sys/static_embedding_20261014
python3 - "$out" "$mut" <<'PY'
import pathlib,sys
o=pathlib.Path(sys.argv[1]);m=int(sys.argv[2]);e=pathlib.Path('rtl/qwen_sys/static_embedding_20261014')
s=(e/'qkd_embedding_row_tx_ctx.sv').read_text().replace('module qkd_embedding_row_tx_ctx #(','module qkd_embedding_row_tx_ctx__ot_pr_core #(');(o/'old_core.sv').write_text(s)
s=pathlib.Path('results/rtl/kv_rowctx_native32_1020/baseline/ot_pin_regs_wrapper.v').read_text().replace('module qkd_embedding_row_tx_ctx (','module qkd_embedding_row_tx_ctx_old_view (');(o/'old_view.v').write_text(s)
s=(e/'qkd_kvs_emb_ctx.sv').read_text().replace('module qkd_kvs_emb_ctx #','module qkd_kvs_emb_ctx_bound_reference #').replace('qkd_embedding_row_tx_ctx u_rowtx','qkd_embedding_row_tx_ctx_old_view u_rowtx');(o/'reference.sv').write_text(s)
s=(e/'qkd_kvs_emb_ctx_n32child.sv').read_text()
if m==1:s=s.replace('.fill_token(tok)','.fill_token(tok ^ 18\'d1)')
if m==2:s=s.replace('.emb_tx_payload(rowtx__emb_tx_payload)',".emb_tx_payload(bad_payload)").replace('    wire        st;',"    wire [547:0] bad_payload; assign rowtx__emb_tx_payload=bad_payload ^ 548'd1;\n    wire        st;")
if m==3:s=s.replace('assign emb_fault = cf | jf | rf;','assign emb_fault = cf | jf;')
if m==4:s=s.replace('.PIPE_JOIN(PIPE_JOIN)', '.PIPE_JOIN(0)')
if m==5:s=s.replace('.row_open(row_open), .ctx_v', ".row_open(1'b0), .ctx_v")
assert m==0 or s!=(e/'qkd_kvs_emb_ctx_n32child.sv').read_text()
(o/'dut.sv').write_text(s)
PY
"$v" --binary --timing -O2 -j 4 -Wno-fatal --top-module tb_parent --Mdir "$out/obj" \
 rtl/lib/ot_rst_relay.sv "$e/qkd_embedding_ctx_start.sv" "$e/qkd_embedding_static_join.sv" \
 "$e/qkd_embedding_static_join_fan32.sv" "$e/qkd_embedding_static_join4.sv" "$e/qkd_embedding_static_join4_cal.sv" \
 "$e/qkd_embedding_row_tx_ctx_native32.sv" "$out/old_core.sv" "$out/old_view.v" "$out/reference.sv" "$out/dut.sv" \
 physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v \
 results/rtl/kv_emb_parent_nativechild_1020/tb_parent.sv > "$out/build.log" 2>&1
"$out/obj/Vtb_parent" 2>&1 | tee "$out/run.log"
