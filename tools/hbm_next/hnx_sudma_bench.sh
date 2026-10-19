#!/bin/bash
# HBM-NEXT-UNITS-SUDMA 2026-10-19: SU.VOP N-row benches (fleet, Verilator 5.050). Run from a bundle root (git archive of
# the lane branch) on a fleet host:  tools/hbm_next/hnx_sudma_bench.sh OUT STAGE
#  g   indexed SU.VOP (route gather A[I] -> O): d4g single-row engine bench (tb_indexed_scalar, fixed_cycles) and the hnx
#      R-row engine (tb_hnx_su_indexed_rows, rows 1..8 on the real static VM banks): MUT 0 PASS (R1..R8 cycles),
#      MUT 1 (I row stride dropped) / 2 (O row stride dropped) / 3 (value pipe short) -> GATHER_ROWS FAIL (witnesses)
#  d   DMA.KVWB_DS N rows into the 256-slot window ring on the d4g die master ot_hgi_dma_back_static_vp4_banks (unchanged)
#      (tb_hnx_dma_kvwb_ring): MUT 0 PASS (R1..R6 + slots >= 128 + wraps split into two moves), MUT 1 (7-b ring index)
#      / 2 (no wrap split) / 3 (VM row stride dropped) -> KVWB_RING FAIL (witnesses)
#  a   ARGMAX.LOCAL N rows (ot_hnx_argmax_static_rows on the actual SW VM slice, closed argmax18 engine): vectors
#      seeds 0..2 (hnx_argmax_rows_vectors.py), MUT 0 PASS, MUT 1 (A row stride) / 2 (O row stride) / 3 (id offset from
#      row 0) -> ARGMAX_ROWS FAIL (witnesses)
#  s0  un-indexed SU.VOP on the WHOLE static SU (d4g ot_hbm_su_static_top unchanged) behind ot_hnx_su_rowx, MUT 0:
#      AB  N = 1,2,3,4,6 row-relative; AB N = 4 --absolute (the unrolled d4g image, row codes 0 = d4g bit for bit);
#      ABC N = 1,4,6; AB N = 4 --guard 0 (fill / lane-result store writes back to back) -> SU_ROWS PASS + SU_ROWS_EDGES
#  s1..s4  rowx mutant m (1 vmr sector stride, 2 control vb stride, 3 vmw sector stride, 4 store-row stride),
#      AB N = 4 row-relative -> SU_ROWS FAIL (fail witnesses)
#  w0..w3 (SUDMA2 10-19) split store write phase: ot_hnx_su_top (ot_hnx_su_pgslice + ot_hnx_su_wsplit) behind rowx,
#      tb_hnx_su_rows_ws -GWMUT=m. w0: wsplit 1 AB N = 1,2,3,4,6 and ABC N = 1,4,6 (II = 2 k nv); wsplit 0 on the d4g
#      vectors ab_n1 / ab_n4 / abc_n1 (= d4g bit for bit: same expected writes and edges as stage s0); schedule-parity
#      witness ws_ab_n4_fw11 (lane writes on the wrong phase -> FAULT, must FAIL). w1 deferral dropped / w2 HI = 1
#      deferred / w3 deferred address not captured: ws_ab_n4 -> SU_ROWS FAIL (witnesses)
#  aw  (SUDMA2 10-19) wide ARGMAX.LOCAL ot_hnx_argmax_wide_rows (8 sectors a beat, engine LP 64), same SW VM slice:
#      vectors hnx_argmax_wide_vectors.py seeds 0..2: MUT 0 PASS (done edges exact: P1 67, P6 177), MUT 1/2/3 (as stage a),
#      4 beat bank rotation dropped, 5 last-beat sector mask dropped -> ARGMAX_ROWS FAIL; plus WS 1 PMIN 1 on the
#      ORIGINAL vectors (hnx_argmax_rows_vectors.py) -> PASS = the original reader edge for edge
#  p   (SUDMA2 10-19) ROW CODE AS PROGRAMME COLUMN: images ws_ab_n6 / ws_abc_n6 with the 20-b rc in the spare top bits
#      of column 9 (line 2442 b a quarter: pslice SB 2422 -> 2442, same 10 columns); su_programme_compile --line-bits
#      9768 --partition 4, d4g producers ot_hbm_su_programme_part PIPE 2 (= pslice_q4) vs monolithic, lockstep + golden
#      (tb_hnx_su_programme_rc = d4g tb, mono at PIPE 2): positive PASS; mutants template / pcoff (as d4g) and rcdrop (image compiled
#      without rc, golden with rc) -> SU_PROGRAMME_PART FAIL
set -u
B=$(pwd); O=$(realpath -m "${1:?OUT}"); ST=${2:?STAGE}; mkdir -p "$O"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
VL=$(command -v verilator); echo "verilator: $VL $($VL --version)" > "$O/verilator.txt"
V(){ echo "$(date -Is) $*" | tee -a "$O/verdict_$ST.txt"; }
V "start host=$(hostname) bundle=$(cat $B/BUNDLE_COMMIT 2>/dev/null)"
GA=rtl/hbm_accel/generic/adapters/static_su/gather
VMB=(rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v)
if [ "$ST" = g ]; then
  gb(){ # tag top mut srcs...
    local t=$1 top=$2 m=$3; shift 3; local d=$O/obj_$t; rm -rf $d
    verilator --binary --timing -j 4 -Wno-fatal --top-module $top -GMUT=$m -Mdir $d -o V$t "$@" "${VMB[@]}" > $O/build_$t.log 2>&1 || \
      { sleep 5; verilator --binary --timing -j 1 -Wno-fatal --top-module $top -GMUT=$m -Mdir $d -o V$t "$@" "${VMB[@]}" > $O/build_$t.log 2>&1; }
    ( cd $O && $d/V$t > $O/$t.log 2>&1; echo RUN_RC=$? >> $O/$t.log )
    V "$t: $(grep -h 'GATHER_NATIVE\|GATHER_ROWS\|RUN_RC' $O/$t.log | head -2 | tr '\n' ' ')"; rm -rf $d
  }
  gb g_d4g tb_indexed_scalar 0 $GA/ot_hbm_su_indexed_scalar.sv $GA/tb_indexed_scalar.sv &
  for m in 0 1 2 3; do gb g_m$m tb_hnx_su_indexed_rows $m rtl/hbm_next/su/ot_hnx_su_indexed_scalar_rows.sv rtl/hbm_next/su/tb/tb_hnx_su_indexed_rows.sv & done
  wait; V "done"; exit 0
