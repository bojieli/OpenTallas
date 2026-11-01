#!/bin/bash
set -euo pipefail
T=$(cd "$(dirname "$0")" && pwd)
O=${1:?scratch output directory required}
python3 "$T/gen.py" "$O"
cp "$T/tb.sv" "$T/check_boundary.sh" "$O/"
cd "$O"
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
verilator --binary --timing --assert -Wno-fatal --top-module tb --Mdir obj -j "${JOBS:-4}" ref.sv new.sv mut.sv tb.sv > build.log 2>&1
./obj/Vtb | tee sim.log
bash check_boundary.sh | tee boundary.log
