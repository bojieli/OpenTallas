#!/usr/bin/env bash
# S81-ARCH-RTL-2 11-12: all HLAT gates for dsdv_bksel_q (bksplit_1108 profile).  usage (repo root):
#   run_hlat_gates.sh <kit_rtl_dir> <out>     kit_rtl_dir = the vC4r kit rtl/ copy (unchanged support sources)
# (1) q bench HLAT 0 vs 1, random stimulus: outputs bit-exact + every u_fl_ latch holds through the high phase;
#     mutant OT_S81PH_HLK_MUT (positive-level) must FAIL.  (2) layer bench tb_bk_layer (compiler stimulus, 6 sets):
#     HLAT 1 trace == HLAT 0 trace; HLK_COV: every latch instance toggles.  (3) verilator lint HLAT 0 / 1.
set -u
K=$1; O=$2; mkdir -p $O
P=physical/die_plan/s81/cores/legacy/profiles/bksplit_1108; B=$P/bench_hlat
DEF="-DOT_BKSEL_RC=0 -DOT_BKSEL_RS=0 -DOT_BKSEL_RO=0 -DOT_BKSEL_RLN=0 -DOT_S81PH_SEL_INDEXED13 -DOT_S81PH_FIFO_SRAM -DOT_SRAM_P192 -DOT_S81PH_SEL_SUCC -DOT_S81PH_SEL_FAN32 -DOT_S81PH_SEL_ACC32 -DOT_S81PH_SEL_ILD -DOT_S81PH_SEL_FRPR -DOT_S81PH_SEL_HQ -DOT_S81PH_HQ_INPUT_RAW -DOT_HB_PINCOPY -DOT_S81PH_PACK_Z0FOLD -DOT_BKQ_RCP=16 -DOT_BKQ_GBREG -DOT_BKQ_GBREG2 -DOT_BKQ_BSTG -DOT_BKQ_FO8 -DOT_BKQ_ORT -DOT_BKQ_SPLIT"
SETS="legacy indexed13 indexed13_ties indexed13_ninf indexed13_zeros indexed13_corrupt"
for m in 0 1; do bash $B/run_hlat_bench.sh $K $P/rtl $O/q $m > $O/q$m.log 2>&1 & done
for h in 0 1 c; do
  ds=""; for d in $SETS; do mkdir -p $O/l$h/$d; cp results/arch/s81_topk_final_1019/bench/$d/{stim.txt,exp.txt,meta.json} $O/l$h/$d/; ds="$ds $O/l$h/$d"; done
  hv=$h; x=""; [ $h = c ] && { hv=1; x="-DOT_S81PH_HLK_COV"; }
  VL_EXTRA="$DEF -DOT_BKQ_HLAT_DEF=$hv $x" J=12 bash $B/run_hlat_layer.sh $O/lb$h $ds > $O/l$h.log 2>&1 &
done
for h in 0 1; do LINT_ONLY=1 VL_EXTRA="$DEF -DOT_BKQ_HLAT_DEF=$h" bash $B/run_hlat_layer.sh $O/lint$h > $O/lint$h.out 2>&1 & done
wait
ok=1
q0=$(grep -h "^DSDV_BKSEL_HLAT" $O/q0.log); q1=$(grep -h "^DSDV_BKSEL_HLAT" $O/q1.log)
echo "$q0" | grep -q " PASS " || ok=0; echo "$q1" | grep -q " FAIL " || ok=0
same=0; for d in $SETS; do cmp -s <(grep -v "^- " $O/l0/$d/run.log) <(grep -v "^- " $O/l1/$d/run.log) && same=$((same+1)); done
[ $same = 6 ] || ok=0
ncov=$(grep -h "^HLK_COV" $O/lc/*/run.log | awk '{print $2}' | sort -u | wc -l)
nzero=$(grep -h "^HLK_COV" $O/lc/*/run.log | awk '{k[$2]+=$NF} END{n=0; for (i in k) if (k[i]==0) n++; print n}')
[ "$ncov" -gt 0 ] && [ "$nzero" = 0 ] || ok=0
le=$(for h in 0 1; do grep -c "%Error" $O/lint$h/lint.log; done | paste -sd/)
lw=$(diff <(grep -o "%Warning-[A-Z]*" $O/lint0/lint.log | sort | uniq -c) <(grep -o "%Warning-[A-Z]*" $O/lint1/lint.log | sort | uniq -c) | grep "^>" | tr "\n" " ")
echo "HLAT_GATES $([ $ok = 1 ] && echo PASS || echo FAIL) q_bench: [$q0] mutant: [$q1] layer_traces_identical $same/6 latch_instances $ncov untoggled $nzero lint_errors(h0/h1) $le new_warnings: $lw"
