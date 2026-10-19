#!/bin/bash
# KV-PEER5 2026-10-19: qkd_host_peer_root_mux_pl2 vs the unchanged qkd_host_peer_root_mux (tb_hr_peer_pl2.sv).
#   usage: run_hr_peer_pl2.sh OUT [MUT] [SEED]    MUT 1 = -DQKD_HR_PE_PL2_MUTANT (RX slice corrupts a bit; must FAIL)
# Verilator 5.050 (the closure daemon's) unless VERILATOR is set. Prints the bench's result line; exit 0 on PASS.
set -u
cd "$(dirname "$0")/../../../.."
O=${1:?out}; m=${2:-0}; s=${3:-1019}; mkdir -p "$O"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
d=""; [ "$m" = 1 ] && d="-DQKD_HR_PE_PL2_MUTANT"
T=rtl/test/qwen_host/hr_peer_pl2_1019
$V --version
$V --binary --timing -Wno-fatal -Wno-lint -Wno-style -j 4 $d -GSEED=$s --top-module tb_hr_peer_pl2 -Mdir "$O/obj$m" \
  $T/tb_hr_peer_pl2.sv rtl/qwen_sys/host_integrated_20261014/qkd_host_peer_root_mux.sv \
  rtl/qwen_sys/host_cluster_20261017/peer_rr/qkd_host_peer_root_mux_pl2.sv > "$O/build$m.log" 2>&1 \
  || { echo "HR_PEER_PL2 BUILD-ERR"; tail -30 "$O/build$m.log"; exit 1; }
r=$("$O/obj$m/Vtb_hr_peer_pl2" | tee "$O/run$m.log" | grep -E '^HR_PEER_PL2 .*(PASS|FAIL)$' | tail -1)
echo "$r"
case "$r" in *" PASS") exit 0;; *) exit 1;; esac
