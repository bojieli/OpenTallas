#!/bin/bash
# QW-CB16FULL full-parent lockstep bench: qfd_c_b16_dv (soft source of truth) vs qfd_c_b16_full / qfd_c_b16_fullb
# (rtl/physical/qcluster/qfd_c_b16_full.sv), every output bit every cycle (tools/qwen_cluster/tb_full_lockstep.sv),
# Verilator 5.050 (closure daemon pin).  usage (repo root): bench_full_lockstep.sh OUTDIR [CASE...]
#   MUT0 (FAR 0 and 1)       must print FULL_LOCKSTEP_PASS
#   F1 F6 = fabric MUT 1 / 6; F8 reset-slip is covered independently by bench_cb16_reset_calendar.sh
#   fabric MUT 1 / 6 / 8 in qfd_c_b16_full (leg delay / landing read slot K / region reset slip), B3 = fabric
#   MUT 3 in qfd_c_b16_fullb (dn2 relay one edge late): each must FAIL with FULL_LOCKSTEP_MISMATCH dut=<that kit>
#   (or a LAND_FAULT for F6), the other DUT staying clean.
set -uo pipefail
OUT=$(mkdir -p "$1" && realpath "$1"); shift
CASES=${*:-MUT0 F1 F6 B3}
V=${VERILATOR:-/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator}
SRC=(tools/qwen_cluster/tb_a0_model_full.sv rtl/physical/qcluster/qfd_q3h_stn.sv
     rtl/physical/qcluster/qfd_c_stn.sv rtl/physical/qcluster/qfd_c_xstn_safe.sv rtl/physical/qcluster/qfd_c_land.sv
     rtl/physical/qcluster/qfd_c_land_r1h.sv rtl/physical/qcluster/qfd_c_b16_dv_fabric.sv rtl/physical/qcluster/qfd_c_b16_dv.sv
     rtl/physical/qcluster/qfd_c_b16_full.sv rtl/qwen_sys/dvm_20261014/ot_qfd_xslice_slots.sv rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv
     rtl/hdc/ot_hdc_delay.sv tools/qwen_cluster/tb_full_lockstep.sv)
{ sha256sum "${SRC[@]}" "$0"; "$V" --version; } > "$OUT/sources.sha256"; cat "$OUT/sources.sha256"
declare -A MFv=([MUT0]=0 [F1]=1 [F6]=6 [F8]=8 [B3]=0) MBv=([MUT0]=0 [F1]=0 [F6]=0 [F8]=0 [B3]=3)
declare -A RE=([F1]='FULL_LOCKSTEP_MISMATCH dut=full ' [F6]='FULL_LOCKSTEP_MISMATCH dut=full |LAND_FAULT .*u_f\.' [F8]='FULL_LOCKSTEP_MISMATCH dut=full |LAND_FAULT .*u_f\.' [B3]='FULL_LOCKSTEP_MISMATCH dut=fullb ')
rc=0
for C in $CASES; do
 B="$OUT/obj_$C"; S="$OUT/src_$C"; mkdir -p "$S"; F="$S/qfd_c_b16_full.sv"
 sed -e "s/^    qfd_c_b16_full_fabric u_fab (/    qfd_c_b16_full_fabric #(.MUT(${MFv[$C]})) u_fab (/" \
     -e "s/^    qfd_c_b16_fullb_fabric u_fab (/    qfd_c_b16_fullb_fabric #(.MUT(${MBv[$C]})) u_fab (/" rtl/physical/qcluster/qfd_c_b16_full.sv > "$F"
 nd=$(diff rtl/physical/qcluster/qfd_c_b16_full.sv "$F" | grep -c '^>'); echo "== $C: MF=${MFv[$C]} MB=${MBv[$C]} (fabric instance lines set: $nd of 2)"
 [[ $nd == 2 ]] || { echo "FULL_LOCKSTEP_BENCH $C: MUT sed failed"; rc=1; continue; }
 bld() { "$V" --binary --timing -j 16 -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN --top-module tb \
        -GMF=${MFv[$C]} -GMB=${MBv[$C]} -Mdir "$B" "${SRC[@]/rtl\/physical\/qcluster\/qfd_c_b16_full.sv/$F}" > "$OUT/build_$C.log" 2>&1; }
 bld || { echo "retry build $C"; rm -rf "$B"; bld; }
 [[ -x "$B/Vtb" ]] || { echo "FULL_LOCKSTEP_BENCH $C: build failed"; grep -m10 -i error "$OUT/build_$C.log"; rc=1; continue; }
 if [[ $C == MUT0 ]]; then
  for F in 0 1; do ARG=""; [[ $F == 1 ]] && ARG="+FAR"
   (cd "$OUT" && "$B/Vtb" $ARG ${CB16_DIAG_ARGS:-}) > "$OUT/${C}_far$F.log" 2>&1; x=$?; grep -E "FULL_LOCKSTEP|LAND_FAULT|Error" "$OUT/${C}_far$F.log" | head -5
   if [[ $x == 0 ]] && grep -q "FULL_LOCKSTEP_PASS FAR=$F" "$OUT/${C}_far$F.log" && ! grep -q LAND_FAULT "$OUT/${C}_far$F.log"; then echo "FULL_LOCKSTEP_BENCH MUT0 FAR=$F PASS"; else echo "FULL_LOCKSTEP_BENCH MUT0 FAR=$F UNEXPECTED FAIL"; rc=1; fi
  done
 else
  (cd "$OUT" && "$B/Vtb" ${CB16_DIAG_ARGS:-}) > "$OUT/$C.log" 2>&1; x=$?; grep -E "FULL_LOCKSTEP|LAND_FAULT" "$OUT/$C.log" | head -5
  clean_other=0
  if [[ ${MFv[$C]} != 0 ]]; then grep -q 'mism_fullb=0$' "$OUT/$C.log" && clean_other=1
  else grep -q 'mism_full=0 ' "$OUT/$C.log" && clean_other=1; fi
  if [[ $x != 0 && $clean_other == 1 ]] && ! grep -q FULL_LOCKSTEP_PASS "$OUT/$C.log" && grep -qE "${RE[$C]}" "$OUT/$C.log"; then echo "FULL_LOCKSTEP_BENCH $C FAILS AS REQUIRED"; else echo "FULL_LOCKSTEP_BENCH $C NOT CAUGHT (exit $x)"; rc=1; fi
 fi
done
echo "FULL_LOCKSTEP_BENCH_EXIT $rc CASES=$CASES"; exit $rc
