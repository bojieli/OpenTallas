#!/bin/bash
set -euo pipefail
WORK=${1:?fresh scratch directory required}
HERE=$(cd -- "$(dirname -- "$0")" && pwd)
REPO=$(cd "$HERE/../../../.." && pwd)
mkdir "$WORK"
tar -xzf "$REPO/results/rtl/qc_stn55_1116/source_capsule.tar.gz" -C "$WORK"
cp "$HERE/tb.sv" "$HERE/sources.f" "$HERE/build.sh" "$WORK/"
cd "$WORK"
bash build.sh
./obj/Vtb +K=2 +MODE=1 >o.log 2>&1
./obj/Vtb +K=6 +MODE=1 >down.log 2>&1
./obj/Vtb +K=32 +MODE=0 >gu.log 2>&1
./obj/Vtb +K=8 +MODE=2 >qkv.log 2>&1
cat o.log down.log gu.log qkv.log
