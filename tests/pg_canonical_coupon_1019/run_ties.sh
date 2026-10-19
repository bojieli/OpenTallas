#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../.."
ROOT=$PWD
IMG=openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
mkdir -p evidence_native_v3
sha256sum map_v2/results/asap7/pg_canonical_coupon_1019/base/1_synth.odb >evidence_native_v3/original_before.sha256
RUN=(docker run --rm -v "$ROOT:/src" -w /src "$IMG")
"${RUN[@]}" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /src/tests/pg_canonical_coupon_1019/ties.tcl >evidence_native_v3/ties.log 2>&1
"${RUN[@]}" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /src/tests/pg_canonical_coupon_1019/export_raw.py /src/evidence_native_v3/ties.odb /src/evidence_native_v3 >evidence_native_v3/export.log 2>&1
"${RUN[@]}" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /src/tests/pg_canonical_coupon_1019/native_cost.py /src/evidence_native_v3/ties.odb /src/evidence_native_v3/native_cost.json >evidence_native_v3/native_cost.log 2>&1
cp -a evidence_native_v2/libs_TT evidence_native_v2/libs_FF evidence_native_v2/libs_SS evidence_native_v3/
python3 tests/pg_canonical_coupon_1019/strict_inventory.py "$ROOT" v3 >evidence_native_v3/strict.log 2>&1
sha256sum -c evidence_native_v3/original_before.sha256 >evidence_native_v3/original_after.log
