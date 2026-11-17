#!/bin/bash
set -euo pipefail
WORK=${1:?fresh scratch directory required}
HERE=$(cd -- "$(dirname -- "$0")" && pwd)
REPO=$(cd "$HERE/../../../../.." && pwd)
mkdir "$WORK"
tar -xzf "$REPO/results/rtl/qc_stn55_1116/source_capsule.tar.gz" -C "$WORK"
cp "$HERE/tb.sv" "$WORK/"
cd "$WORK"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --binary --timing --top-module tb -j 2 -Wno-fatal -Wno-lint -Wno-style --Mdir obj tb.sv delay55.sv reset.sv safe.sv helpers.sv sram.v ring.sv land.sv land_n32.sv >build.log 2>&1
./obj/Vtb
