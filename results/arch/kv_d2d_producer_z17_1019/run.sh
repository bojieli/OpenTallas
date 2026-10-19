#!/bin/bash
set -euo pipefail
R=$(pwd); O=$R/results/arch/kv_d2d_producer_z17_1019
mkdir -p "$O/out"
SRC=(rtl/lib/ot_rst_pipe.sv rtl/qwen_sys/split_20261014/ot_qwen_crc_parallel.sv rtl/qwen_sys/split_20261014/ot_qwen_static_slot_link.sv rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv rtl/qwen_sys/split_20261014/qkd_native_attention_record.sv rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_static.sv rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_services.sv rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies.sv rtl/qwen_sys/d2d_static_20261015/qkd_d2d_static_z17.sv rtl/qwen_split/qfd_kvn_static_transport.sv physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy/ot_qkvd_ucie_x64_phy_model.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v)
sha256sum "${SRC[@]}" "$O"/{build.py,tb_z17_equiv.sv,tb_z17_boundary.sv} tools/qwen_split/d2d_link_calendar.py > "$O/out/dependencies.sha256"
for pr in 0 1; do
 out=$O/out/pr$pr; mkdir -p "$out"
 args=(); if [ "$pr" = 1 ]; then args+=(--pinreg); fi
 python3 tools/qwen_split/d2d_link_calendar.py --out "$out/cal" --txl 6 --phy 5 --profile dies_token --txd-c 1,2,1,2 --txd-k 1,2,1,1 "${args[@]}" > "$out/calendar.log"
 sha256sum "$out"/cal/* > "$out/calendar.sha256"
 iverilog -g2012 -I"$out/cal" -DOT_MEM_NO_INIT -s tb_qwen_d2d_dies -Ptb_qwen_d2d_dies.PR=$pr -Ptb_qwen_d2d_dies.CALDIR=\"$out/cal\" -o "$out/tb.vvp" "${SRC[@]}" "$O/tb_z17_equiv.sv" > "$out/build.log" 2>&1
 vvp -n "$out/tb.vvp" > "$out/run.log" 2>&1
 grep '^D2D_DIES_PASS' "$out/run.log"
 grep '^Z17_EQ_PRED_PASS' "$out/run.log"
done
iverilog -g2012 -DOT_MEM_NO_INIT -s tb_z17_boundary -o "$O/out/boundary.vvp" "${SRC[@]}" "$O/tb_z17_boundary.sv" > "$O/out/boundary.build.log" 2>&1
vvp -n "$O/out/boundary.vvp" > "$O/out/boundary.log" 2>&1
grep '^Z17_BOUNDARY_PASS' "$O/out/boundary.log"
# Causal mutant: omit reserved word-0 bit 19 from Z0.
sed 's/c_rx_payload\[31:19\]/c_rx_payload[31:20]/' rtl/qwen_sys/d2d_static_20261015/qkd_d2d_static_z17.sv > "$O/out/mutant.sv"
MSRC=(); for p in "${SRC[@]}"; do if [[ "$p" == *qkd_d2d_static_z17.sv ]]; then MSRC+=("$O/out/mutant.sv"); else MSRC+=("$p"); fi; done
iverilog -g2012 -DOT_MEM_NO_INIT -s tb_z17_boundary -o "$O/out/mutant.vvp" "${MSRC[@]}" "$O/tb_z17_boundary.sv" > "$O/out/mutant.build.log" 2>&1
if vvp -n "$O/out/mutant.vvp" > "$O/out/mutant.log" 2>&1; then echo 'MUTANT_UNCAUGHT'; exit 1; fi
grep 'Z17_BOUNDARY_FAIL reset0 bit19' "$O/out/mutant.log"
echo PRODUCER_Z17_PASS
