#!/usr/bin/env bash
# HBM-BIND B2 (lane hbm-bind-idx 2026-10-24): ot_hbm_idx_rootctl_static_am SID / NQ / NL straps (tb_idx_rootctl_nq.sv).
#   PASS legs: B2 0 (defaults vs the unchanged as-built master) at DIE 0 and DIE 1 (r18h5 instance params);
#              B2 1 (SID 3, NQ 2, NL 1 vs the as-built text with strap 3) at DIE 0 and DIE 1.
#   FAIL legs (mutants): B2 1 DIE 0 with B2MUT 1, 2, 3, 4.
# usage: run_idx_rootctl_nq.sh OUT REFDIR   (REFDIR from mk_idx_b2_refs.sh); run from the repo root.
set -uo pipefail
out=${1:?out}; refs=${2:?refdir}; mkdir -p "$out"; fail=0
I=rtl/hbm_accel/index
F=(rtl/test/hbm_idx_static/tb_idx_rootctl_nq.sv $I/quad_1017/ot_hbm_idx_rootctl_static_am.sv "$refs/rootctl_ref.sv" "$refs/rootctl_ref3.sv"
   $I/ot_hbm_idx_calendar_static.sv $I/ot_hbm_idx_calendar_static_f32.sv $I/ot_hbm_idx_kreg.sv $I/ot_hbm_idx_topk_static.sv
   $I/ot_hbm_idx_topk_static_f32.sv rtl/hbm_accel/generic/idx/ot_hgi_idx_tk2.sv $I/ot_hbm_idx_vm_share_static_amr.sv
   rtl/lib/ot_rst_relay.sv physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v)
bld() {  # B2 DIE B2MUT
  t="b$1_d$2_m$3"
  iverilog -g2012 -DB2=$1 -DDIE=$2 -DB2MUT=$3 -o "$out/$t" "${F[@]}" > "$out/$t.build.log" 2>&1 || { echo "BUILD_FAIL $t" > "$out/$t.log"; return; }
  vvp -n "$out/$t" > "$out/$t.log" 2>&1
}
chk() {  # B2 DIE B2MUT expect
  t="b$1_d$2_m$3"
  r=$(grep -o 'IDX_ROOTCTL_NQ [A-Z]* checks=[0-9]* errors=[0-9]*' "$out/$t.log" | tail -1); s=$(grep 'IDX_ROOTCTL_NQ B2' "$out/$t.log" | tail -1)
  echo "$t expect=$4 :: ${r:-NO RESULT $(head -1 $out/$t.log)} :: $s"
  if [ "$4" = pass ]; then echo "$r" | grep -q ' PASS ' || fail=1; else echo "$r" | grep -Eq ' FAIL checks=[0-9]+ errors=[1-9]' || fail=1; fi
}
L=("0 0 0 pass" "0 1 0 pass" "1 0 0 pass" "1 1 0 pass" "1 0 1 fail" "1 0 2 fail" "1 0 3 fail" "1 0 4 fail")
for l in "${L[@]}"; do set -- $l; bld $1 $2 $3 & done; wait
for l in "${L[@]}"; do chk $l; done
[ $fail = 0 ] && echo "IDX_ROOTCTL_NQ_GATE PASS" || { echo "IDX_ROOTCTL_NQ_GATE FAIL"; exit 1; }
