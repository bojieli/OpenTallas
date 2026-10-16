#!/bin/bash
# run_landing_seg.sh pos|neg OUT (Q-KVSYS-STRIP 2026-10-16): the hardened static landing segment qkd_static_kv_landing_seg
# in tb_static_landing at production shape (32 groups = 32 segment instances on their cfg straps, 128 PCs with the real
# 128x256 SRAM model, ctx 8192, VMAP 1 = PV16 V layout, VREQ 1 = V gets on the vport face), latency 8 edges.
#   pos: faultmode 0 must PASS (every K and V row word, t, kind on its edge) and the fault modes 1-5 must FAIL
#   neg: the segment with HOP_MUT 1 (branch-0 response hop flips a data bit) must FAIL -> prints
#        'FAIL landing_seg mutant detected' and exits 1
set -u
M=$1; O=$2; mkdir -p "$O"
V5=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; VL=${VERILATOR:-$( [ -x $V5 ] && echo $V5 || command -v verilator)}
S=rtl/qwen_sys/static_kv_20261014
HM=0; [ "$M" = neg ] && HM=1
$VL --binary --timing -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTH -Wno-MULTIDRIVEN --build-jobs 8 \
  --top-module tb_static_landing -GVMAP=1 -GDUT_VMAP=1 -GVREQ=1 -GPHYS=1 -GSEG_HOP_MUT=$HM --Mdir "$O/obj" \
  physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
  $S/qkd_static_kv_landing.sv $S/qkd_static_kv_hop.sv $S/qkd_static_kv_landing_seg.sv rtl/test/qwen_static_kv/tb_static_landing.sv \
  > "$O/build.log" 2>&1 || { echo "BUILD FAIL"; tail -5 "$O/build.log"; exit 3; }
res(){ "$O/obj/Vtb_static_landing" +faultmode=$1 2>&1 | tee "$O/fm$1.log" | grep -E "^(PASS|FAIL) staticlanding" | tail -1; }
if [ "$M" = neg ]; then
  l=$(res 0); echo "mutant run: ${l:-no result line}"
  case "$l" in FAIL*) echo "FAIL landing_seg mutant detected (response hop data bit)"; exit 1;; esac
  echo "mutant NOT detected"; exit 0
fi
rc=0
l=$(res 0); echo "faultmode 0: ${l:-no result line}"; case "$l" in PASS*) ;; *) rc=1;; esac
for f in 1 2 3 4 5; do l=$(res $f); echo "faultmode $f (must FAIL): ${l:-no result line}"; case "$l" in FAIL*) ;; *) rc=1;; esac; done
[ $rc = 0 ] && echo "PASS landing_seg exact: 32 segments x 4 PCs, K + V (PV16, vport face) every word, fault modes 1-5 caught" || echo "FAIL landing_seg"
exit $rc
