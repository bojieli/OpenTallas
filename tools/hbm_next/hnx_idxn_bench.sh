#!/bin/bash
# HBM-NEXT-UNITS-IDXN 2026-10-19: one-key-stream N-row IDX.INDEX benches on the fleet (Verilator 5.050). Run from a bundle
# root (git archive of the lane branch):  tools/hbm_next/hnx_idxn_bench.sh OUT STAGE
#  lint   : lint of the idxn sources and the d4g parent (fast fail before the hierarchical builds)
#  index  : full-shape IDX.INDEX, real VM banks / quant / 4 scorers / selectors / link, ONE build of each DUT:
#    d4g_n1      d4g DUT, d4g programme, 1 row                                  -> PASS + dump
#    n1_d4gprog  idxn DUT, d4g programme (gap 100), 1 row                       -> PASS, dump == d4g_n1 (every edge)
#    n1..n6      idxn DUT, row frame (gap 4), pitch = compiled row II, N = 1..6 -> PASS each; IDX_ROWS_CYCLES(N)
#                (n1 payload == d4g_n1 payload: same scores / TX flits, earlier by the shorter emit->key gap)
#    m21 m22 m23 N = 4: replay read without lookahead / all rows on selector 0 / link row slots dropped -> FAIL
#    mii1        N = 2, pitch = row II - 1 (query reload 22 < 23 slots after the last key)        -> FAIL (fault)
#    mg2         N = 2, frame compiled with G2 = 8 (query-reload hazard ignored), its own pitch     -> FAIL
#    msel        N = 6, pitch 200 (selector class collision between rows r and r + 4)            -> FAIL (fault)
#    mstride     N = 2, operand row strides 0 (d4g addressing)                                   -> FAIL
set -u
B=$(pwd); O=$(realpath -m "${1:?OUT}"); ST=${2:?STAGE}; mkdir -p "$O"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
VL=$(command -v verilator); echo "verilator: $VL $($VL --version)" > "$O/verilator.txt"
V(){ echo "$(date -Is) $*" | tee -a "$O/verdict_$ST.txt"; }
V "start host=$(hostname) bundle=$(cat $B/BUNDLE_COMMIT 2>/dev/null)"
X=rtl/hbm_accel/index
D4G=($X/ot_hbm_idx_scheduled_static.sv $X/ot_hbm_idx_calendar_static.sv $X/ot_hbm_idx_parent_static.sv $X/ot_hbm_idx_vm_query_static.sv
 $X/ot_hbm_idx_topk_link_static.sv)
N=rtl/hbm_next/idxn
HNX=($N/ot_hnx_idxn_scheduled.sv $N/ot_hnx_idxn_calendar.sv $N/ot_hnx_idxn_parent.sv $N/ot_hnx_idxn_keybuf.sv $N/ot_hnx_idxn_link.sv
 rtl/hbm_next/idx/ot_hnx_idx_vm_query_static.sv)
COMMON=($X/ot_hbm_idx_vm_static.sv $X/hidx_meta_w25_d123_r0.sv rtl/hdc/ot_hdc_delay_rf.sv $X/ot_hbm_idx_score_static.sv
 $X/ot_hbm_idx_engine_static.sv $X/ot_hbm_idx_selector_static.sv
 $X/ot_hbm_idx_query_static.sv $X/ot_hbm_idx_query_owned_native.sv $X/ot_hbm_idx_actquant_owned_native.sv
 physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v
 rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv
 rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/v41x/ot_hbm_idx_owned_native.sv rtl/hdc/v41x/ot_hdc_v41x_idx_hslice.sv
 rtl/lib/ot_rst_relay.sv rtl/hdc/v41x/ot_hdc_v41x_idx_lat.sv rtl/hdc/v41x/ot_hdc_v41x_idx_arith_lat.sv rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv
 rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
 physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
 physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v
 $N/tb/tb_hnx_idxn_rows.sv)
VLT=rtl/test/hbm_idx_static/parent.vlt
sha256sum "${D4G[@]}" "${HNX[@]}" "${COMMON[@]}" $VLT tools/hbm_next/hnx_idxn_calendar.py tools/hbm_next/hnx_idx_rows_vectors.py \
  tools/hbm_idx_static_calendar.py tools/hbm_next/hnx_idxn_bench.sh > "$O/sources_$ST.sha256"