fi
if [ "$ST" = d ]; then
  PS=rtl/hbm_accel/generic/peers/static
  for m in 0 1 2 3; do (
    d=$O/obj_d$m; rm -rf $d
    verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_hnx_dma_kvwb_ring -GMUT=$m -Mdir $d -o Vd$m \
      rtl/hbm_next/dma/tb/tb_hnx_dma_kvwb_ring.sv $PS/ot_hgi_dma_back_static_vp4_banks.sv $PS/ot_hgi_dma_back_static_vp_banks.sv \
      "${VMB[@]}" physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v > $O/build_d$m.log 2>&1
    ( cd $O && $d/Vd$m > $O/d_m$m.log 2>&1; echo RUN_RC=$? >> $O/d_m$m.log )
    V "d_m$m: $(grep -h 'KVWB_RING\|RUN_RC' $O/d_m$m.log | head -2 | tr '\n' ' ')"; rm -rf $d ) &
  done
  wait; V "done"; exit 0
fi
if [ "$ST" = p ]; then
  PS=rtl/hbm_accel/generic/adapters/static_su/programme
  PM=physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
  for c in ws_ab_n6 ws_abc_n6; do (
    case $c in ws_ab_n6) a="--n 6 --wsplit 1";; *) a="--n 6 --op ABC --wsplit 1";; esac
    python3 tools/hbm_next/su_rows_compile.py $O/vec_$c $a > $O/vec_$c.log 2>&1 || V "vector gen $c FAILED"
    P=$O/p_$c; X=$O/p_${c}_rcdrop; mkdir -p $P $X
    python3 tools/hbm_static/su_programme_compile.py $O/vec_$c/prog_rc.mem $P/mono --line-bits 9768 > $P/mono.log 2>&1
    python3 tools/hbm_static/su_programme_compile.py $O/vec_$c/prog_rc.mem $P --line-bits 9768 --partition 4 --start-depth 2 --mut-pc-slice 3 > $P/part.log 2>&1
    python3 tools/hbm_static/su_programme_compile.py $O/vec_$c/prog_rc0.mem $X/mono --line-bits 9768 > $X/mono.log 2>&1
    python3 tools/hbm_static/su_programme_compile.py $O/vec_$c/prog_rc0.mem $X --line-bits 9768 --partition 4 --start-depth 2 > $X/part.log 2>&1
    cp $P/expected.mem $X/expected.mem
    V "$c compile: $(tail -1 $P/part.log | cut -c1-300)"
    for m in 0 1; do
      verilator --binary --timing -O1 -j 4 -Wno-fatal -Wno-WIDTHTRUNC -Wno-WIDTHEXPAND --top-module tb_hnx_su_programme_rc \
        -I$P -GMUT=$m -GPIPE=2 --Mdir $P/obj$m $PS/ot_hbm_su_programme.sv $PS/ot_hbm_su_programme_root.sv \
        $PS/ot_hbm_su_programme_part.sv rtl/hbm_next/su/tb/tb_hnx_su_programme_rc.sv $PM > $P/build$m.log 2>&1 || V "$c build $m FAILED"
    done
    for r in "0 _ positive $P" "0 +MUT_TEMPLATE template $P" "0 +MUT_PCOFF pcoff $P" "1 _ phase $P" "0 _ rcdrop $X"; do
      set -- $r; a=$2; [ "$a" = _ ] && a=""
      $P/obj$1/Vtb_hnx_su_programme_rc +DIR=$4 $a > $O/p_${c}_$3.log 2>&1; echo RUN_RC=$? >> $O/p_${c}_$3.log
      V "p $c $3: $(grep -h 'SU_PROGRAMME_PART PASS\|SU_PROGRAMME_PART FAIL\|RUN_RC' $O/p_${c}_$3.log | head -2 | tr '\n' ' ')"
    done
    rm -rf $P/obj0 $P/obj1 ) &
  done
  wait; V "done"; exit 0
