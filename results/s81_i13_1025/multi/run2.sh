#!/usr/bin/env bash
set -uo pipefail
cd /srv/opentallas-scratch2/claude/s81-ports-1025/i13_multi
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$VL" --binary --timing --x-initial unique --x-assign unique -j 4 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style --top-module tb -Mdir obj dsdv_idx_tx_i13.sv dsdv_idx_l20s.sv dsdv_idx_tree.sv ot_rst_relay.sv tb2.sv > build.log 2>&1 || { tail -20 build.log; exit 2; }
for c in multi samebank; do obj/Vtb +CASE=$c +verilator+rand+reset+2 > $c.log; done
python3 check2.py
