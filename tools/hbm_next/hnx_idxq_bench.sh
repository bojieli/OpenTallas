#!/bin/bash
# HBM-NEXT-UNITS IDXQ 2026-10-19: IDXN ported into the per-quadrant IDX client (ot_hnx_idxq_client_quad), lockstep vs the
# IDXN stack-scorer client ot_hnx_idxn_scheduled N_Q=2 TP=192 (OT_IDX_SCORE_CLUSTER) + exact oracle on N query rows.
# Fleet (Verilator 5.050), from a bundle root:  tools/hbm_next/hnx_idxq_bench.sh OUT {lint|lockstep}
#  lint     : lint of the sources (fast fail before the hierarchical build)
#  lockstep : ONE build; runs (pitch = the compiled row II of the chain 8 and chain 14 frames, both 232):
#    n1 n2 n4 n6   N = 1, 2, 4, 6 rows                                                     -> PASS
#    chain13       N = 2, new programme compiled for a 1-edge-short tree (--score-chain 13)  -> FAIL
#    m2 / m3       N = 2, live key bit flipped on beat 100 / quadrant halves swapped on the key lines -> FAIL
#    m4            N = 2, quadrant 1 replay buffer bypassed (rows >= 1 score the idle live lines)   -> FAIL
#    m6 / m7       N = 4, link row slots dropped / every row on selector 0                          -> FAIL
#    m8            N = 2, quadrant 2 calendar copy at pitch + 1 (copies out of lockstep)            -> FAIL
set -u
B=$(pwd); O=$(realpath -m "${1:?OUT}"); ST=${2:?STAGE}; mkdir -p "$O"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
VL=$(command -v verilator); echo "verilator: $VL $($VL --version)" > "$O/verilator.txt"
V(){ echo "$(date -Is) $*" | tee -a "$O/verdict_$ST.txt"; }
V "start host=$(hostname) bundle=$(cat $B/BUNDLE_COMMIT 2>/dev/null) $(cat $O/verilator.txt)"
X=rtl/hbm_accel/index; Q=$X/quad_1017; N=rtl/hbm_next/idxn; QQ=rtl/hbm_next/idxq
SRC=($N/ot_hnx_idxn_scheduled.sv $N/ot_hnx_idxn_calendar.sv $N/ot_hnx_idxn_parent.sv $N/ot_hnx_idxn_keybuf.sv $N/ot_hnx_idxn_link.sv
 rtl/hbm_next/idx/ot_hnx_idx_vm_query_static.sv
 $QQ/ot_hnx_idxq_qctl.sv $QQ/ot_hnx_idxq_rootctl.sv $QQ/ot_hnx_idxq_link.sv $QQ/ot_hnx_idxq_client_quad.sv
 $Q/ot_hbm_idx_score_quarter_static.sv $Q/ot_hbm_idx_xq_node_static.sv
 $X/ot_hbm_idx_vm_static.sv $X/hidx_meta_w25_d123_r0.sv rtl/hdc/ot_hdc_delay_rf.sv $X/ot_hbm_idx_score_static.sv $X/ot_hbm_idx_engine_static.sv
 $X/ot_hbm_idx_selector_static.sv $X/ot_hbm_idx_query_static.sv $X/ot_hbm_idx_query_owned_native.sv $X/ot_hbm_idx_actquant_owned_native.sv
 $X/ot_hbm_idx_topk_static.sv rtl/hbm_accel/generic/idx/ot_hgi_idx_tk2.sv $X/ot_hbm_idx_vm_share_static.sv
 rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv
 rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/v41x/ot_hbm_idx_owned_native.sv rtl/hdc/v41x/ot_hdc_v41x_idx_hslice.sv
 rtl/lib/ot_rst_relay.sv rtl/hdc/v41x/ot_hdc_v41x_idx_lat.sv rtl/hdc/v41x/ot_hdc_v41x_idx_arith_lat.sv rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv
 rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
 physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
 physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v
 physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v
 rtl/hdc/v41x/ot_hbm_idx_chunk_rt.sv $X/ot_hbm_idx_score_cluster.sv
 $QQ/tb/tb_hnx_idxq_lockstep.sv)
VLT=rtl/test/hbm_idx_static/quad.vlt
sha256sum "${SRC[@]}" $VLT tools/hbm_next/hnx_idxn_calendar.py tools/hbm_next/hnx_idxq_vectors.py tools/hbm_idx_static_calendar.py \
  tools/hbm_next/hnx_idxq_bench.sh > "$O/sources_$ST.sha256"
TOP="--top-module tb_hnx_idxq_lockstep"
if [ "$ST" = lint ]; then
  verilator --lint-only --timing -DOT_IDX_SCORE_CLUSTER -Wno-fatal -Wno-lint -Wno-style $TOP "${SRC[@]}" > $O/lint.log 2>&1
  V "lint rc=$? errors=$(grep -c '%Error' $O/lint.log)"; grep '%Error' $O/lint.log | head -20 | tee -a $O/verdict_$ST.txt
  V done; exit 0
