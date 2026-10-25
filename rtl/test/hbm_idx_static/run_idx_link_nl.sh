#!/usr/bin/env bash
# HBM-BIND B2 (lane hbm-bind-idx 2026-10-24): ot_hbm_idx_topk_link_static NL bench (tb_idx_link_nl.sv).
#   PASS legs: NL 4 (default vs the unchanged as-built master), NL 2, NL 1 at OFF 0 and OFF 1.
#   FAIL legs (mutants): NL 1 LMUT 1 (record halves swapped), NL 1 LMUT 2 (emit sequence id), NL 1 LMUT 3 (last list not
#   ingested), NL 4 LMUT 3.
# Legs build and run in parallel (HBM-BIND gate 2026-10-24), then are checked in order.
# usage: run_idx_link_nl.sh OUT REFDIR   (REFDIR from mk_idx_b2_refs.sh); run from the repo root.
set -uo pipefail
out=${1:?out}; refs=${2:?refdir}; mkdir -p "$out"; fail=0
F=(rtl/test/hbm_idx_static/tb_idx_link_nl.sv rtl/hbm_accel/index/ot_hbm_idx_topk_link_static.sv "$refs/link_ref.sv"
   physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v)
run1() {  # NL OFF LMUT expect
  t="nl$1_o$2_m$3"
  iverilog -g2012 -s tb_idx_link_nl -Ptb_idx_link_nl.NL=$1 -Ptb_idx_link_nl.OFF=$2 -Ptb_idx_link_nl.LMUT=$3 \
    -o "$out/$t" "${F[@]}" > "$out/$t.build.log" 2>&1 || { echo "BUILD_FAIL $t"; tail -5 "$out/$t.build.log"; return; }
  vvp -n "$out/$t" > "$out/$t.log" 2>&1
}
chk() {  # NL OFF LMUT expect
  t="nl$1_o$2_m$3"
  [ -f "$out/$t.log" ] || { echo "BUILD_FAIL $t"; tail -5 "$out/$t.build.log"; fail=1; return; }
  r=$(grep -o 'IDX_LINK_NL [A-Z]* checks=[0-9]* errors=[0-9]*' "$out/$t.log" | tail -1); s=$(grep 'IDX_LINK_NL NL' "$out/$t.log" | tail -1)
  echo "$t expect=$4 :: $r :: $s"
  if [ "$4" = pass ]; then echo "$r" | grep -q ' PASS ' || fail=1; else echo "$r" | grep -Eq ' FAIL checks=[0-9]+ errors=[1-9]' || fail=1; fi
}
L=("4 0 0 pass" "2 0 0 pass" "1 0 0 pass" "1 1 0 pass" "1 0 1 fail" "1 0 2 fail" "1 0 3 fail" "4 0 3 fail")
for l in "${L[@]}"; do set -- $l; run1 "$@" & done; wait
for l in "${L[@]}"; do set -- $l; chk "$@"; done
[ $fail = 0 ] && echo "IDX_LINK_NL_GATE PASS" || { echo "IDX_LINK_NL_GATE FAIL"; exit 1; }
