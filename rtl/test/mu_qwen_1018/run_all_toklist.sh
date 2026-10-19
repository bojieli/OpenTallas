#!/bin/bash
# MU-KV-TOKLIST 10-19: the TOKLIST bench, its mutants (must FAIL) and the GAP-mode regression (MU-KV-BOOT bench + mutants on
# the edited qkd_static_kv_layer_programme_mu / qkd_static_kv_boot_dispatch_mu at TOKLIST 0).  usage: run_all_toklist.sh ROOT OUT
# Keep OUT short: tb_mu_kv_boot passes absolute data paths through 128-character filename registers.
set -u
R=$(cd "${1:?root}" && pwd); O=${2:?out}; mkdir -p "$O"; O=$(cd "$O" && pwd)
B=$(dirname "$(readlink -f "$0")")
for t in tb_mu_kv_toklist kt_sealwrong kt_listnot kt_u0hdr kt_short kt_collide kt_nowrap kt_lane; do
  "$B/run_mu_kv_toklist.sh" "$R" "$O/tl" $t > "$O/s_$t.txt" 2>&1 & done
TL_DIR=results/rtl/mu_qwen_1018/kvtoklist/f14 "$B/run_mu_kv_toklist.sh" "$R" "$O/f14" tb_mu_kv_toklist > "$O/s_f14_tb_mu_kv_toklist.txt" 2>&1 &
for t in tb_mu_kv_boot kb_sealwrong kb_gapnot kb_u0gap kb_collide; do
  "$B/run_mu_kv_boot.sh" "$R" "$O/g" $t > "$O/s_$t.txt" 2>&1 & done
wait
cat "$O"/s_*.txt | sort > "$O/summary.txt"; cat "$O/summary.txt"
