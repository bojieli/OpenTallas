#!/bin/bash
set -euo pipefail
WORK=${1:?fresh scratch directory required}
HERE=$(cd -- "$(dirname -- "$0")" && pwd)
REPO=$(cd "$HERE/../../../.." && pwd)
mkdir "$WORK"
tar -xzf "$REPO/results/rtl/qc_rope_boundary_1116/source_capsule.tar.gz" -C "$WORK"
cp "$HERE/tb.sv" "$HERE/sources.f" "$HERE/rope_sweep.hex" "$HERE/rope_expected.hex" "$WORK/"
if [[ ${2:-ovl1} == ovl0 ]]; then cp "$HERE/tb_ovl0.sv" "$WORK/tb.sv"; fi
cd "$WORK"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --binary --timing --top-module tb -j 2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-PINMISSING -Wno-IMPLICIT -Wno-WIDTH --Mdir obj -f sources.f >build.log 2>&1
./obj/Vtb >run.log 2>&1
cat run.log
grep -q ROPE_RESIDENT_BOUNDARY_PASS run.log
