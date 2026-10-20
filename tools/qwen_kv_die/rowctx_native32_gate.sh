#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
out=${1:?OUT};m=${2:-0};mkdir -p "$out";out=$(cd "$out" && pwd)
v=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
python3 - "$out" <<'PY'
import pathlib,sys
p=pathlib.Path(sys.argv[1]);b=pathlib.Path('rtl/qwen_sys/static_embedding_20261014/qkd_embedding_row_tx_ctx.sv').read_text().replace('module qkd_embedding_row_tx_ctx #(','module qkd_embedding_row_tx_ctx__ot_pr_core #(');(p/'old_core.sv').write_text(b)
b=pathlib.Path('results/rtl/kv_rowctx_native32_1020/baseline/ot_pin_regs_wrapper.v').read_text().replace('module qkd_embedding_row_tx_ctx (','module qkd_embedding_row_tx_ctx_old_view (');(p/'old_view.v').write_text(b)
PY
"$v" --binary --timing -O2 -j 4 -Wno-fatal --top-module tb_rowctx_native32 -DMUT="$m" --Mdir "$out/obj" rtl/lib/ot_rst_relay.sv rtl/qwen_sys/static_embedding_20261014/qkd_embedding_row_tx_ctx_native32.sv "$out/old_core.sv" "$out/old_view.v" physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v results/rtl/kv_rowctx_native32_1020/tb_rowctx_native32.sv > "$out/build.log" 2>&1
"$out/obj/Vtb_rowctx_native32" 2>&1 | tee "$out/run.log"
