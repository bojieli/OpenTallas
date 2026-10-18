#!/usr/bin/env bash
# usage: run_host_cfg_leaf.sh OUT [MUT] [SEED]   lockstep of the d4g host config leaves (ot_hbm_host_cfg_leaf) vs d4f direct
# MUT 1 dropped cfg_data bit, 2 copy one stage short, 3 ready bits swapped, 4 fault bit dropped. Prints the PASS/FAIL line.
set -uo pipefail
cd "$(dirname "$0")/../../.."
out=${1:?out}; mut=${2:-0}; seed=${3:-7}; mkdir -p "$out"
D=rtl/hbm_accel/host_static_20261015
iverilog -g2012 -Ptb_hbm_host_cfg_leaf_lockstep.MUT=$mut -Ptb_hbm_host_cfg_leaf_lockstep.SEED=$seed -s tb_hbm_host_cfg_leaf_lockstep -o "$out/sim" \
 $D/tb_hbm_host_cfg_leaf_lockstep.sv $D/ot_hbm_host_cfg_leaf.sv $D/ot_hbm_host_static_ingress.sv $D/ot_hbm_status_join_fa.sv \
 $D/ot_hbm_status_join.sv rtl/lib/ot_rst_relay.sv > "$out/build.log" 2>&1 \
 || { echo "HOST_CFG_LEAF_LOCKSTEP_FAIL build"; cat "$out/build.log"; exit 1; }
vvp -n "$out/sim" > "$out/run.log" 2>&1
r=$(grep -E 'HOST_CFG_LEAF_LOCKSTEP_(PASS|FAIL)' "$out/run.log" | tail -1); echo "$r"
case "$r" in *PASS*) exit 0;; *) exit 1;; esac
