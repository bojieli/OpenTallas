#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --binary --timing --top-module tb -j 1 -Wno-fatal -Wno-lint -Wno-style --Mdir obj_protocol809 tb_protocol809.sv qfd_dv_ar_go_phase_reset.sv phase805_named.sv packet/rst.sv >build_protocol809.log 2>&1
./obj_protocol809/Vtb >protocol809.log 2>&1
cat protocol809.log