TOP="--top-module tb_hnx_idxn_rows"
if [ "$ST" = lint ]; then
  verilator --lint-only --timing -Wno-fatal -Wno-lint -Wno-style $TOP "${HNX[@]}" "${COMMON[@]}" > $O/lint_hnx.log 2>&1
  V "lint idxn rc=$? errors=$(grep -c '%Error' $O/lint_hnx.log)"; grep '%Error' $O/lint_hnx.log | head -20 | tee -a $O/verdict_$ST.txt
  verilator --lint-only --timing -Wno-fatal -Wno-lint -Wno-style +define+D4G_DUT $TOP "${D4G[@]}" "${COMMON[@]}" > $O/lint_d4g.log 2>&1
  V "lint d4g rc=$? errors=$(grep -c '%Error' $O/lint_d4g.log)"; grep '%Error' $O/lint_d4g.log | head -5 | tee -a $O/verdict_$ST.txt
  python3 tools/hbm_next/hnx_idxn_calendar.py $O/cal > $O/cal.log 2>&1; V "calendar rc=$? $(cut -c1-300 $O/cal.log)"
  V done; exit 0
fi
# ---- vectors + calendars
OPENBLAS_NUM_THREADS=1 python3 tools/hbm_next/hnx_idx_rows_vectors.py $O/vec 6 > $O/vectors.log 2>&1 || { V "vectors FAILED"; cat $O/vectors.log; exit 1; }
python3 tools/hbm_next/hnx_idxn_calendar.py $O/cal > $O/cal.log 2>&1 || { V "calendar FAILED"; cat $O/cal.log; exit 1; }
python3 tools/hbm_next/hnx_idxn_calendar.py $O/calg2 --g2 8 > $O/calg2.log 2>&1 || { V "calendar g2 FAILED"; exit 1; }
V "vectors: $(tr '\n' ' ' < $O/vectors.log)"; V "calendar: $(cat $O/cal.log)"; V "calendar g2=8 (mutant): $(cut -c1-120 $O/calg2.log)"
J(){ python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print(eval(sys.argv[2]))" "$@"; }
FL=$(J $O/cal/frame/calendar.json "d['length']"); II=$(J $O/cal/frame/calendar.json "d['row_ii']")
FK=$(J $O/cal/frame/calendar.json "d['first_key_edge_row0']"); FT=$(J $O/cal/frame/calendar.json "d['first_tx_edge_row0']")
G2L=$(J $O/calg2/frame/calendar.json "d['length']"); G2II=$(J $O/calg2/frame/calendar.json "d['row_ii']")
DL=$(J $O/cal/d4g/calendar.json "d['length']"); DK=$(J $O/cal/d4g/calendar.json "d['predicted']['first_key_instruction']+3")
DT=$(J $O/cal/d4g/calendar.json "d['predicted']['first_tx_from_instruction0']+3")
TV=""; [ -x /usr/bin/time ] && TV="/usr/bin/time -v"
build(){ # tag defines sources...
  local t=$1 def=$2; shift 2; local d=$O/obj_$t; rm -rf $d
  $TV verilator $def --hierarchical --binary --timing --verilate-jobs 4 --build-jobs ${IDX_BUILD_JOBS:-8} -O1 -Wno-fatal -Wno-lint -Wno-style \
    $TOP -Mdir $d -o V$t "$@" $VLT > $O/build_$t.log 2>&1
  local rc=$?
  if [ ! -x $d/V$t ]; then V "build $t rc=$rc: retry once (PCH race)"; $TV verilator $def --hierarchical --binary --timing \
    --verilate-jobs 2 --build-jobs 8 -O1 -Wno-fatal -Wno-lint -Wno-style $TOP -Mdir $d -o V$t "$@" $VLT \
    > $O/build_${t}_retry.log 2>&1; fi
  V "build $t rc=$rc bin=$( [ -x $d/V$t ] && echo ok || echo MISSING) maxrss_kb=$(grep -h 'Maximum resident' $O/build_$t*.log | tail -1 | awk '{print $NF}')"
}
run(){ # tag binary-tag caldir want plusargs...
  local t=$1 b=$2 cal=$3 want=$4; shift 4; local od=$O/run_$t; rm -rf $od; mkdir -p $od
  cp $O/vec/*.hex $od/; cp $cal/calendar_instructions.hex $od/
  ( cd $od && $O/obj_$b/V$b "$@" > $od/run.log 2>&1; echo RUN_RC=$? >> $od/run.log )
  local rc=$(grep -o 'RUN_RC=[0-9]*' $od/run.log | cut -d= -f2)
  local verdict=PASS; grep -q 'IDX_HNX_ROWS PASS' $od/run.log || verdict=FAIL
  local ok=OK; [ "$verdict" = "$want" ] || ok=UNEXPECTED
  V "$t [$ok want $want got $verdict rc=$rc]: $(grep -h 'IDX_ROWS_CYCLES\|IDX_HNX_ROWS rows\|TIMELINE\|SCOREBAD\|TXBAD\|EXTRASCORE\|KEYSTREAM\|BEATROW' $od/run.log | head -5 | tr '\n' ' ')"
}
if [ "$ST" = index ]; then
  build hnx "" "${HNX[@]}" "${COMMON[@]}"           # sequential: two parallel hierarchical builds peaked > 80 GB (OOM 10-19)
  build d4g "+define+D4G_DUT" "${D4G[@]}" "${COMMON[@]}"
  run d4g_n1 d4g $O/cal/d4g PASS +N=$DL +EXP_KEY=$DK +EXP_TX=$DT &
  run n1_d4gprog hnx $O/cal/d4g PASS +N=$DL +ROWS=1 +EXP_KEY=$DK +EXP_TX=$DT &
  for n in 1 2 3 4 5 6; do run n$n hnx $O/cal/frame PASS +N=$FL +ROWS=$n +PITCH=$II +EXP_KEY=$FK +EXP_TX=$FT & done
  wait
  for m in 21 22 23; do run m$m hnx $O/cal/frame FAIL +N=$FL +ROWS=4 +PITCH=$II +MUT=$m +MUT$m & done
  run mii1 hnx $O/cal/frame FAIL +N=$FL +ROWS=2 +PITCH=$((II-1)) &
  run mg2 hnx $O/calg2/frame FAIL +N=$G2L +ROWS=2 +PITCH=$G2II &
  run msel hnx $O/cal/frame FAIL +N=$FL +ROWS=6 +PITCH=200 &
  run mstride hnx $O/cal/frame FAIL +N=$FL +ROWS=2 +PITCH=$II +QSTR=0 +WSTR=0 &
  wait
  # N = 1 bit-for-bit equivalence with the d4g parent
  if cmp -s $O/run_d4g_n1/tx_dump.txt $O/run_n1_d4gprog/tx_dump.txt; then V "EQUIV n1_d4gprog == d4g_n1: IDENTICAL ($(wc -l < $O/run_d4g_n1/tx_dump.txt) score/TX lines, every edge)"
  else V "EQUIV n1_d4gprog vs d4g_n1: DIFFERENT ($(diff $O/run_d4g_n1/tx_dump.txt $O/run_n1_d4gprog/tx_dump.txt | grep -c '^[<>]') lines)"; fi
  strip(){ awk '{ $2=""; print }' $1; }
  if cmp -s <(strip $O/run_d4g_n1/tx_dump.txt) <(strip $O/run_n1/tx_dump.txt); then
    V "EQUIV n1 (row frame) payload == d4g_n1: IDENTICAL ($(wc -l < $O/run_n1/tx_dump.txt) score/TX lines); edge shift first score $(awk 'NR==1{print $2}' $O/run_n1/tx_dump.txt) vs $(awk 'NR==1{print $2}' $O/run_d4g_n1/tx_dump.txt)"
  else V "EQUIV n1 payload vs d4g_n1: DIFFERENT"; fi
  rm -rf $O/obj_d4g $O/obj_hnx; find $O -name tx_dump.txt -size +5M -delete; find $O -name '*.hex' -size +1M -delete
  V done
fi
