#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch2/claude/codex-selector-1028/frontend_coupon
Y=/home/ubuntu/.local/opentallas-tools/bin/yosys
for mode in eager deferred; do
 flags=''; test "$mode" != deferred || flags='-defer'
 /usr/bin/time -v "$Y" -Q -T -p "read_verilog -sv $flags coupon.sv; hierarchy -top coupon -chparam STRUCT 1; proc; stat" > "$mode.log" 2>&1
done
