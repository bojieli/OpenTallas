#!/bin/bash
# KV-KITS-ATTN 2026-10-18: kit bench of qkd_pv_fin_s at the die's parameters (kv_static_die qkd_pvfin: ADD_LAT 7, MUL_LAT 6,
# SKEW 1), Verilator 5.050 (the closure daemon's pinned tool).  tb_qkd_pv_fin_s = lockstep against the reference
# ot_qwen_tp8_pv_join16_static_cal slices (bit-exact blocks, beat b = reference + 1 + b), QXF-FACE b6d08acc2 version.
#   run_qkd_pv_fin_s_kit.sh OUT M
#   M=0: lockstep R <= max(P0, P1) (+N=40) AND the die's STRETCH=1 regimes (+N=48) AND the 3 negative controls (DUT fault)
#        -> one line "PVFIN_KIT PASS mut=0 ..." only if all five pass
#   M=1: reciprocal head index (b + 1) / 8        M=2: pair-0 operand one tap late       M=3: R left out of the join age
#        -> the RTL mutant on the stretched lockstep; "PVFIN_KIT FAIL mut=M ..." when the bench catches it
# Exit 0 only on a PVFIN_KIT PASS line.  Run from the repository root (on the fleet via ot-run).
set -u
O=$1; M=${2:-0}
mkdir -p "$O"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
[ -x "$V" ] || V=verilator
S=rtl/qwen_sys/split_20261014
SRC=("$S/qkd_pv_fin_s.sv" rtl/hdc/nearhbm/ot_qwen_tp8_pv256_finalize_static_cal_gen.sv rtl/hdc/ot_hdc_fp32_add_lat.sv
     rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv rtl/test/qwen_split/tb_qkd_pv_fin_s.sv)
sha256sum "${SRC[@]}" "$0" > "$O/source.sha256"
echo "SIM $($V --version)"
$V --binary --timing -j "${JOBS:-4}" -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTH -Wno-MULTIDRIVEN \
   --top-module tb_qkd_pv_fin_s -GMUT="$M" -GSKEW=1 --Mdir "$O/obj" "${SRC[@]}" > "$O/build.log" 2>&1 \
   || { grep -m5 %Error "$O/build.log"; echo "PVFIN_KIT FAIL mut=$M build"; exit 1; }
B=$O/obj/Vtb_qkd_pv_fin_s
run() { "$B" "$@" 2>&1 | grep -vE '^- (S i m|Verilator:)' ; }
if [ "$M" = 0 ]; then
  a=$(run +SEED=7 +N=40); b=$(run +SEED=9 +N=48 +STRETCH=1)
  n1=$(run +SEED=5 +N=6 +NEG=1); n2=$(run +SEED=5 +N=6 +NEG=2); n3=$(run +SEED=5 +N=6 +NEG=3)
  printf '%s\n' "$a" "$b" "$n1" "$n2" "$n3" | grep -E 'PASS|FAIL|MISMATCH' | head -12
  ok=1
  grep -qE '^PASS STRETCH=0 40 commands' <<< "$a" || ok=0
  grep -qE '^PASS STRETCH=1 48 commands' <<< "$b" || ok=0
  for n in "$n1" "$n2" "$n3"; do grep -q 'DUT fault raised (expected) -- PASS' <<< "$n" || ok=0; done
  if [ $ok = 1 ]; then echo "PVFIN_KIT PASS mut=0 lockstep STRETCH=0 40 cmds + STRETCH=1 48 cmds bit-exact, NEG 1-3 faulted (SKEW 1)"; exit 0; fi
  echo "PVFIN_KIT FAIL mut=0 (see above)"; exit 1
fi
r=$(run +SEED=9 +N=48 +STRETCH=1)
grep -E 'PASS|FAIL|MISMATCH|fault' <<< "$r" | head -6
if grep -qE '^PASS STRETCH=1' <<< "$r"; then echo "PVFIN_KIT PASS mut=$M (mutant NOT detected)"; exit 0; fi
echo "PVFIN_KIT FAIL mut=$M detected ($(grep -cE '^MISMATCH|fault' <<< "$r") mismatch/fault lines)"; exit 1
