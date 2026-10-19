#!/bin/bash
# HNX-GQ s3 (L2H-P3/GQ 10-19): benches of the structurally safe gather issue leaf (ot_hnx_coll_gq_issue with
# ot_hnx_coll_aq14: S9 split, SRAM element ring, registered descriptor read). Fleet, Verilator 5.050 (closure daemon's).
# Run from a bundle root:  tools/hbm_next/hnx_gq_s3_bench.sh OUT STAGE
#  STAGE main : schedule proofs, vectors, one build (MUT 0, FFL 4 = launch -> fire), runs s0 (d4g rows, N 1), s1 (trains
#               N 1..6), s2 (cycles(N) scan), faults f1..f5 -> COLLQ PASS / COLLQ FAULT PASS; + the AQ14 lockstep bench
#               (tb_hnx_aq14 vs ot_hdc_actquant one edge later, 1,024 blocks) -> COLLQ AQ14 AQ14_EXACT_PASS
#  STAGE m2|m6|m7|m8|m9 : leaf mutant (2 exponent bias 126, 6 source ignores rs_A, 7 landing ignores rs_O, 8 row-local k
#               never restarts, 9 quantiser SRAM ring one slot short) -> COLLQ FAIL
#  STAGE aqec|aqrs|aql : quantiser mutant on tb_hnx_aq14 (exponent copy, shift-count copy, ring slot) -> AQ14 FAIL
set -u
B=$(pwd); O=$(realpath -m "${1:?OUT}"); ST=${2:?STAGE}; mkdir -p "$O"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
VL=$(command -v verilator); echo "verilator: $VL $($VL --version)" > "$O/verilator.txt"
V(){ echo "$(date -Is) $*" | tee -a "$O/verdict_$ST.txt"; }
V "start host=$(hostname) bundle=$(cat $B/BUNDLE_COMMIT 2>/dev/null) $($VL --version)"
P=rtl/hbm_accel/generic/collective/p2p
MEM=physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
AQ=(rtl/hbm_next/coll/ot_hnx_coll_aq14.sv rtl/hbm_next/coll/ot_hnx_coll_aq_scale13r.sv "$MEM")
LIB=(rtl/hbm_next/coll/ot_hnx_coll_gq.sv "$P/ot_hgi_coll_ring_ag.sv" "$P/ot_hgi_coll_ring_ag_lane.sv" "$P/ot_hgi_coll_ring_b_stop.sv"
     "$P/ot_hgi_coll_pring_static_state_capture.sv" "$P/ot_hgi_coll_pring_static.sv"
     rtl/hbm_accel/index/quad_1017/ot_hbm_idx_vm_share2_static.sv rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv
     rtl/lib/ot_rst_relay.sv "${AQ[@]}" rtl/hdc/v41/ot_hdc_actquant.sv
     rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_cg.sv
     rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv)
FL=(--binary --timing -O2 -j 16 -DOT_GQ_FAN32 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-MULTITOP -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN)
build(){ # tag mut
  local d=$O/obj_$1; rm -rf $d
  verilator "${FL[@]}" -GMUT=$2 -GKQMUT=0 -GFFL=4 -GVEC="\"$O/vec\"" -GVECR="\"$O/vecr\"" --top-module tb_hnx_coll_gq --Mdir $d \
    -o V$1 rtl/hbm_next/coll/tb/tb_hnx_coll_gq.sv "${LIB[@]}" > $O/build_$1.log 2>&1 || { sleep 5;
  verilator "${FL[@]}" -j 1 -GMUT=$2 -GKQMUT=0 -GFFL=4 -GVEC="\"$O/vec\"" -GVECR="\"$O/vecr\"" --top-module tb_hnx_coll_gq --Mdir $d \
    -o V$1 rtl/hbm_next/coll/tb/tb_hnx_coll_gq.sv "${LIB[@]}" > $O/build_$1.log 2>&1; }
  V "build $1 rc=$? bin=$( [ -x $d/V$1 ] && echo ok || echo MISSING)"
  [ -x $d/V$1 ] || grep -m5 -i "error" $O/build_$1.log | tee -a "$O/verdict_$ST.txt"
}
run(){ # tag bin args...
  local t=$1 b=$2; shift 2
  ( cd $O && $O/obj_$b/V$b "$@" > $O/$t.log 2>&1; echo RUN_RC=$? >> $O/$t.log )
  V "$t: $(grep -h '^COLLQ PASS\|^COLLQ FAIL\|^COLLQ FAULT' $O/$t.log | head -1)"
}
aq(){ # tag defines... -> AQ14 lockstep
  local t=$1; shift
  verilator --binary --timing -O2 -j 8 -DOT_GQ_FAN32 "$@" -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --top-module tb --Mdir $O/obj_$t \
    rtl/hbm_next/coll/tb/tb_hnx_aq14.sv "${AQ[@]}" rtl/hdc/v41/ot_hdc_actquant.sv rtl/hdc/ot_hdc_fpu.sv \
    rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_cg.sv > $O/$t.build.log 2>&1 || grep -m5 -i error $O/$t.build.log
  $O/obj_$t/Vtb > $O/$t.log 2>&1
  if grep -q '^AQ14_EXACT_PASS blocks1024 ' $O/$t.log; then V "COLLQ $t $(grep -m1 AQ14_EXACT_PASS $O/$t.log)"
  else V "COLLQ $t FAIL $(grep -m1 -o 'AQ14_[A-Z_]*MISMATCH[^\"]*' $O/$t.log | head -1)"; fi; rm -rf $O/obj_$t
}
case "$ST" in
main)
  python3 tools/hgi_sim/collq_gather_1018.py check > $O/check_d4g.log 2>&1; V "$(tail -1 $O/check_d4g.log)"
  python3 tools/hgi_sim/collq_gather_1018.py vectors $O/vec > $O/vec.log 2>&1 || V "vectors FAILED"
  python3 tools/hbm_next/hnx_coll_gq_train.py vectors-rows $O/vecr > $O/vecr.log 2>&1 || V "vectors-rows FAILED"
  ( python3 tools/hbm_next/hnx_coll_gq_train.py check-train > $O/check_train.log 2>&1; V "$(tail -1 $O/check_train.log)" ) &
  ( aq aq14 ) &
  build m 0
  run s0 m +set=0 & run s1 m +set=1 & run s2 m +set=2 &
  for f in 1 2 3 4; do run f$f m +set=0 +fault=$f & done
  run f5 m +set=1 +fault=5 &
  wait
  grep -h '^COLLQ_TRAIN' $O/s1.log $O/s2.log > $O/cycles_N.txt
  rm -rf $O/obj_m ;;
aqec) aq aqec -DOT_HNX_AQ_MUT_EC ;;
aqrs) aq aqrs -DOT_HNX_AQ_MUT_RS ;;
aql)  aq aql -GLMUT=1 ;;
m*)
  m=${ST#m}
  python3 tools/hbm_next/hnx_coll_gq_train.py vectors-rows $O/vecr > $O/vecr.log 2>&1 || V "vectors-rows FAILED"
  python3 tools/hgi_sim/collq_gather_1018.py vectors $O/vec > $O/vec.log 2>&1 || V "vectors FAILED"
  build $ST $m; if [ "$m" = 9 ] || [ "$m" = 2 ]; then run $ST $ST +set=0; else run $ST $ST +set=1; fi; rm -rf $O/obj_$ST ;;
esac
V "done"