fi
OPENBLAS_NUM_THREADS=1 python3 tools/hbm_next/hnx_idxq_vectors.py $O/vec 6 191 > $O/vectors.log 2>&1 || { V "vectors FAILED"; cat $O/vectors.log; exit 1; }
NK=$(cat $O/vec/nkeys.txt)
for c in 8 13 14; do python3 tools/hbm_next/hnx_idxn_calendar.py $O/cal_c$c --score-chain $c > $O/cal_c$c.log 2>&1 || { V "calendar c$c FAILED"; exit 1; }; done
V "vectors (n $NK): $(tr '\n' ' ' < $O/vectors.log)"; for c in 8 13 14; do V "calendar chain $c: $(cut -c1-160 $O/cal_c$c.log)"; done
J(){ python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print(eval(sys.argv[2]))" "$@"; }
L8=$(J $O/cal_c8/frame/calendar.json "d['length']"); L13=$(J $O/cal_c13/frame/calendar.json "d['length']"); L14=$(J $O/cal_c14/frame/calendar.json "d['length']")
I8=$(J $O/cal_c8/frame/calendar.json "d['row_ii']"); I14=$(J $O/cal_c14/frame/calendar.json "d['row_ii']"); II=$(( I8 > I14 ? I8 : I14 ))
V "frames: chain8 F=$L8 II=$I8, chain14 F=$L14 II=$I14 -> pitch $II"
TV=""; [ -x /usr/bin/time ] && TV="/usr/bin/time -v"
d=$O/obj; rm -rf $d
$TV verilator -DOT_IDX_SCORE_CLUSTER --hierarchical --binary --timing --verilate-jobs 4 --build-jobs ${IDX_BUILD_JOBS:-8} -O1 -Wno-fatal -Wno-lint -Wno-style \
  -GTP=192 -GRANK=191 -GNKEYS=$NK -GCHAIN=6 $TOP -Mdir $d -o Vq "${SRC[@]}" $VLT > $O/build.log 2>&1; rc=$?
if [ ! -x $d/Vq ]; then V "build rc=$rc: retry once (PCH race)"; $TV verilator -DOT_IDX_SCORE_CLUSTER --hierarchical --binary --timing \
  --verilate-jobs 2 --build-jobs 8 -O1 -Wno-fatal -Wno-lint -Wno-style -GTP=192 -GRANK=191 -GNKEYS=$NK -GCHAIN=6 $TOP -Mdir $d -o Vq \
  "${SRC[@]}" $VLT > $O/build_retry.log 2>&1; fi
V "build rc=$rc bin=$( [ -x $d/Vq ] && echo ok || echo MISSING) maxrss_kb=$(grep -h 'Maximum resident' $O/build*.log | tail -1 | awk '{print $NF}')"
[ -x $d/Vq ] || { tail -30 $O/build.log | tee -a $O/verdict_$ST.txt; exit 1; }
run(){ # tag newchain want plusargs...
  local t=$1 c=$2 want=$3; shift 3; local od=$O/run_$t; rm -rf $od; mkdir -p $od
  cp $O/vec/*.hex $od/; cp $O/cal_c8/frame/calendar_instructions.hex $od/cal_old.hex; cp $O/cal_c$c/frame/calendar_instructions.hex $od/cal_new.hex
  local ln=$L14; [ $c = 13 ] && ln=$L13
  ( cd $od && $d/Vq +NO=$L8 +NN=$ln +PITCH=$II "$@" > $od/run.log 2>&1; echo RUN_RC=$? >> $od/run.log )
  local got=PASS; grep -q 'IDXQ_LOCKSTEP PASS' $od/run.log || got=FAIL
  local ok=OK; [ "$got" = "$want" ] || ok=UNEXPECTED
  V "$t [$ok want $want got $got $(grep -o 'RUN_RC=[0-9]*' $od/run.log)]: $(grep -h 'IDXQ_LOCKSTEP rows\|IDXQ_ROWS_CYCLES\|BAD\|disagree\|ORACLE\|FAIL' $od/run.log | head -4 | tr '\n' ' ')"
  rm -f $od/*.hex
}
if [ "$ST" = lockstep ]; then
  for n in 1 2 4 6; do run n$n 14 PASS +ROWS=$n & done; wait
  run chain13 13 FAIL +ROWS=2 &
  for m in 2 3 4 8; do run m$m 14 FAIL +ROWS=2 +MUT=$m & done
  for m in 6 7; do run m$m 14 FAIL +ROWS=4 +MUT=$m & done
  wait
  rm -rf $d
  V "SUMMARY unexpected=$(grep -c UNEXPECTED $O/verdict_$ST.txt)"
  V done
fi
