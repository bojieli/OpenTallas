#!/bin/bash
set -euo pipefail
P=rtl/hbm_accel/generic/collective/p2p
V=/opt/verilator-5.050/bin/verilator
[[ -x $V ]] || V=verilator
mkdir -p target16
for variant in pos ADDR LIMIT COPY START; do
 D=();[[ $variant == pos ]] || D=(-DOT_GQ_T16_MUT_$variant)
 "$V" --binary --timing -j 8 -Wno-fatal -Wno-WIDTH "${D[@]}" --top-module tb_gq_target16 --Mdir "target16/$variant" "$P/tb_gq_target16.sv" "$P/ot_hgi_coll_gq_target16.sv" rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv > "target16/$variant.build.log" 2>&1 || { tail -30 "target16/$variant.build.log";exit 2; }
 if [[ $variant == pos ]];then
  for m in 0 1 2;do "target16/$variant/Vtb_gq_target16" +mode=$m >"target16/pos.$m.log" 2>&1;cat "target16/pos.$m.log";done
 else
  case $variant in ADDR)m=1;;LIMIT)m=2;;COPY|START)m=0;;esac
  set +e
  "target16/$variant/Vtb_gq_target16" +mode=$m >"target16/$variant.log" 2>&1
  r=$?
  set -e
  [[ $r != 0 ]] || { echo "MUTANT $variant ESCAPED";exit 1; }
  grep -E 'T16|Error' "target16/$variant.log" | head -3
  echo "GQ_TARGET16 MUTANT $variant REJECTED exit$r"
 fi
done
