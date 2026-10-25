#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$VL" --binary --timing --x-initial unique --x-assign unique -j 4 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style --top-module tb -Mdir obj_r3 dsdv_idx_tx_i13.sv dsdv_idx_l20s.sv dsdv_idx_tree.sv ot_rst_relay.sv tb.sv > build_r3.log 2>&1
for c in dense cam miss duplicate wrongtag;do obj_r3/Vtb +CASE=$c +verilator+rand+reset+2 > $c.r3.log;done
python3 check.py r3
