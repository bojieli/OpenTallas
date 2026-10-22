#!/bin/bash
# KV-BIND5-OBS 10-19: qkd_host_obs_csr bench (mutant 0 = PASS) under the fleet's pinned Verilator 5.050.
#   [OBS_DEFS='-DOBS_NB=.. -DOBS_NF=..'] tools/qwen_kv_die/host_obs_bench.sh MUT OUTDIR  -> OUTDIR/bench_m<MUT>.log
#   exit 0 iff the PASS line (m0); default shape = the generated root's window (1301 + 71)
set -u
M=${1:-0}; O=${2:-/tmp/host_obs_bench}; mkdir -p "$O/obj_m$M"
R=$(cd "$(dirname "$0")/../.." && pwd)
for _d in "$HOME/.local/opentallas-tools/verilator-5.050/bin"; do [ -d "$_d" ] && export PATH="$_d:$PATH"; done
verilator --version
verilator --binary --timing -Wno-fatal -Wno-WIDTHTRUNC -Wno-WIDTHEXPAND -DOBS_MUT=$M ${OBS_DEFS:-} --top-module tb_qkd_host_obs_csr \
  -Mdir "$O/obj_m$M" "$R/rtl/qwen_sys/kv_host_obs_20261019/qkd_host_obs_csr.sv" "$R/rtl/test/qwen_host/tb_qkd_host_obs_csr.sv" \
  > "$O/build_m$M.log" 2>&1 || { tail -30 "$O/build_m$M.log"; exit 2; }
"$O/obj_m$M/Vtb_qkd_host_obs_csr" > "$O/bench_m$M.log" 2>&1
cat "$O/bench_m$M.log" | tail -12
grep -q "TB_QKD_HOST_OBS_CSR PASS" "$O/bench_m$M.log"