fi
if [ "$ST" = aw ]; then
  AS=(rtl/hbm_next/argmax/ot_hnx_argmax_wide_rows.sv physical/hbm_generic/argmax18/rtl/ot_hgi_argmax18_m.sv
   physical/hbm_generic/argmax18/rtl/ot_hgi_argmax18_value_m.sv physical/hbm_mtp/rtl/ot_dshbm_argmax_m.sv
   rtl/gpu/ot_gpu_fadd.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv
   rtl/hbm_accel/index/ot_hbm_idx_vm_share_static.sv
   rtl/hbm_accel/generic/vm/static/hfd_hgi_vms_static.sv rtl/hbm_accel/generic/vm/static/ot_vms_slice_static.sv
   rtl/hbm_accel/generic/vm/static/ot_vms_hub_static.sv rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv
   rtl/hbm_accel/generic/vm/static/ot_vms_rstop_static.sv rtl/hbm_accel/generic/vm/static/ot_vms_rcl_static.sv
   rtl/hbm_accel/generic/vm/static/ot_vms_status_static.sv
   physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
   rtl/hbm_next/argmax/tb/tb_hnx_argmax_wide.sv)
  for sd in 0 1 2; do python3 tools/hbm_next/hnx_argmax_wide_vectors.py $O/wvec$sd $sd > $O/wvec$sd.log 2>&1 || V "wide vectors seed $sd FAILED"; done
  python3 tools/hbm_next/hnx_argmax_rows_vectors.py $O/ovec0 0 > $O/ovec0.log 2>&1 || V "orig vectors FAILED"
  V "vectors: $(head -1 $O/wvec0.log)"
  for m in 0 1 2 3 4 5 o; do (
    d=$O/obj_aw$m; rm -rf $d; P="-GMUT=$m"; [ $m = o ] && P="-GMUT=0 -GWS=1 -GPMIN=1"
    verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_hnx_argmax_wide $P -Mdir $d -o Vaw$m \
      "${AS[@]}" > $O/build_aw$m.log 2>&1
    if [ $m = o ]; then SDS=o; else SDS="0 1 2"; fi
    for sd in $SDS; do vd=$O/wvec$sd; [ $sd = o ] && vd=$O/ovec0
      ( cd $vd && $d/Vaw$m > $O/aw_m${m}_s$sd.log 2>&1; echo RUN_RC=$? >> $O/aw_m${m}_s$sd.log )
      V "aw_m$m seed$sd: $(grep -h 'ARGMAX_ROWS\|RUN_RC' $O/aw_m${m}_s$sd.log | head -2 | tr '\n' ' ')"; done
    rm -rf $d ) &
  done
  wait; V "done"; exit 0
