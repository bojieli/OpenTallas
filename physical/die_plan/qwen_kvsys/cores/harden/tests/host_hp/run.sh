#!/bin/bash
set -euo pipefail
T=$(cd "$(dirname "$0")" && pwd)
O=${1:?scratch output dir required}
mkdir -p "$O"
python3 "$T/gen.py" "$O"
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
verilator --binary --timing --assert -Wno-fatal --top-module tb --Mdir "$O/obj" -j "${JOBS:-4}" "$T/old.sv" "$O/hp_new.sv" "$O/hp_mut.sv" "$T/tb.sv" > "$O/build.log" 2>&1
"$O/obj/Vtb" | tee "$O/sim.log"
yosys -Q -T -p "read_verilog -sv -noautowire $O/hp_new.sv; hierarchy -top hp_new; proc; check -assert" > "$O/lint.log" 2>&1
