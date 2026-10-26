#!/bin/bash
# TOKc-SEGCAL 10-22: LM-head die-form bench (TOK.QW.LAYER.3).  Runs on a fleet host (ot-run), Verilator 5.050.
#   run_segcal_bench.sh REF_TREE DUT_ROOT OUT
# REF_TREE = the TOKEN PASS head-stage tree (source assembly c0f8097f3 + fixtures: tokfunc-qw-1021/head/tree);
# DUT_ROOT = materialize_hp13_sources.py output (HP13 die-form sources incl. this branch's go port).
# Runs (in parallel): dv-form reference imgh / img0 with trace; HP13 die form (flat + landed lp in lockstep) imgh SEG_CAL 1
# (the port) / SEG_CAL 0 (go as on main before the port: must FAIL) / img0; mutants imgh BMUT 3, MUT 37 (must FAIL).
set -u
REF=$(readlink -f "$1"); DUT=$(readlink -f "$2"); OUT=$(readlink -f "$3"); HERE=$(dirname "$(readlink -f "$0")")
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version | grep -q '5.050' || { echo "need Verilator 5.050"; exit 2; }
mkdir -p "$OUT"; IMG=$REF/results/rtl/qlb_c4b_1018/lmh_cal/codex_r1
BENCH=$REF/rtl/test/qwen_dv/tt_ctlm_prog_bench.py
python3 "$HERE/ref_tb_trace_patch.py" "$REF/rtl/test/qwen_dv/tb_qfd_tt_ctlm_prog.sv" "$OUT/tb_ref_trace.sv" || exit 2
A=(--decode 3 --hard 1)
ref() { python3 "$HERE/hp13_prog_bench.py" --bench "$BENCH" --root "$REF" --tb "$OUT/tb_ref_trace.sv" \
          --sources "$REF/rtl/test/qwen_dv/tt_ctlm_dv_sources.f" --trace -- "${A[@]}" --segcal 1 "$@"; }
die() { python3 "$HERE/hp13_prog_bench.py" --bench "$BENCH" --root "$DUT" --tb "$HERE/tb_qfd_tt_ctlm_prog_hp13.sv" \
          --sources "$DUT/hp13_sources.f" "$@"; }
( ref --img $IMG/imgh --work $OUT/ref_imgh > $OUT/ref_imgh.out 2>&1; echo "RC $?" >> $OUT/ref_imgh.out ) &
( ref --img $IMG/img0 --work $OUT/ref_img0 > $OUT/ref_img0.out 2>&1; echo "RC $?" >> $OUT/ref_img0.out ) &
( die --trace --lockstep -- "${A[@]}" --segcal 1 --img $IMG/imgh --work $OUT/hp13_imgh > $OUT/hp13_imgh.out 2>&1; echo "RC $?" >> $OUT/hp13_imgh.out; cp $OUT/hp13_imgh/trace.txt $OUT/trace_hp13_imgh.txt; cp $OUT/hp13_imgh/log_m0_b0_TB_TRACE_TB_LANDED.txt $OUT/log_hp13_imgh.txt
  die --trace --lockstep -- "${A[@]}" --segcal 1 --img $IMG/img0 --work $OUT/hp13_img0 > $OUT/hp13_img0.out 2>&1; echo "RC $?" >> $OUT/hp13_img0.out; cp $OUT/hp13_img0/trace.txt $OUT/trace_hp13_img0.txt
  die --trace --lockstep -- "${A[@]}" --segcal 1 --bmut 3 --img $IMG/imgh --work $OUT/hp13_imgh > $OUT/hp13_bmut3.out 2>&1; echo "RC $?" >> $OUT/hp13_bmut3.out ) &
( die --trace --lockstep -- "${A[@]}" --segcal 0 --img $IMG/imgh --work $OUT/hp13_seg0 > $OUT/hp13_seg0_imgh.out 2>&1; echo "RC $?" >> $OUT/hp13_seg0_imgh.out ) &
( die --trace --lockstep -- "${A[@]}" --segcal 1 --mut 37 --img $IMG/imgh --work $OUT/hp13_mut37 > $OUT/hp13_mut37.out 2>&1; echo "RC $?" >> $OUT/hp13_mut37.out ) &
wait
cp $OUT/ref_imgh/trace.txt $OUT/trace_ref_imgh.txt; cp $OUT/ref_img0/trace.txt $OUT/trace_ref_img0.txt
cp $OUT/hp13_seg0/trace.txt $OUT/trace_hp13_seg0_imgh.txt
for p in imgh:hp13_imgh img0:hp13_img0 imgh:hp13_seg0_imgh; do
  echo "== trace ${p#*:} vs dv-form ref_${p%%:*}"; python3 "$HERE/trace_compare.py" $OUT/trace_ref_${p%%:*}.txt $OUT/trace_${p#*:}.txt
done > $OUT/trace_lockstep.txt 2>&1
for f in $OUT/*.out; do echo "$(basename $f .out): $(grep -E 'CTLM_PROG|LANDED_LOCKSTEP' $f | tr '\n' ' ')"; done > $OUT/summary.txt
cat $OUT/summary.txt $OUT/trace_lockstep.txt
# landed-lockstep sensitivity witness: only the landed copy without the port (TB_LP_SEG0) must FAIL LANDED_LOCKSTEP.
# (lp.py mutants 4 / 5 = reset-run / landing-release one edge late stay lockstep-clean under this stimulus and under the
#  generated random bench on origin/main too: they are not observable here, recorded, not used as witnesses)
die --lockstep -- "${A[@]}" --segcal 1 --defs TB_LP_SEG0 --img $IMG/imgh --work $OUT/hp13_lpseg0 > $OUT/hp13_lpseg0.out 2>&1
echo "hp13_lpseg0: $(grep -E 'CTLM_PROG|LANDED_LOCKSTEP' $OUT/hp13_lpseg0.out | tr '\n' ' ')" | tee -a $OUT/summary.txt
