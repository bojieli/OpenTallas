#!/bin/bash
# KV-HOST/PEER r6 (10-19): qkd_host_peer_coordinator_codec_pd vs the original codec with its allocated_* inputs delayed one
# por_n-cleared edge (tb_hr_peer_codec_pd.sv).  usage: run_hr_peer_codec_pd.sh OUT [MUT] [SEED]   MUT 1 = -DQKD_HR_PE_CPD_MUTANT
# (the registered change test without its sent bypass; must FAIL).  Verilator 5.050 unless VERILATOR.
set -u
cd "$(dirname "$0")/../../../.."
O=${1:?out}; m=${2:-0}; s=${3:-1019}; mkdir -p "$O"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
d=""; [ "$m" = 1 ] && d="-DQKD_HR_PE_CPD_MUTANT"
$V --version
$V --binary --timing -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -j 8 $d -GSEED=$s --top-module tb_hr_peer_codec_pd \
  -Mdir "$O/obj$m" rtl/test/qwen_host/hr_peer_codec_pd_1019/tb_hr_peer_codec_pd.sv \
  rtl/qwen_sys/host_integrated_20261014/qkd_host_peer_coordinator_codec.sv \
  rtl/qwen_sys/host_cluster_20261017/peer_pd/qkd_host_peer_coordinator_codec_pd.sv > "$O/build$m.log" 2>&1 \
  || { echo "HR_PEER_CODEC_PD BUILD-ERR"; tail -30 "$O/build$m.log"; exit 1; }
r=$("$O/obj$m/Vtb_hr_peer_codec_pd" | tee "$O/run$m.log" | grep -E "^HR_PEER_CODEC_PD .*(PASS|FAIL)\$" | tail -1)
echo "$r"
case "$r" in *" PASS") exit 0;; *) exit 1;; esac