fi
if [ "$ST" = a ]; then
  AS=(rtl/hbm_next/argmax/ot_hnx_argmax_static_rows.sv physical/hbm_generic/argmax18/rtl/ot_hgi_argmax18_m.sv
   physical/hbm_generic/argmax18/rtl/ot_hgi_argmax18_value_m.sv physical/hbm_mtp/rtl/ot_dshbm_argmax_m.sv
   rtl/gpu/ot_gpu_fadd.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv
   rtl/hbm_accel/index/ot_hbm_idx_vm_share_static.sv
   rtl/hbm_accel/generic/vm/static/hfd_hgi_vms_static.sv rtl/hbm_accel/generic/vm/static/ot_vms_slice_static.sv
   rtl/hbm_accel/generic/vm/static/ot_vms_hub_static.sv rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv
   rtl/hbm_accel/generic/vm/static/ot_vms_rstop_static.sv rtl/hbm_accel/generic/vm/static/ot_vms_rcl_static.sv
   rtl/hbm_accel/generic/vm/static/ot_vms_status_static.sv
   physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
   rtl/hbm_next/argmax/tb/tb_hnx_argmax_rows.sv)
  for sd in 0 1 2; do python3 tools/hbm_next/hnx_argmax_rows_vectors.py $O/avec$sd $sd > $O/avec$sd.log 2>&1 || V "argmax vectors seed $sd FAILED"; done
  for m in 0 1 2 3; do (
    d=$O/obj_a$m; rm -rf $d
    verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_hnx_argmax_rows -GMUT=$m -Mdir $d -o Va$m \
      "${AS[@]}" > $O/build_a$m.log 2>&1
    for sd in 0 1 2; do ( cd $O/avec$sd && $d/Va$m > $O/a_m${m}_s$sd.log 2>&1; echo RUN_RC=$? >> $O/a_m${m}_s$sd.log )
      V "a_m$m seed$sd: $(grep -h 'ARGMAX_ROWS\|RUN_RC' $O/a_m${m}_s$sd.log | head -2 | tr '\n' ' ')"; done
    rm -rf $d ) &
  done
  wait; V "done"; exit 0
fi
S=rtl/hbm_accel/generic/adapters/static_su
SRC=($S/arithmetic/ot_hbm_su_static_ins.sv $S/arithmetic/ot_hbm_su_static_lane.sv $S/arithmetic/ot_hbm_su_static_side.sv
 $S/data_store/ot_hbm_su_static_data_store.sv $S/data_store/ot_hbm_su_static_pinned_bank.sv
 $S/register_file/ot_hbm_su_static_rf.sv $S/reduction/ot_hbm_su_reduce_static.sv $S/ot_hbm_su_static_vm_ports.sv
 $S/top/ot_hbm_su_static_pgslice.sv $S/top/ot_hbm_su_static_qcore.sv $S/top/ot_hbm_su_static_quarter.sv
 $S/top/ot_hbm_su_stree.sv $S/top/ot_hbm_su_static_top.sv rtl/hbm_next/su/ot_hnx_su_rowx.sv rtl/hbm_next/su/tb/tb_hnx_su_rows.sv
 rtl/hbm_accel/generic/peers/ot_hgi_su_unit.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv
 rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv
 rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv
 rtl/hdc/ot_hdc_fastfp_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv
 rtl/hdc/v41/ot_hdc_fsqrt.sv rtl/hdc/v41/ot_hdc_fdiv.sv rtl/hdc/v41/ot_hdc_softplus.sv
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v)
WM=-1
case $ST in s0) M=0;; s1) M=1;; s2) M=2;; s3) M=3;; s4) M=4;; w0) M=0;WM=0;; w1) M=0;WM=1;; w2) M=0;WM=2;; w3) M=0;WM=3;;
 *) V "bad stage"; exit 2;; esac
