#!/bin/bash
# HBM-NEXT-UNITS-SUDMA 2026-10-19: SU.VOP N-row benches (fleet, Verilator 5.050). Run from a bundle root (git archive of
# the lane branch) on a fleet host:  tools/hbm_next/hnx_sudma_bench.sh OUT STAGE
#  g   indexed SU.VOP (route gather A[I] -> O): d4g single-row engine bench (tb_indexed_scalar, fixed_cycles) and the hnx
#      R-row engine (tb_hnx_su_indexed_rows, rows 1..8 on the real static VM banks): MUT 0 PASS (R1..R8 cycles),
#      MUT 1 (I row stride dropped) / 2 (O row stride dropped) / 3 (value pipe short) -> GATHER_ROWS FAIL (witnesses)
#  d   DMA.KVWB_DS N rows into the 256-slot window ring on the d4g die master ot_hgi_dma_back_static_vp4_banks (unchanged)
#      (tb_hnx_dma_kvwb_ring): MUT 0 PASS (R1..R6 + slots >= 128 + wraps split into two moves), MUT 1 (7-b ring index)
#      / 2 (no wrap split) / 3 (VM row stride dropped) -> KVWB_RING FAIL (witnesses)
#  s0  un-indexed SU.VOP on the WHOLE static SU (d4g ot_hbm_su_static_top unchanged) behind ot_hnx_su_rowx, MUT 0:
#      AB  N = 1,2,3,4,6 row-relative; AB N = 4 --absolute (the unrolled d4g image, row codes 0 = d4g bit for bit);
#      ABC N = 1,4,6; AB N = 4 --guard 0 (fill / lane-result store writes back to back) -> SU_ROWS PASS + SU_ROWS_EDGES
#  s1..s4  rowx mutant m (1 vmr sector stride, 2 control vb stride, 3 vmw sector stride, 4 store-row stride),
#      AB N = 4 row-relative -> SU_ROWS FAIL (fail witnesses)
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
case $ST in s0) M=0;; s1) M=1;; s2) M=2;; s3) M=3;; s4) M=4;; *) V "bad stage"; exit 2;; esac
gen(){ # case args...
  local c=$1; shift
  [ -f $O/vec_$c/programme.json ] || python3 tools/hbm_next/su_rows_compile.py $O/vec_$c "$@" > $O/vec_$c.log 2>&1 || V "vector gen $c FAILED"
}
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
