#!/bin/bash
# Q-LINK static D2D link component bench. Usage: run_d2d_static.sh OUT [MUT]
set -eu
OUT=$1; MUT=${2:-0}
W=$(cd "$(dirname "$0")/../.." && pwd); R=$(cd "$W/.." && pwd)
TXL=${TXL:-6}; PHY=${PHY:-5}
mkdir -p "$OUT"
CTXL=$TXL; [ "$MUT" = 4 ] && CTXL=$((TXL-1))
python3 "$R/tools/qwen_split/d2d_link_calendar.py" --out "$OUT/cal" --txl "$CTXL" --phy "$PHY" > "$OUT/calendar.log"
SRC=("$W/qwen_sys/split_20261014/ot_qwen_crc_parallel.sv" "$W/qwen_sys/split_20261014/ot_qwen_static_slot_link.sv"
 "$W/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv" "$W/qwen_sys/split_20261014/qkd_native_attention_record.sv"
 "$W/qwen_sys/d2d_static_20261015/ot_qwen_d2d_static.sv" "$W/qwen_sys/d2d_static_20261015/ot_qwen_d2d_services.sv"
 "$R/physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy/ot_qkvd_ucie_x64_phy_model.sv"
 "$R/physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v"
 "$W/test/qwen_split/tb_qwen_d2d_static.sv")
sha256sum "${SRC[@]}" "$R/tools/qwen_split/d2d_link_calendar.py" > "$OUT/source.sha256"
iverilog -g2012 -DOT_MEM_NO_INIT -s tb_qwen_d2d_static -Ptb_qwen_d2d_static.MUT=$MUT -Ptb_qwen_d2d_static.TXL=$TXL \
 -Ptb_qwen_d2d_static.PHY=$PHY -Ptb_qwen_d2d_static.CALDIR=\"$OUT/cal\" -o "$OUT/tb.vvp" "${SRC[@]}" > "$OUT/build.log" 2>&1 || { head -30 "$OUT/build.log"; exit 2; }
vvp -n "$OUT/tb.vvp" > "$OUT/run.log" 2>&1 || true
grep -E 'D2D_STATIC_|RECOVERY|frames' "$OUT/run.log"
grep -q '^D2D_STATIC_PASS' "$OUT/run.log"
