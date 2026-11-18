#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
for mode in legacy round96;do
 flags=;if [ "$mode" = round96 ];then flags=-DOT_QC_AR_ROUND96;fi
 "$V" --binary --timing --top-module tb -j 2 -Wno-fatal -Wno-lint -Wno-style -Wno-PINMISSING $flags --Mdir obj_$mode tb.sv head.sv ot_rst_relay.sv >build_$mode.log 2>&1
 for op in 0 1 2 3;do ./obj_$mode/Vtb +op=$op >${mode}_${op}.log 2>&1;done
done
