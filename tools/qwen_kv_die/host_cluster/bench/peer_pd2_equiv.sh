#!/bin/bash
# KV-HOST/PEER r6 (10-19): qkd_hr_core_peer r6 token-service fork _pd2 equivalence bench (tb_hkv_peer_pd2_equiv: delayed
# output arrays vs the original one edge earlier, every other output every edge), four configurations
# (ENABLE_SERVICE=ENABLE_TOKEN in {1,0} x die {0, peer}).
#   peer_pd2_equiv.sh pass   OUT -> "HKV_PEER_PD2 PASS 4/4"
#   peer_pd2_equiv.sh mutant OUT -> built with QKD_HR_PEPD2_MUTANT; "HKV_PEER_PD2 FAIL mutant n/4" (n>=1 required)
# Run from the repository root (Verilator 5.050, as the closure daemon).
set -u
MODE=${1:-pass}; OUT=${2:-/tmp/hkv_peer_pd2}; mkdir -p "$OUT"
D=""; [ "$MODE" = mutant ] && D="-DQKD_HR_PEPD2_MUTANT"
F="rtl/test/qwen_host/tb_hkv_peer_pd2_equiv.sv rtl/qwen_sys/host_integrated_20261014/qkd_host_ctrl_token_service_packet_collected.sv rtl/qwen_sys/host_cluster_20261017/peer_pd/qkd_host_ctrl_token_service_packet_collected_pd2.sv"
verilator --version
np=0; nf=0
for cfg in "1 0 11" "1 3 12" "0 0 13" "0 5 14"; do
  set -- $cfg; n="es$1_d$2"
  rm -rf "$OUT/$n"
  verilator --binary -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD $D -GES=$1 -GDIEID=$2 -GSEED=$3 \
    --top-module tb_hkv_peer_pd2_equiv -Mdir "$OUT/$n" $F >"$OUT/$n.build.log" 2>&1 || { tail -30 "$OUT/$n.build.log"; echo "BUILD_ERROR $n"; exit 2; }
  "$OUT/$n/Vtb_hkv_peer_pd2_equiv" | tee "$OUT/$n.log"
  grep -q "HKV_PEER_PD2_EQUIV PASS" "$OUT/$n.log" && np=$((np+1)) || nf=$((nf+1))
done
if [ "$MODE" = pass ]; then
  [ $np = 4 ] && { echo "HKV_PEER_PD2 PASS 4/4"; exit 0; }; echo "HKV_PEER_PD2 FAIL $nf/4"; exit 1
else
  [ $nf -ge 1 ] && { echo "HKV_PEER_PD2 FAIL mutant $nf/4"; exit 1; }; echo "HKV_PEER_PD2 MUTANT_NOT_CAUGHT"; exit 0
fi
