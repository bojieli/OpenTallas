#!/bin/bash
# usage: harden_wc.sh <name> <runner args...>   W11 WC (SS) setup / BC (FF) hold at 0.833 ns, 60/25
name=$1; shift
export TMPDIR=/home/ubuntu/w11tmp; mkdir -p $TMPDIR
O=/tmp/claude-1000/w11s/hard/$name; mkdir -p $O
exec python3 tools/run_abi3_physical.py --view asap7 --clock-period-ns 0.833 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
  --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0 --false-path-from rst_n --slew-margin-percent 40 --stages synth,pnr --force \
  --step-tcl PRE_CTS=physical/abi3/v41x_karb_repair_buffer_cap.tcl --step-tcl PRE_GLOBAL_ROUTE=physical/abi3/v41x_karb_repair_buffer_cap.tcl \
  --keep-heavy-artifacts --hold-margin-ns 0.01 --nickname-tag w11$name --output $O/physical.json "$@"
