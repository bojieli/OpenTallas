#!/bin/bash
set -euo pipefail
# Run only through ot-run; WORK must be a fresh scratch directory.
WORK=${1:?fresh scratch directory required}
FIXTURE=${2:-single}
HERE=$(cd -- "$(dirname -- "$0")" && pwd)
REPO=$(cd "$HERE/../../../.." && pwd)
mkdir "$WORK"
tar -xzf "$REPO/results/rtl/qc_mif_native_1116/source_capsule.tar.gz" -C "$WORK"
cp "$HERE/component.sv" "$HERE/tb.sv" "$HERE/sources.f" "$WORK/"
cp "$HERE/$FIXTURE.hex" "$WORK/programme.hex"
cd "$WORK"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --binary --timing --top-module tb -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-PINMISSING -Wno-IMPLICIT -Wno-SELRANGE -Wno-WIDTH --Mdir obj -f sources.f >build.log 2>&1
./obj/Vtb >run.log 2>&1
cat run.log
grep -q MIF_NATIVE_PROFILE_PASS run.log
