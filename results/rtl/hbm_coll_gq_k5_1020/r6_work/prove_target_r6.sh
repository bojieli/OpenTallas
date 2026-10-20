#!/bin/bash
set -euo pipefail
out=$PWD/proofs_r6_target;mkdir -p "$out"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
P=rtl/hbm_accel/generic/collective/p2p
Q=rtl/hbm_accel/generic/vm/static
"$V" --version > "$out/version.txt"
sha256sum "$P/ot_hgi_coll_gq_target16.sv" "$P/tb_gq_target16_r6.sv" "$Q/ot_static_program_target.sv" > "$out/sources.sha256"
for name in gold mutant;do
 flags=();if test "$name" = mutant;then flags+=(-DOT_GQ_MUT_BASE_SHADOW);fi
 "$V" --binary --timing -j 2 -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -DOT_GQ_N32 "${flags[@]}" --top-module tb_gq_target16_r6 --Mdir "$out/obj_$name" -o tb "$P/tb_gq_target16_r6.sv" "$P/ot_hgi_coll_gq_target16.sv" "$Q/ot_static_program_target.sv" > "$out/build_$name.log" 2>&1
 if test "$name" = gold;then
  for mode in 0 1 2;do "$out/obj_$name/tb" +mode=$mode > "$out/gold_$mode.log" 2>&1;done
 else
  if "$out/obj_$name/tb" +mode=0 > "$out/mutant.log" 2>&1;then echo R6_MUT_ESCAPED;exit 1;fi
  grep R6_BASE_COPY_FAIL "$out/mutant.log"
 fi
done
echo R6_TARGET_PROOF_PASS_20LAUNCHES_16BASES_3MODES_CAUSAL1
