#!/bin/bash
# S81-TOPK3: re-run the earlier successor mutants (SUCC one-hot, FAN32 group select, FAN32 clear copy) on the ACC32
# build so every kit mutant witness is from the exact define set.  usage: run_mut_prev.sh <outdir>
set -uo pipefail
O=${1:?out}; mkdir -p "$O"
DEF="-DOT_S81PH_SEL_INDEXED13 -DOT_S81PH_FIFO_SRAM -DOT_SRAM_P192 -DOT_S81PH_SEL_SUCC -DOT_S81PH_SEL_RST64 -DOT_S81PH_SEL_FAN32 -DOT_S81PH_SEL_ACC32"
declare -A SRC=([oh]=results/arch/s81_topk_succ_1019/bench/mut_oh [gs]=results/arch/s81_topk_fan32_1019/bench/mut_gs [clr]=results/arch/s81_topk_fan32_1019/bench/mut_clr)
declare -A MD=([oh]=OT_S81PH_SEL_SUCC_MUT_OH [gs]=OT_S81PH_SEL_FAN32_MUT_GS [clr]=OT_S81PH_SEL_FAN32_MUT_CLR)
for m in oh gs clr; do
  rm -rf "$O/mut_$m"; mkdir -p "$O/mut_$m"; cp ${SRC[$m]}/stim.txt ${SRC[$m]}/exp.txt ${SRC[$m]}/meta.json "$O/mut_$m/"
  VL_EXTRA="$DEF -D${MD[$m]}" bash tools/s81_dv/layer_prog/bk/run_bk_layer.sh "$O/build_mut_$m" "$O/mut_$m" > "$O/mut_$m.log" 2>&1 &
done
wait
for m in oh gs clr; do echo "mut_$m $(cut -c1-60 $O/mut_$m/verdict.txt 2>/dev/null)"; done
