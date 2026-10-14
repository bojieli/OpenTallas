#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
tag=${1:-split}; corner=${2:-ss}
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
yosys -Q -p "read_json eg_${tag}.json; hierarchy -top split_eg; write_verilog -noattr eg_${tag}_phase_dut.sv" > phase_${corner}_${tag}_emit.log
"$V" --binary --timing -j 4 -Wno-fatal --top-module tb --Mdir work_phase_${corner}_${tag} eg_${tag}_phase_dut.sv eg_surrogates.sv phase_${corner}_tb.sv retention_cell_models.sv > phase_${corner}_${tag}_build.log 2>&1
set +e
./work_phase_${corner}_${tag}/Vtb > phase_${corner}_${tag}_runtime.log 2>&1
rc=$?
set -e
cat phase_${corner}_${tag}_runtime.log
exit "$rc"
