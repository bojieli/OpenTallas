#!/bin/bash
# LH-P3UNITS/FUSHUB 2026-10-19: FUSED die csum tree + hub benches (fleet, Verilator 5.050), on ot_hnx_fused_tree_top
# (32 lanes + 28 tree nodes + hub wired as DIE f4c_t9p3, links = relay stations + landings, E = 2).  Run from a bundle
# root (git archive of the branch) on a fleet host:  tools/hbm_next/hnx_fushub_bench.sh OUT STAGE
#   lint  lint of tb_hnx_fused_tree
#   t0    MUT 0: HC_PRE_NORM and HC_POST, N = 1,2,3,4,6, rgap 0, ph 0 -> HNX_FUSED PASS each (golden chunk8, exact)
#   phr   MUT 0: HC_PRE_NORM N 4 ph 3 -> the hub REFUSES it: PH_REFUSE PASS (fault, 0 writes); HC_POST N 2 ph 5 (no
#         cross-lane reduction, ph free) -> HNX_FUSED PASS
#   ref   ot_hnx_fused_top (rotating star top) on the same ph 3 / ph 5 vectors -> HNX_FUSED PASS (the vectors are valid)
#   m4    MUT 4 heap not cleared on consume                        -> HNX_FUSED FAIL
#   m7    MUT 7 hub accepts HC_PRE_NORM ph != 0 (N 4 ph 3, N 2 ph 5) -> HNX_FUSED FAIL mism (fixed tree != golden order)
#   m8    MUT 8 lanes 2 / 4 of quadrant 0 swap tree positions      -> HNX_FUSED FAIL mism (wrong tree order)
#   m9    MUT 9 quadrant 0 n2L pad one edge short                  -> HNX_FUSED FAIL (misaligned chunk sums: fault)
set -u
B=$(pwd); O=$(realpath -m "${1:?OUT}"); ST=${2:?STAGE}; mkdir -p "$O"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
VL=$(command -v verilator); echo "verilator: $VL $($VL --version)" > "$O/verilator.txt"
V(){ echo "$(date -Is) $*" | tee -a "$O/verdict_$ST.txt"; }
V "start host=$(hostname) bundle=$(cat $B/BUNDLE_COMMIT 2>/dev/null) $(cat $O/verilator.txt)"
LIB=(rtl/hbm_next/fused/ot_hnx_fused_eng.sv
  physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
  rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_delay_ring.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv
  rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv
  rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_f12.sv
  rtl/hdc/v41x/ot_dsrom_divc.sv rtl/hdc/v41x/ot_dsrom_fp32_add_l6.sv rtl/hdc/v41x/ot_dsrom_su_add6.sv
  rtl/hdc/v41x/ot_dsrom_su_norm.sv rtl/hdc/v41x/ot_dsrom_su_hcpost.sv rtl/hdc/v41/ot_hdc_actquant.sv
  rtl/hdc/v41x/ot_dsrom_aq12.sv rtl/lib/ot_rst_relay.sv)
if [ "$ST" = ref ]; then
  SRC=(rtl/hbm_next/fused/tb/tb_hnx_fused.sv "${LIB[@]}"); TOP=tb_hnx_fused; VLT=tools/hbm_next/hnx_fused.vlt
else
  SRC=(rtl/hbm_next/fused/tb/tb_hnx_fused_tree.sv rtl/hbm_next/fused/tb/ot_hnx_fused_tree_top.sv rtl/hbm_next/fused/ot_hnx_fused_tree.sv
       physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1/ot_sram_1r1w2c_32x64_m1.v "${LIB[@]}")
  TOP=tb_hnx_fused_tree; VLT=tools/hbm_next/hnx_fushub.vlt
fi
VF=($VLT --hierarchical -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT --top-module $TOP)
if [ "$ST" = lint ]; then
  verilator --lint-only --timing "${VF[@]}" "${SRC[@]}" > $O/lint.log 2>&1
  V "lint rc=$? errors=$(grep -c '%Error' $O/lint.log)"; grep '%Error' $O/lint.log | head -20 | tee -a "$O/verdict_$ST.txt"
  V "done"; exit 0
