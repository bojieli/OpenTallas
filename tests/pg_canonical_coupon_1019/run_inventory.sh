#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../.."
ROOT=$PWD
IMG=openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
mkdir -p evidence_native_v2
ODB=/src/map_v2/results/asap7/pg_canonical_coupon_1019/base/1_synth.odb
RUN=(docker run --rm -v "$ROOT:/src" -w /src "$IMG")
"${RUN[@]}" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /src/tests/pg_canonical_coupon_1019/export_raw.py "$ODB" /src/evidence_native_v2 >evidence_native_v2/export.log 2>&1
"${RUN[@]}" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /src/tests/pg_canonical_coupon_1019/native_cost.py "$ODB" /src/evidence_native_v2/native_cost.json >evidence_native_v2/native_cost.log 2>&1
"${RUN[@]}" bash -lc 'for c in TT FF SS; do mkdir -p /src/evidence_native_v2/libs_$c; cp /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_RVT_${c}_* /src/evidence_native_v2/libs_$c/; done'
python3 tests/pg_canonical_coupon_1019/strict_inventory.py "$ROOT" >evidence_native_v2/strict.log 2>&1
