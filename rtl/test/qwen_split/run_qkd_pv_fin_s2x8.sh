#!/bin/bash
# KV-PVFIN-1 2026-11-13: equivalence bench of the lane-sliced pv_fin pair (qkd_pv_fin_s2x8 = 2 x qkd_pv_fin_s8) against
# the unsliced qkd_pv_fin_s, lock-step on the same pins, every edge (0 added cycles).  Verilator 5.050.
#   run_qkd_pv_fin_s2x8.sh OUT
# PASS (exit 0, one line "PVFIN_S2X8_KIT PASS ...") only if: SKEW 1 (the kit) and SKEW 2, 3 seeds each, all PASS; and every
# negative control FAILS: slice MUT 1 / 2 / 3, the lane-swap wiring mutant, and +SHIFT=1 (a wrongly declared +1 cycle).
set -u
O=$1; mkdir -p "$O"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
[ -x "$V" ] || V=verilator
S=rtl/qwen_sys/split_20261014
SRC=("$S/qkd_pv_fin_s.sv" "$S/qkd_pv_fin_s8.sv" rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv
     rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv rtl/test/qwen_split/tb_qkd_pv_fin_s2x8.sv)
sha256sum "${SRC[@]}" "$0" > "$O/source.sha256"
echo "SIM $($V --version)"
build() {  # tag skew mut [defines]
  $V --binary --timing -j "${JOBS:-8}" -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTH -Wno-MULTIDRIVEN \
     --top-module tb_qkd_pv_fin_s2x8 -GMUT="$3" -GSKEW="$2" ${4:-} --Mdir "$O/obj_$1" "${SRC[@]}" > "$O/build_$1.log" 2>&1 \
     || { grep -m5 %Error "$O/build_$1.log"; echo "BUILD_FAIL $1"; return 1; }
}
run() { local t=$1; shift; "$O/obj_$t/Vtb_qkd_pv_fin_s2x8" "$@" 2>&1 | grep -vE '^- (S i m|Verilator:)' | tee -a "$O/run_$t.log" | grep -E '^(PVFIN_S2X8|COVER)'; }
ok=1
for sk in 1 2; do
  build s$sk $sk 0 || { ok=0; continue; }
  for sd in 3 11 29; do r=$(run s$sk +SEED=$sd +N=300); echo "$r"; grep -q '^PVFIN_S2X8 PASS' <<< "$r" || ok=0; done
done
r=$(run s1 +SEED=3 +N=60 +SHIFT=1); echo "$r"
if grep -q '^PVFIN_S2X8 FAIL' <<< "$r"; then echo "NEGCTRL_CAUGHT shift=1"; else echo "NEGCTRL_SURVIVED shift=1"; ok=0; fi
for m in 1 2 3; do
  build m$m 1 $m || { ok=0; continue; }
  r=$(run m$m +SEED=3 +N=60); echo "$r"
  if grep -q '^PVFIN_S2X8 FAIL' <<< "$r"; then echo "MUTANT_CAUGHT mut=$m"; else echo "MUTANT_SURVIVED mut=$m"; ok=0; fi
done
build swap 1 0 -DOT_PVFIN_S2X8_MUTANT_LANESWAP || ok=0
r=$(run swap +SEED=3 +N=30); echo "$r"
if grep -q '^PVFIN_S2X8 FAIL' <<< "$r"; then echo "MUTANT_CAUGHT laneswap"; else echo "MUTANT_SURVIVED laneswap"; ok=0; fi
if [ $ok = 1 ]; then echo "PVFIN_S2X8_KIT PASS lockstep vs qkd_pv_fin_s SKEW 1+2 x 3 seeds x 300 cmds, 0 cycles; negatives shift1 mut1-3 laneswap caught"; exit 0; fi
echo "PVFIN_S2X8_KIT FAIL"; exit 1
