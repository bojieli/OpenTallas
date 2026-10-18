#!/usr/bin/env bash
# usage: run_host_cp_rx.sh OUT [MUT]   lockstep of the folded host rx tile vs the separate landing+packet pair
# MUT 1: rx word bit flipped inside the fold; MUT 2: packet without its reset relay.  Prints the bench's PASS/FAIL line.
set -uo pipefail
cd "$(dirname "$0")/../../.."
out=${1:?out}; mut=${2:-0}; mkdir -p "$out"
D=rtl/hbm_accel/host_static_20261015; L=rtl/hbm_accel/io_native_20261014
iverilog -g2012 -DOT_MEM_NO_INIT -Ptb_hbm_host_cp_rx_lockstep.MUT=$mut -s tb_hbm_host_cp_rx_lockstep -o "$out/sim" \
 $D/tb_hbm_host_cp_rx_lockstep.sv $D/ot_hbm_host_cp_rx.sv $D/ot_hbm_host_packet_static.sv $D/ot_hbm_host_static_ingress.sv \
 $L/ot_hbm_host_landing256.sv rtl/lib/ot_rst_relay.sv \
 physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v > "$out/build.log" 2>&1 \
 || { echo "HOST_CP_RX_LOCKSTEP_FAIL build"; cat "$out/build.log"; exit 1; }
vvp -n "$out/sim" > "$out/run.log" 2>&1
r=$(grep -E 'HOST_CP_RX_LOCKSTEP_(PASS|FAIL)' "$out/run.log" | tail -1); echo "$r"
case "$r" in *PASS*) exit 0;; *) exit 1;; esac