fi
gen(){ # dir op n rgap ph
  [ -f "$1/plus.txt" ] || python3 tools/hbm_next/hnx_fused_vec.py --op $2 --n $3 --rgap $4 --ph $5 --out $1 > $1.gen.log 2>&1 || V "vector gen $1 FAILED"
}
build(){ # tag "-G..."
  local d=$O/obj_$1; rm -rf $d
  verilator --binary --timing -O1 -j 16 "${VF[@]}" $2 -Mdir $d -o V$1 "${SRC[@]}" > $O/build_$1.log 2>&1 || {
    sleep 5; verilator --binary --timing -O1 -j 4 "${VF[@]}" $2 -Mdir $d -o V$1 "${SRC[@]}" > $O/build_$1.log 2>&1; }
  V "build $1 rc=$? bin=$( [ -x $d/V$1 ] && echo ok || echo MISSING)"
}
run(){ # tag op n rgap ph
  local t=$1 c=$2_n$3_g$4_p$5; local od=$O/run_${t}_$c; rm -rf $od; mkdir -p $O/cases
  gen $O/cases/$c $2 $3 $4 $5; cp -r $O/cases/$c $od
  ( cd $od && $O/obj_$t/V$t $(cat plus.txt) > run.log 2>&1; echo RUN_RC=$? >> run.log
    local r; r=$(grep -h 'HNX_FUSED_CYCLES\|HNX_FUSED PASS\|HNX_FUSED FAIL' run.log | tr '\n' ' ')
    if [ "$t" = phr ] && [ "$2" = pre ]; then   # refusal: the record must FAULT with no lane activity
      if echo "$r" | grep -q 'fault=1 done=0 bankerr=0 writes=0'; then r="$r PH_REFUSE PASS"; else r="$r PH_REFUSE FAIL"; fi
    fi
    V "$t $c: $r $(grep -h MISMATCH run.log | head -1)"
    [ "$t" = t0 ] && grep -h '^HNX_TREE' run.log | sort -u >> $O/tree_schedule.txt
    rm -f vmi.mem vme.mem )
}
case $ST in
  t0)  build t0 "-GKX=4 -GMUT=0"
       for op in pre post; do for n in 1 2 3 4 6; do run t0 $op $n 0 0 & done; done; wait ;;
  phr) build phr "-GKX=4 -GMUT=0"
       run phr pre 4 0 3 & run phr post 2 0 5 & wait ;;
  ref) build ref "-GKX=4 -GMUT=0"
       run ref pre 4 0 3 & run ref post 2 0 5 & wait ;;
  m4|m8|m9) k=${ST#m}; build $ST "-GKX=4 -GMUT=$k"
       run $ST pre 4 0 0 & wait ;;
  m7)  build m7 "-GKX=4 -GMUT=7"
       run m7 pre 4 0 3 & run m7 pre 2 0 5 & wait ;;
esac
rm -rf $O/obj_$ST
if [ "$ST" = phr ]; then
  V "$ST SUMMARY refuse=$(grep -c 'PH_REFUSE PASS' $O/verdict_$ST.txt) accept=$(grep -c 'PH_REFUSE FAIL' $O/verdict_$ST.txt) post_pass=$(grep -c ' phr post_.*HNX_FUSED PASS' $O/verdict_$ST.txt)"
else
  V "$ST SUMMARY pass=$(grep -c " $ST [a-z0-9_]*: .*HNX_FUSED PASS" $O/verdict_$ST.txt) fail=$(grep -c " $ST [a-z0-9_]*: .*HNX_FUSED FAIL" $O/verdict_$ST.txt) noresult=$(grep " $ST [a-z0-9_]*: " $O/verdict_$ST.txt | grep -vc 'HNX_FUSED PASS\|HNX_FUSED FAIL')"
fi
V "done"
