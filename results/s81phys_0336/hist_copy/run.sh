#!/bin/bash
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
RUN=${1:?Pass a scratch output directory}
mkdir -p "$RUN"
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
verilator --binary --timing --assert -Wno-fatal -j 4 --top-module tb --Mdir "$RUN/obj" "$HERE/prefix.sv" "$HERE/reset.sv" "$HERE/ref.sv" "$HERE/copy.sv" "$HERE/mut.sv" "$HERE/tb.sv" > "$RUN/build.log" 2>&1
"$RUN/obj/Vtb" > "$RUN/result.log" 2>&1
cat "$RUN/result.log"
