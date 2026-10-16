#!/bin/bash
# Q-LINK static D2D link DIE-NAME bench. Usage: run_d2d_static.sh OUT [MUT]
set -eu
OUT=$1; MUT=${2:-0}
W=$(cd "$(dirname "$0")/../.." && pwd); R=$(cd "$W/.." && pwd)
TXL=${TXL:-6}; PHY=${PHY:-5}
mkdir -p "$OUT"
CTXL=$TXL; [ "$MUT" = 4 ] && CTXL=$((TXL-1))
python3 "$R/tools/qwen_split/d2d_link_calendar.py" --out "$OUT/cal" --txl "$CTXL" --phy "$PHY" --profile program --txd-c 1,2,1,2 --txd-k 1,2,1,1 --host-stages 0 --link-handoff "$R/results/arch/qwen_split_compute_1014/res_train_decision_1015/decision.json" $([ "${PR:-1}" = 1 ] && echo --pinreg) > "$OUT/calendar.log"
python3 "$R/tools/qwen_split/d2d_program_params.py" "$OUT/cal/calendar.json" "$OUT/cal"
# the committed constant sequencer image must be the compiler's (mutant 4 compiles a wrong TXL: its images differ by design)
python3 "$R/tools/qwen_split/d2d_cal_seq_image.py" "$OUT/cal" "$OUT/cal/d2d_cal_image_compiled.svh"
if [ "$MUT" != 4 ]; then cmp "$OUT/cal/d2d_cal_image_compiled.svh" "$W/qwen_sys/d2d_static_20261015/d2d_cal_image.svh" || { echo "D2D_PROGRAM_FAIL committed sequencer image differs from the compiler"; exit 1; }; fi
SRC=("$W/lib/ot_rst_pipe.sv" "$W/qwen_sys/split_20261014/ot_qwen_crc_parallel.sv" "$W/qwen_sys/split_20261014/ot_qwen_static_slot_link.sv"
 "$W/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv" "$W/qwen_sys/split_20261014/qkd_native_attention_record.sv"
 "$W/qwen_sys/d2d_static_20261015/ot_qwen_d2d_static.sv" "$W/qwen_sys/d2d_static_20261015/ot_qwen_d2d_services.sv" "$W/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies.sv" "$W/qwen_split/qfd_kvn_static_transport.sv"
 "$W/qwen_sys/d2d_static_20261015/ot_qwen_d2d_cal_seq.sv" "$W/qwen_sys/d2d_static_20261015/ot_qwen_d2d_cal_seq_dies.sv"
 "$R/physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy/ot_qkvd_ucie_x64_phy_model.sv"
 "$R/physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v"
 "$W/test/qwen_split/tb_qwen_d2d_program.sv")
sha256sum "${SRC[@]}" "$R/tools/qwen_split/d2d_link_calendar.py" > "$OUT/source.sha256"
if [ "${BACKEND:-iverilog}" = verilator ]; then
  verilator --binary --timing -j "${JOBS:-4}" -Wno-fatal -I"$OUT/cal" -I"$W/qwen_sys/d2d_static_20261015" --top-module tb_qwen_d2d_program \
    -DOT_MEM_NO_INIT -GMUT="$MUT" -GDRV="${DRV:-0}" -GPR="${PR:-1}" -GTXL="$TXL" -GPHY="$PHY" -GCALDIR=\"$OUT/cal\" \
    --Mdir "$OUT/obj" "${SRC[@]}" > "$OUT/build.log" 2>&1 || { head -30 "$OUT/build.log"; exit 2; }
  "$OUT/obj/Vtb_qwen_d2d_program" > "$OUT/run.log" 2>&1 || true
else
iverilog -g2012 -I"$OUT/cal" -I"$W/qwen_sys/d2d_static_20261015" -DOT_MEM_NO_INIT -s tb_qwen_d2d_program -Ptb_qwen_d2d_program.MUT=$MUT -Ptb_qwen_d2d_program.DRV=${DRV:-0} -Ptb_qwen_d2d_program.PR=${PR:-1} -Ptb_qwen_d2d_program.TXL=$TXL \
 -Ptb_qwen_d2d_program.PHY=$PHY -Ptb_qwen_d2d_program.CALDIR=\"$OUT/cal\" -o "$OUT/tb.vvp" "${SRC[@]}" > "$OUT/build.log" 2>&1 || { head -30 "$OUT/build.log"; exit 2; }
vvp -n "$OUT/tb.vvp" > "$OUT/run.log" 2>&1 || true
fi
grep -E 'D2D_PROGRAM_|RECOVERY|frames' "$OUT/run.log"
grep -q '^D2D_PROGRAM_PASS' "$OUT/run.log"
