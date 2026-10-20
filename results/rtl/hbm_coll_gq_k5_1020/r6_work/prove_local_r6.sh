#!/bin/bash
set -euo pipefail
out=$PWD/proofs_r6_local;mkdir -p "$out"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
P=rtl/hbm_accel/generic/collective/p2p
sha256sum "$P/ot_hgi_coll_gq.sv" "$P/tb_gq_r6_local.sv" rtl/lib/ot_rst_relay.sv > "$out/sources.sha256"
for name in gold resetraw resetlate wraphigh;do
 flags=();case "$name" in resetraw)flags+=(-DOT_GQ_MUT_REQ_RESET_RAW);;resetlate)flags+=(-DOT_GQ_MUT_REQ_RESET_LATE);;wraphigh)flags+=(-DOT_GQ_MUT_WRAP_HIGH);;esac
 "$V" --binary --timing -j 2 -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD "${flags[@]}" --top-module tb_gq_r6_local --Mdir "$out/obj_$name" -o tb "$P/tb_gq_r6_local.sv" "$P/ot_hgi_coll_gq.sv" rtl/lib/ot_rst_relay.sv > "$out/build_$name.log" 2>&1
 if test "$name" = gold;then "$out/obj_$name/tb" > "$out/$name.log" 2>&1;grep R6_LOCAL_PASS "$out/$name.log";
 else
  if "$out/obj_$name/tb" > "$out/$name.log" 2>&1;then echo MUT_ESCAPED;exit 1;fi
  if test "$name" = wraphigh;then grep R6_WRAP_EQ_FAIL "$out/$name.log";else grep R6_RESET_EQ_FAIL "$out/$name.log";fi
 fi
done
echo R6_LOCAL_PROOFS_PASS_GOLD_PLUS3CAUSAL
