#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch2/claude/codex-hbm-ep-f6-1453
for mode in legacy f6; do
 if [ "$mode" = f6 ]; then define=-DOT_HEP_RAM_F6; else define=; fi
 /home/ubuntu/.local/opentallas-tools/bin/yosys -Q -p "read_verilog -sv $define ep_keep_control.sv; hierarchy -top top; proc; flatten; opt; write_json ${mode}.json; stat -width" > "$mode.log" 2>&1
done
