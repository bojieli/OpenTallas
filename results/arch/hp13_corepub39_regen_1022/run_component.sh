#!/usr/bin/env bash
set -euo pipefail
ROOT=$PWD
OUT=${1:?output directory}
mkdir -p "$OUT"
V=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --version
D=results/arch/hp13_corepub39_regen_1022
for s in ${ONLY_STAGES:-1 2}; do
 for mut in ${MUTS:-0 1 2}; do
 "$V" --binary --timing -j 1 -Wno-fatal -Wno-lint -Wno-style --top-module tb_pub -GSTAGES=$s -GMUT=$mut \
  "$D/tb_pub.sv" "$D/component_$s.sv" \
  rtl/qwen_dv/headprep13/corepub39/qfd_hp13_corepub39.sv \
  rtl/qwen_dv/headprep13/native32/qfd_tt_ctlm_dv_hp13_rrloc_helpers.sv \
  -Mdir "$OUT/obj${s}_m$mut" > "$OUT/build${s}_m$mut.log" 2>&1
 set +e
 "$OUT/obj${s}_m$mut/Vtb_pub" > "$OUT/run${s}_m$mut.log" 2>&1
 rc=$?
 set -e
 if [ "${RAW_NEG:-0}" = 1 ]; then cat "$OUT/run${s}_m$mut.log"; exit "$rc"; fi
 if [ "$mut" = 0 ]; then
   test "$rc" = 0; grep -q PUB_PASS "$OUT/run${s}_m$mut.log"
 else
   test "$rc" != 0; grep -q PUB_FAIL "$OUT/run${s}_m$mut.log"
 fi
 cat "$OUT/run${s}_m$mut.log"
 done
done
