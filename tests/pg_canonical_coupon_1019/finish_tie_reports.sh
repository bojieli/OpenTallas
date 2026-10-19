#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../.."
ROOT=$PWD
IMG=openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
RUN=(docker run --rm -v "$ROOT:/src" -w /src "$IMG")
"${RUN[@]}" bash -lc 'for c in TT FF SS; do mkdir -p /src/evidence_native_v3/libs_$c; cp /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_RVT_${c}_* /src/evidence_native_v3/libs_$c/; done'
"${RUN[@]}" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /src/tests/pg_canonical_coupon_1019/native_cost.py /src/evidence_native_v3/ties.odb /src/evidence_native_v3/native_cost_full.json >evidence_native_v3/native_cost_full.log 2>&1
python3 tests/pg_canonical_coupon_1019/strict_inventory.py "$ROOT" v3 >evidence_native_v3/strict.log 2>&1
sha256sum -c evidence_native_v3/original_before.sha256 >evidence_native_v3/original_after.log
