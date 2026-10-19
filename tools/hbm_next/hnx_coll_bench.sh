#!/bin/bash
# HBM-NEXT-UNITS-COLL 2026-10-19: N-row message-train benches of the next-die COLL gather master (ot_hnx_coll_gq), fleet,
# Verilator 5.050. Run from a bundle root (git archive of the lane branch):  tools/hbm_next/hnx_coll_bench.sh OUT STAGE
#  STAGE main : schedule proofs (d4g check F<400 + train check N 1..6 F<200), vectors, one build (MUT 0), runs
#               s0 (+set=0 = the d4g bench rows, N 1: the fork reproduces ot_hgi_coll_gq at every compiled edge),
#               s1 (+set=1 trains N 1..6, negative rs_A), s2 (+set=2 cycles(N) scan), faults f1..f4 (set 0) and f5 (set 1,
#               rs_O breaks the bank rule) -> COLLQ PASS / COLLQ FAULT PASS
#  STAGE m6|m7|m8 : mutant (6 source ignores rs_A, 7 landing ignores rs_O, 8 row-local k never restarts) on +set=1 -> FAIL
set -u
B=$(pwd); O=$(realpath -m "${1:?OUT}"); ST=${2:?STAGE}; mkdir -p "$O"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
VL=$(command -v verilator); echo "verilator: $VL $($VL --version)" > "$O/verilator.txt"
V(){ echo "$(date -Is) $*" | tee -a "$O/verdict_$ST.txt"; }
V "start host=$(hostname) bundle=$(cat $B/BUNDLE_COMMIT 2>/dev/null)"
P=rtl/hbm_accel/generic/collective/p2p
LIB=(rtl/hbm_next/coll/ot_hnx_coll_gq.sv "$P/ot_hgi_coll_ring_ag.sv" "$P/ot_hgi_coll_ring_ag_lane.sv" "$P/ot_hgi_coll_ring_b_stop.sv"
     "$P/ot_hgi_coll_pring_static_state_capture.sv" "$P/ot_hgi_coll_pring_static.sv"
     rtl/hbm_accel/index/quad_1017/ot_hbm_idx_vm_share2_static.sv rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv
     rtl/lib/ot_rst_relay.sv physical/hbm_xp_aq_tree13_1014/ot_hbm_xp_aq_tree13.sv physical/hbm_xp_aq_tree13_1014/ot_hbm_xp_aq_scale13.sv
     rtl/hdc/v41/ot_hdc_actquant.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_delay.sv
     rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv)
FL=(--binary --timing -O2 -j 16 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-MULTITOP -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN)
build(){ # tag mut
  local d=$O/obj_$1; rm -rf $d
  verilator "${FL[@]}" -GMUT=$2 -GKQMUT=0 -GVEC="\"$O/vec\"" -GVECR="\"$O/vecr\"" --top-module tb_hnx_coll_gq --Mdir $d \
    -o V$1 rtl/hbm_next/coll/tb/tb_hnx_coll_gq.sv "${LIB[@]}" > $O/build_$1.log 2>&1 || { sleep 5;
  verilator "${FL[@]}" -j 1 -GMUT=$2 -GKQMUT=0 -GVEC="\"$O/vec\"" -GVECR="\"$O/vecr\"" --top-module tb_hnx_coll_gq --Mdir $d \
    -o V$1 rtl/hbm_next/coll/tb/tb_hnx_coll_gq.sv "${LIB[@]}" > $O/build_$1.log 2>&1; }
  V "build $1 rc=$? bin=$( [ -x $d/V$1 ] && echo ok || echo MISSING)"
}
run(){ # tag bin args...
  local t=$1 b=$2; shift 2
  ( cd $O && $O/obj_$b/V$b "$@" > $O/$t.log 2>&1; echo RUN_RC=$? >> $O/$t.log )
  V "$t: $(grep -h '^COLLQ PASS\|^COLLQ FAIL\|^COLLQ FAULT' $O/$t.log | head -1)"
}
if [ "$ST" = main ]; then
  python3 tools/hgi_sim/collq_gather_1018.py check > $O/check_d4g.log 2>&1; V "$(tail -1 $O/check_d4g.log)"
  python3 tools/hgi_sim/collq_gather_1018.py vectors $O/vec > $O/vec.log 2>&1 || V "vectors FAILED"
  python3 tools/hbm_next/hnx_coll_gq_train.py vectors-rows $O/vecr > $O/vecr.log 2>&1 || V "vectors-rows FAILED"
  python3 tools/hbm_next/hnx_coll_gq_train.py price > $O/price.jsonl 2>&1
  ( python3 tools/hbm_next/hnx_coll_gq_train.py check-train > $O/check_train.log 2>&1; V "$(tail -1 $O/check_train.log)" ) &
  build m 0
  run s0 m +set=0 & run s1 m +set=1 & run s2 m +set=2 &
  for f in 1 2 3 4; do run f$f m +set=0 +fault=$f & done
  run f5 m +set=1 +fault=5 &
  wait
  grep -h '^COLLQ_TRAIN' $O/s1.log $O/s2.log > $O/cycles_N.txt
  rm -rf $O/obj_m
else
  python3 tools/hbm_next/hnx_coll_gq_train.py vectors-rows $O/vecr > $O/vecr.log 2>&1 || V "vectors-rows FAILED"
  m=${ST#m}; build $ST $m; run $ST $ST +set=1; rm -rf $O/obj_$ST
fi
V "done"
