#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")"
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$VL" --binary --timing --x-initial unique --x-assign unique -j 4 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style --top-module tb -Mdir obj dsdv_idx_tx_i13.sv reference.sv dsdv_idx_l20s.sv dsdv_idx_tree.sv ot_rst_relay.sv tb_lockstep.sv > build.log 2>&1 || { tail -20 build.log; exit 2; }
rc=0
for c in dense cam skip twosrc; do obj/Vtb +CASE=$c +verilator+rand+reset+2 > "$c.log" 2>&1 || rc=1; done
"$VL" --binary --timing --x-initial unique --x-assign unique -j 4 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style --top-module tb +define+MUT=2 -Mdir obj_mut dsdv_idx_tx_i13.sv reference.sv dsdv_idx_l20s.sv dsdv_idx_tree.sv ot_rst_relay.sv tb_lockstep.sv > build_mut.log 2>&1 || { tail -20 build_mut.log; exit 2; }
if obj_mut/Vtb +CASE=cam +verilator+rand+reset+2 > mutant.log 2>&1; then echo MUTANT_ESCAPED; rc=1; else echo MUTANT_CAUGHT; fi
echo lockstep_rc=$rc
exit $rc
