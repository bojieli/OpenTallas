#!/bin/bash
# NATIVE-FIX3/kvhr 2026-10-18: reset-relay lockstep + release-latency bench, one case per call.
#   usage: run_hr_rr.sh OUT CASE [MUT]     CASE: tx | rx     MUT 1 = -DQKD_HR_RR_MUTANT (relay bypassed; must FAIL)
# Prints the bench's own result line ("HR_RR_LOCKSTEP ... PASS|FAIL"); exit 0 on PASS.
set -u
cd "$(dirname "$0")/../../../.."
O=${1:?out}; c=${2:?case}; m=${3:-0}; mkdir -p "$O"
H=rtl/qwen_sys/host_20261013; T=rtl/test/qwen_host/hr_rr_1018
d=""; [ "$m" = 1 ] && d="-DQKD_HR_RR_MUTANT"
case "$c" in
 tx) a="$T/tb_hr_rr_tx.sv $H/qkd_host_tx_class_rr.sv $H/qkd_host_tx_class.sv rtl/lib/ot_rst_relay.sv";;
 rx) a="$T/tb_hr_rr_rx.sv $H/qkd_host_rx_class_admission_rr.sv $H/qkd_host_rx_class_admission.sv $H/qkd_host_rx_class.sv rtl/lib/ot_rst_relay.sv";;
 *) echo "HR_RR $c: unknown case"; exit 2;;
esac
iverilog -g2012 $d $a -o "$O/$c.vvp" > "$O/$c.build" 2>&1 || { echo "HR_RR $c: BUILD-ERR"; cat "$O/$c.build"; exit 1; }
r=$(vvp -n "$O/$c.vvp" | grep -v 'finish called' | tee "$O/$c.log" | grep -E 'HR_RR_LOCKSTEP .*(PASS|FAIL)$' | tail -1)
echo "$r"
case "$r" in *" PASS") exit 0;; *) exit 1;; esac
