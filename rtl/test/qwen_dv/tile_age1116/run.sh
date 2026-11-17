#!/bin/bash
set -euo pipefail
WORK=${1:?fresh scratch directory required}
HERE=$(cd -- "$(dirname -- "$0")" && pwd)
REPO=$(cd "$HERE/../../../.." && pwd)
mkdir "$WORK"
tar -xzf "$REPO/results/rtl/qc_tile_age_1116/source_capsule.tar.gz" -C "$WORK"
cp "$HERE"/{tb.sv,commands.hex,sources.f,run.py,build.sh} "$WORK/"
cd "$WORK"
bash build.sh
python3 run.py
