#!/usr/bin/env bash
set -uo pipefail
cd /srv/opentallas-scratch2/claude/s81-ports-1025/i13_sram
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$VL" --binary --timing --x-initial unique --x-assign unique -j 4 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style --top-module tb -Mdir obj_s ot_sram_1r1w_1024x256_m2_r2c2.v dsdv_idx_tx_i13.sv dsdv_idx_l20s.sv dsdv_idx_tree.sv ot_rst_relay.sv tb.sv > build_s.log 2>&1 || { tail -20 build_s.log; exit 2; }
for c in dense cam miss duplicate wrongtag;do obj_s/Vtb +CASE=$c +verilator+rand+reset+2 > $c.s.log;done
python3 check.py s
