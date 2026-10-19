#!/usr/bin/env bash
# usage: run_status_join_relay.sh OUT [MUT]   lockstep of ot_hbm_status_join RRELAY=1 vs the relayed-reset r1 join
# MUT 1: participation ignored; MUT 3: DUT without its reset relay.  Prints the bench's PASS/FAIL line.
set -uo pipefail
cd "$(dirname "$0")/../../.."
out=${1:?out}; mut=${2:-0}; mkdir -p "$out"
D=rtl/hbm_accel/host_static_20261015
iverilog -g2012 -Ptb_hbm_status_join_relay.MUT=$mut -s tb_hbm_status_join_relay -o "$out/sim" \
 $D/tb_hbm_status_join_relay.sv $D/ot_hbm_status_join.sv rtl/lib/ot_rst_relay.sv > "$out/build.log" 2>&1 \
 || { echo "STATUS_JOIN_RELAY_FAIL build"; cat "$out/build.log"; exit 1; }
vvp -n "$out/sim" > "$out/run.log" 2>&1
r=$(grep -E 'STATUS_JOIN_RELAY_(PASS|FAIL)' "$out/run.log" | tail -1); echo "$r"
case "$r" in *PASS*) exit 0;; *) exit 1;; esac