gen(){ # case args...
  local c=$1; shift
  [ -f $O/vec_$c/programme.json ] || python3 tools/hbm_next/su_rows_compile.py $O/vec_$c "$@" > $O/vec_$c.log 2>&1 || V "vector gen $c FAILED"
}
if [ $WM -ge 0 ]; then
  SRC+=(rtl/hbm_next/su/ot_hnx_su_wsplit.sv rtl/hbm_next/su/ot_hnx_su_pgslice.sv rtl/hbm_next/su/ot_hnx_su_quarter.sv
   rtl/hbm_next/su/ot_hnx_su_top.sv rtl/hbm_next/su/tb/tb_hnx_su_rows_ws.sv)
  SRC=("${SRC[@]/rtl\/hbm_next\/su\/tb\/tb_hnx_su_rows.sv/}")
  if [ $WM = 0 ]; then
   CASES="ws_ab_n1 ws_ab_n2 ws_ab_n3 ws_ab_n4 ws_ab_n6 ws_abc_n1 ws_abc_n4 ws_abc_n6 ab_n1 ab_n4 abc_n1 ws_ab_n4_fw11"
   for n in 1 2 3 4 6; do gen ws_ab_n$n --n $n --wsplit 1; done
   for n in 1 4 6; do gen ws_abc_n$n --n $n --op ABC --wsplit 1; done
   gen ab_n1 --n 1; gen ab_n4 --n 4; gen abc_n1 --n 1 --op ABC; gen ws_ab_n4_fw11 --n 4 --wsplit 1 --fw 11
  else
   CASES="ws_ab_n4"; gen ws_ab_n4 --n 4 --wsplit 1
  fi
  SRC=($(printf '%s\n' "${SRC[@]}" | grep -v '^$'))
  d=$O/obj_w$WM; rm -rf $d
  verilator --binary --timing --hierarchical -O1 -j ${JOBS:-8} -CFLAGS -O0 -Wno-fatal -Wno-lint -Wno-style \
    --top-module tb_hnx_su_rows_ws -GWMUT=$WM --Mdir $d "${SRC[@]}" > $O/build_w$WM.log 2>&1
  V "build w$WM rc=$? bin=$( [ -x $d/Vtb_hnx_su_rows_ws ] && echo ok || echo MISSING)"
  for c in $CASES; do
    read -r NE NW WS < <(python3 -c 'import json,sys;d=json.load(open(sys.argv[1]));print(d["edges"],d["expected_vm_writes"],d.get("wsplit",0))' $O/vec_$c/programme.json)
    ( $d/Vtb_hnx_su_rows_ws +DIR=$O/vec_$c +NE=$NE +NW=$NW +WSPLIT=$WS > $O/run_w${WM}_$c.log 2>&1; echo RUN_RC=$? >> $O/run_w${WM}_$c.log
      V "w$WM $c: $(grep -h 'SU_ROWS PASS\|SU_ROWS FAIL\|SU_ROWS_EDGES\|RUN_RC' $O/run_w${WM}_$c.log | head -3 | tr '\n' ' ')" ) &
  done
  wait; rm -rf $d
  V "done"; exit 0
fi
if [ $M = 0 ]; then
  CASES="ab_n1 ab_n2 ab_n3 ab_n4 ab_n6 ab_n4_abs abc_n1 abc_n4 abc_n6 ab_n4_g0"
  gen ab_n1 --n 1; gen ab_n2 --n 2; gen ab_n3 --n 3; gen ab_n4 --n 4; gen ab_n6 --n 6; gen ab_n4_abs --n 4 --absolute
  gen abc_n1 --n 1 --op ABC; gen abc_n4 --n 4 --op ABC; gen abc_n6 --n 6 --op ABC; gen ab_n4_g0 --n 4 --guard 0
else
  CASES="ab_n4"; gen ab_n4 --n 4
fi
d=$O/obj_s$M; rm -rf $d
verilator --binary --timing --hierarchical -O1 -j ${JOBS:-8} -CFLAGS -O0 -Wno-fatal -Wno-lint -Wno-style \
  --top-module tb_hnx_su_rows -GMUT=$M --Mdir $d "${SRC[@]}" > $O/build_s$M.log 2>&1
V "build s$M rc=$? bin=$( [ -x $d/Vtb_hnx_su_rows ] && echo ok || echo MISSING)"
for c in $CASES; do
  read -r NE NW < <(python3 -c 'import json,sys;d=json.load(open(sys.argv[1]));print(d["edges"],d["expected_vm_writes"])' $O/vec_$c/programme.json)
  ( $d/Vtb_hnx_su_rows +DIR=$O/vec_$c +NE=$NE +NW=$NW > $O/run_s${M}_$c.log 2>&1; echo RUN_RC=$? >> $O/run_s${M}_$c.log
    V "s$M $c: $(grep -h 'SU_ROWS PASS\|SU_ROWS FAIL\|SU_ROWS_EDGES\|RUN_RC' $O/run_s${M}_$c.log | head -3 | tr '\n' ' ')" ) &
done
wait; rm -rf $d
V "done"
