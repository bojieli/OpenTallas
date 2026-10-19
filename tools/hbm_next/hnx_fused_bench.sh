#!/bin/bash
# HBM-NEXT-UNITS-FUSED 2026-10-19: hnx FUSED N-row benches (fleet, Verilator 5.050).  Run from a bundle root (git
# archive of the lane branch) on a fleet host:  tools/hbm_next/hnx_fused_bench.sh OUT STAGE
#   lint   lint of tb_hnx_fused + ot_hnx_fused_top (catches elaboration errors before the full builds)
#   m0     KX 4 MUT 0: HC_PRE_NORM and HC_POST, N = 1,2,3,4,6, rgap 0 -> HNX_FUSED PASS each; HNX_FUSED_CYCLES(N)
#   k2     KX 2 MUT 0: HC_PRE_NORM N 4 at rgap 0 (must FAULT: x-slot collision) / 64 / 128 / 192
#   m1..m6 KX 4 MUT k: HC_PRE_NORM N 4 (m1, m2 also HC_POST N 4) -> HNX_FUSED FAIL (fail witnesses)
set -u
B=$(pwd); O=$(realpath -m "${1:?OUT}"); ST=${2:?STAGE}; mkdir -p "$O"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
VL=$(command -v verilator); echo "verilator: $VL $($VL --version)" > "$O/verilator.txt"
V(){ echo "$(date -Is) $*" | tee -a "$O/verdict_$ST.txt"; }
V "start host=$(hostname) bundle=$(cat $B/BUNDLE_COMMIT 2>/dev/null)"
SRC=(rtl/hbm_next/fused/tb/tb_hnx_fused.sv rtl/hbm_next/fused/ot_hnx_fused_eng.sv
  physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
  rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv
  rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv
  rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_f12.sv
  rtl/hdc/v41x/ot_dsrom_divc.sv rtl/hdc/v41x/ot_dsrom_fp32_add_l6.sv rtl/hdc/v41x/ot_dsrom_su_add6.sv
  rtl/hdc/v41x/ot_dsrom_su_norm.sv rtl/hdc/v41x/ot_dsrom_su_hcpost.sv rtl/hdc/v41/ot_hdc_actquant.sv
  rtl/hdc/v41x/ot_dsrom_aq12.sv rtl/lib/ot_rst_relay.sv)
VF=(tools/hbm_next/hnx_fused.vlt --hierarchical -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT --top-module tb_hnx_fused)
if [ "$ST" = lint ]; then
  verilator --lint-only --timing "${VF[@]}" "${SRC[@]}" > $O/lint.log 2>&1
  V "lint rc=$? errors=$(grep -c '%Error' $O/lint.log)"; grep '%Error' $O/lint.log | head -20 | tee -a "$O/verdict_$ST.txt"
  V "done"; exit 0
fi
gen(){ # dir op n rgap
  [ -f "$1/plus.txt" ] || python3 tools/hbm_next/hnx_fused_vec.py --op $2 --n $3 --rgap $4 --out $1 > $1.gen.log 2>&1 || V "vector gen $1 FAILED"
}
build(){ # tag "-G..."
  local d=$O/obj_$1; rm -rf $d
  verilator --binary --timing -O1 -j 16 "${VF[@]}" $2 -Mdir $d -o V$1 "${SRC[@]}" > $O/build_$1.log 2>&1 || {
    sleep 5; verilator --binary --timing -O1 -j 4 "${VF[@]}" $2 -Mdir $d -o V$1 "${SRC[@]}" > $O/build_$1.log 2>&1; }
  V "build $1 rc=$? bin=$( [ -x $d/V$1 ] && echo ok || echo MISSING)"
}
run(){ # tag op n rgap
  local t=$1 c=$2_n$3_g$4; local od=$O/run_${t}_$c; rm -rf $od; mkdir -p $O/cases
  gen $O/cases/$c $2 $3 $4; cp -r $O/cases/$c $od
  ( cd $od && $O/obj_$t/V$t $(cat plus.txt) > run.log 2>&1; echo RUN_RC=$? >> run.log
    V "$t $c: $(grep -h 'HNX_FUSED_CYCLES\|HNX_FUSED PASS\|HNX_FUSED FAIL' run.log | tr '\n' ' ') $(grep -h MISMATCH run.log | head -1)"
    rm -f vmi.mem vme.mem )
}
case $ST in
  m0) build m0 "-GKX=4 -GMUT=0"
      for op in pre post; do for n in 1 2 3 4 6; do run m0 $op $n 0 & done; done; wait ;;
  k2) build k2 "-GKX=2 -GMUT=0"
      for g in 0 64 128 192; do run k2 pre 4 $g & done; wait ;;
  m[1-6]) k=${ST#m}; build $ST "-GKX=4 -GMUT=$k"
      run $ST pre 4 0 &
      case $k in 1|2) run $ST post 4 0 & ;; esac
      wait ;;
esac
rm -rf $O/obj_$ST
# one summary line per stage (the kit benches match it): PASS / FAIL counts over this stage's cases
V "$ST SUMMARY pass=$(grep -c " $ST [a-z0-9_]*: .*HNX_FUSED PASS" $O/verdict_$ST.txt) fail=$(grep -c " $ST [a-z0-9_]*: .*HNX_FUSED FAIL" $O/verdict_$ST.txt) noresult=$(grep " $ST [a-z0-9_]*: " $O/verdict_$ST.txt | grep -vc 'HNX_FUSED PASS\|HNX_FUSED FAIL')"
V "done"
