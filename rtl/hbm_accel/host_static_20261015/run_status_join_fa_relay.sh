#!/usr/bin/env bash
# usage: run_status_join_fa_relay.sh OUT [MUT] [PSET]   lockstep of ot_hbm_status_join_fa RRELAY=1 vs RRELAY=0 under a relayed reset
# MUT 1: participation ignored; 3: DUT without its reset relays; 4: cause not sticky (FMUT 1).  Prints the PASS/FAIL line.
set -uo pipefail
cd "$(dirname "$0")/../../.."
out=${1:?out}; mut=${2:-0}; pset=${3:-r3}; mkdir -p "$out"
# PSET r3 = module defaults (NT67/NF105); d4f = the HBM d4f die host_status instance (hdie_host_status_fa_r4, run8 contract)
P=()
case "$pset" in r3) ;; d4f) P=(-Ptb_hbm_status_join_fa_relay.NT=69 -Ptb_hbm_status_join_fa_relay.NF=107 -Ptb_hbm_status_join_fa_relay.NH=6
 "-Ptb_hbm_status_join_fa_relay.TGTS=552'h7f7ed7d6d5d4d3d2d1d0c7c6c5c4c3c2c1c0a5a4a2a0878685846f6e6d6c6a68666463626160575655545352515047464544434241403b3a39387877767574703736353430");;
 *) echo "STATUS_JOIN_FA_RELAY_FAIL pset $pset"; exit 1;; esac
D=rtl/hbm_accel/host_static_20261015
iverilog -g2012 -Ptb_hbm_status_join_fa_relay.MUT=$mut "${P[@]}" -s tb_hbm_status_join_fa_relay -o "$out/sim" \
 $D/tb_hbm_status_join_fa_relay.sv $D/ot_hbm_status_join_fa.sv $D/ot_hbm_status_join.sv rtl/lib/ot_rst_relay.sv > "$out/build.log" 2>&1 \
 || { echo "STATUS_JOIN_FA_RELAY_FAIL build"; cat "$out/build.log"; exit 1; }
vvp -n "$out/sim" > "$out/run.log" 2>&1
r=$(grep -E 'STATUS_JOIN_FA_RELAY_(PASS|FAIL)' "$out/run.log" | tail -1); echo "$r"
case "$r" in *PASS*) exit 0;; *) exit 1;; esac
