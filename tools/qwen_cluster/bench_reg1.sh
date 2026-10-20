#!/bin/bash
# Region bench of the CB16 representative landed region c1r1 (rtl/physical/qcluster/qfd_c_b16_reg1.sv: qfd_c_b16_reg1
# ring-pair alignment vs qfd_c_b16_reg1b three-relay alignment), Verilator 5.050 (the closure daemon's pin).
# usage: bench_reg1.sh OUTDIR [CASE...]      run from the repo root; CASE in MUT0 MUT0W M1 M2 M3 M4 (default: all)
#   MUT0  : unmutated, neighbour phases within the landing contract    -> must print REG1_PASS MUT0
#   MUT0W : unmutated, wide +-0.45 T neighbour phases                   -> must print REG1_PASS MUT0 PHS=1
#   M1    : reg1 ring-pair reader read epoch K 3 (sed: bench-side child qfd_c_land_r257_narrow_k3)
#   M2    : own-region reset leaf rr_leg_1_1b_y_w one stage longer (RDL 7, both tops)
#   M3    : neighbour leaf lrst_leg_3_0a_4_r released one edge late (tb-side)
#   M4    : reg1 leg-2_0a crossing input bits la_i[0] / la_i[1] swapped (reg1 only)
# Each mutant must FAIL with its regex (MUTRE below); exit 0 only if every case behaves.  Mutants are scratch copies
# under OUTDIR; the generated RTL and the generator are never edited.
set -uo pipefail
OUT=$(mkdir -p "$1" && realpath "$1"); shift
CASES=${*:-MUT0 MUT0W M1 M2 M3 M4}
V=${VERILATOR:-/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --version
DUT=rtl/physical/qcluster/qfd_c_b16_reg1.sv
KIDS="rtl/physical/qcluster/qfd_c_land_safe.sv rtl/physical/qcluster/qfd_c_stn.sv rtl/physical/qcluster/qfd_c_xstn_safe.sv"
TB="tools/qwen_cluster/tb_a0_model_reg1.sv tools/qwen_cluster/tb_reg1_mut.sv tools/qwen_cluster/tb_qfd_c_b16_reg1.sv"
PLAN=results/arch/qwen_cluster_1017/q_cluster16/reg1/plan.json
LAT=$(python3 tools/qwen_cluster/reg1_latency.py "$PLAN") || { echo "REG1_BENCH_EXIT 1 (plan latencies)"; exit 1; }
echo "plan latencies: $LAT"
declare -A MUTRE=(
 [M1]='REG1_EPOCH_FAIL side=r edge=[0-9]+ exp=32 sel=0010 tb\.u1\.u_p_2_0a_r(lo|hi)\.'
 [M2]='REG1_EPOCH_FAIL side=w edge=33 exp=32 .*tb\.u[12]\.u_l_leg_1_1b_y_w(lo|hi)\.'
 [M3]='REG1_EPOCH_FAIL side=r edge=33 exp=32 .*tb\.u[12]\.u_l_leg_3_0a_4_r(lo|hi)\.'
 [M4]='REG1_EQ_MISMATCH out=lt_o edge=[0-9]+ first_bit=[01] ')
rc=0
for C in $CASES; do
 S="$OUT/src_$C"; mkdir -p "$S"; cp "$DUT" "$S/qfd_c_b16_reg1.sv"; F="$S/qfd_c_b16_reg1.sv"
 MUT=0; PHS=0
 case $C in
  MUT0) ;;
  MUT0W) PHS=1;;
  M1) sed -i 's/qfd_c_land_r257_narrow u_p_2_0a_r/qfd_c_land_r257_narrow_k3 u_p_2_0a_r/' "$F";;
  M2) sed -i -e 's/reg \[4:0\] rr_leg_1_1b_y_w;/reg [5:0] rr_leg_1_1b_y_w;/' \
             -e 's/{rr_leg_1_1b_y_w\[3:0\], rpin_q}/{rr_leg_1_1b_y_w[4:0], rpin_q}/' \
             -e 's/rr_leg_1_1b_y_w\[4\])/rr_leg_1_1b_y_w[5])/' "$F";;
  M3) MUT=3;;
  M4) sed -i '0,/\.i({la_i\[256:0\]})/s//.i({la_i[256:2], la_i[0], la_i[1]})/' "$F";;
  *) echo "unknown case $C"; rc=1; continue;;
 esac
 diff "$DUT" "$F" > "$OUT/$C.diff"; nd=$(grep -c '^>' "$OUT/$C.diff")
 echo "== $C: source lines mutated: $nd"
 if [[ $C == M1 || $C == M2 || $C == M4 ]] && [[ $nd == 0 ]]; then echo "REG1_BENCH case $C: sed matched nothing"; rc=1; continue; fi
 B="$OUT/obj_$C"
 bld() { "$V" --binary --timing -j 8 -Wno-fatal --top-module tb -GMUT=$MUT -GPHS=$PHS $LAT -Mdir "$B" \
         $TB $KIDS "$F" > "$OUT/build_$C.log" 2>&1; }
 if ! bld; then
  if grep -qiE 'pch|precompiled|No such file' "$OUT/build_$C.log"; then echo "retry build $C (PCH race)"; rm -rf "$B"; bld; fi
 fi
 [[ -x "$B/Vtb" ]] || { echo "REG1_BENCH case $C: build failed"; tail -30 "$OUT/build_$C.log"; rc=1; continue; }
 "$B/Vtb" > "$OUT/$C.log" 2>&1; xrc=$?
 grep -vE '^REG1_EPOCH side|^REG1_FIRST_WORD' "$OUT/$C.log" | tail -25
 echo "   ($(grep -cE '^REG1_EPOCH side|^REG1_FIRST_WORD' "$OUT/$C.log") per-crossing epoch / first-word lines, sim exit $xrc)"
 if [[ $C == MUT0* ]]; then
  if [[ $xrc == 0 ]] && grep -q "REG1_PASS MUT0 PHS=$PHS" "$OUT/$C.log"; then echo "REG1_BENCH $C PASS"; else echo "REG1_BENCH $C UNEXPECTED FAIL"; rc=1; fi
 else
  if [[ $xrc != 0 ]] && ! grep -q REG1_PASS "$OUT/$C.log" && grep -qE "${MUTRE[$C]}" "$OUT/$C.log"; then
   echo "REG1_BENCH $C FAILS AS REQUIRED /${MUTRE[$C]}/"
  else echo "REG1_BENCH $C NOT CAUGHT (exit $xrc, regex /${MUTRE[$C]}/)"; rc=1; fi
 fi
done
echo "REG1_BENCH_EXIT $rc CASES=$CASES"
exit $rc
